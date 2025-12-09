"""API Data Fetcher for Census and FRED economic data."""
import requests
import pandas as pd
import streamlit as st
from typing import Dict, List, Optional
import time

class CensusDataFetcher:
    """Fetch data from US Census Bureau API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.census.gov/data"
    
    def get_median_income_by_county(self, state_fips: str = "06", year: int = 2022) -> pd.DataFrame:
        """
        Fetch median household income by California county.
        State FIPS 06 = California
        """
        try:
            url = f"{self.base_url}/{year}/acs/acs5"
            params = {
                'get': 'NAME,B19013_001E',  # B19013_001E = Median Household Income
                'for': 'county:*',
                'in': f'state:{state_fips}',
                'key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            df = pd.DataFrame(data[1:], columns=data[0])
            df['median_income'] = pd.to_numeric(df['B19013_001E'], errors='coerce')
            df['county_name'] = df['NAME'].str.replace(' County, California', '')
            
            return df[['county_name', 'median_income']].dropna()
            
        except Exception as e:
            st.warning(f"Census API error: {e}")
            return pd.DataFrame()
    
    def get_population_by_county(self, state_fips: str = "06", year: int = 2021) -> pd.DataFrame:
        """Fetch population data by California county from ACS."""
        try:
            # Use ACS 5-year data for population (more reliable)
            url = f"{self.base_url}/{year}/acs/acs5"
            params = {
                'get': 'NAME,B01003_001E',  # B01003_001E = Total Population
                'for': 'county:*',
                'in': f'state:{state_fips}',
                'key': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            df = pd.DataFrame(data[1:], columns=data[0])
            df['population'] = pd.to_numeric(df['B01003_001E'], errors='coerce')
            df['county_name'] = df['NAME'].str.replace(' County, California', '').str.replace(', California', '')
            
            return df[['county_name', 'population']].dropna()
            
        except Exception as e:
            st.warning(f"Census Population API error: {e}")
            return pd.DataFrame()


class FREDDataFetcher:
    """Fetch economic data from Federal Reserve Economic Data (FRED)."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"
    
    def get_series_data(self, series_id: str, start_date: str = "2023-01-01") -> pd.DataFrame:
        """Fetch FRED time series data."""
        try:
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'observation_start': start_date
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'observations' in data:
                df = pd.DataFrame(data['observations'])
                df['value'] = pd.to_numeric(df['value'], errors='coerce')
                df['date'] = pd.to_datetime(df['date'])
                return df[['date', 'value']].dropna()
            
            return pd.DataFrame()
            
        except Exception as e:
            st.warning(f"FRED API error for {series_id}: {e}")
            return pd.DataFrame()
    
    def get_unemployment_rate(self) -> Optional[float]:
        """Get latest US unemployment rate."""
        df = self.get_series_data('UNRATE')  # Unemployment Rate series
        if not df.empty:
            return float(df.iloc[-1]['value'])
        return None
    
    def get_mortgage_rate(self) -> Optional[float]:
        """Get latest 30-year mortgage rate."""
        df = self.get_series_data('MORTGAGE30US')
        if not df.empty:
            return float(df.iloc[-1]['value'])
        return None
    
    def get_california_housing_price_index(self) -> pd.DataFrame:
        """Get California housing price index trends."""
        return self.get_series_data('CASTHPI')  # CA State Housing Price Index


class DataEnricher:
    """Enrich sample data with real API data."""
    
    def __init__(self, census_api_key: str, fred_api_key: str):
        self.census_fetcher = CensusDataFetcher(census_api_key)
        self.fred_fetcher = FREDDataFetcher(fred_api_key)
        self.cached_data = {}
    
    def enrich_neighborhood_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enrich the neighborhood dataset with real API data."""
        
        # Extract county from neighborhood name
        df['county'] = df['name'].str.extract(r'\(([^)]+)\)')[0]
        
        # Fetch real income data
        with st.spinner("Fetching Census income data..."):
            income_data = self.census_fetcher.get_median_income_by_county()
        
        if not income_data.empty:
            # Merge income data
            df = df.merge(
                income_data.rename(columns={'county_name': 'county', 'median_income': 'real_median_income'}),
                on='county',
                how='left'
            )
            
            # Update affordability scores based on real income
            mask = df['real_median_income'].notna()
            if mask.any():
                df.loc[mask, 'median_income'] = df.loc[mask, 'real_median_income']
                # Recalculate affordability
                df.loc[mask, 'affordability'] = df.loc[mask].apply(
                    lambda row: self._calculate_affordability(row['median_rent'], row['real_median_income']),
                    axis=1
                )
        
        # Fetch population data
        with st.spinner("Fetching Census population data..."):
            pop_data = self.census_fetcher.get_population_by_county()
        
        if not pop_data.empty:
            df = df.merge(
                pop_data.rename(columns={'county_name': 'county'}),
                on='county',
                how='left'
            )
        
        return df
    
    def get_economic_indicators(self) -> Dict:
        """Fetch current economic indicators."""
        indicators = {}
        
        with st.spinner("Fetching FRED economic data..."):
            indicators['unemployment_rate'] = self.fred_fetcher.get_unemployment_rate()
            indicators['mortgage_rate'] = self.fred_fetcher.get_mortgage_rate()
            
            # Get housing price index trend
            hpi_data = self.fred_fetcher.get_california_housing_price_index()
            if not hpi_data.empty:
                recent = hpi_data.tail(12)  # Last 12 months
                if len(recent) >= 2:
                    pct_change = ((recent.iloc[-1]['value'] - recent.iloc[0]['value']) / recent.iloc[0]['value']) * 100
                    indicators['housing_price_trend'] = round(pct_change, 2)
                    indicators['latest_hpi'] = float(recent.iloc[-1]['value'])
        
        return indicators
    
    def _calculate_affordability(self, rent: float, income: float) -> float:
        """Calculate affordability score (0-100)."""
        if income <= 0:
            return 0
        monthly_income = income / 12
        rent_to_income_ratio = rent / monthly_income
        
        if rent_to_income_ratio <= 0.25:
            return 100
        elif rent_to_income_ratio <= 0.30:
            return 85
        elif rent_to_income_ratio <= 0.35:
            return 70
        elif rent_to_income_ratio <= 0.40:
            return 50
        else:
            return max(0, 100 - (rent_to_income_ratio - 0.3) * 200)


def display_economic_dashboard(indicators: Dict):
    """Display economic indicators in Streamlit."""
    st.subheader("Current Economic Indicators")
    
    cols = st.columns(3)
    
    with cols[0]:
        if indicators.get('unemployment_rate'):
            st.metric(
                "US Unemployment Rate",
                f"{indicators['unemployment_rate']}%",
                help="Source: Federal Reserve Economic Data (FRED)"
            )
    
    with cols[1]:
        if indicators.get('mortgage_rate'):
            st.metric(
                "30-Year Mortgage Rate",
                f"{indicators['mortgage_rate']}%",
                help="Source: FRED - Freddie Mac Primary Mortgage Market Survey"
            )
    
    with cols[2]:
        if indicators.get('housing_price_trend'):
            st.metric(
                "CA Housing Price Trend (YoY)",
                f"{indicators['housing_price_trend']:+.2f}%",
                delta=f"{indicators['housing_price_trend']:.2f}%",
                help="Year-over-year change in California Housing Price Index"
            )
    
    st.info("Real-time data from US Census Bureau and Federal Reserve FRED APIs")
