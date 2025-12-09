"""
Neighborhood Rental Value Analyzer
Analyzes California rental neighborhoods using real data from multiple sources
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
from typing import Dict

# Census API Integration
try:
    from rental_config import Config
    from rental_api_helpers import DataEnricher
    USE_CENSUS = True
except ImportError:
    USE_CENSUS = False

# Page config
st.set_page_config(
    page_title="CA Rental Analyzer",
    page_icon="🏠",
    layout="wide"
)

# Database class
class DatabaseManager:
    def __init__(self, db_path="rental_data.db"):
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return self.conn
    
    def create_table(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS neighborhoods (
                name TEXT PRIMARY KEY,
                county TEXT,
                latitude REAL,
                longitude REAL,
                median_rent REAL,
                median_income REAL,
                population INTEGER,
                crime_rate REAL,
                restaurant_count INTEGER,
                shop_count INTEGER,
                grocery_count INTEGER,
                total_amenities INTEGER,
                amenity_score REAL,
                affordability REAL,
                safety_score REAL,
                value_score REAL,
                rank INTEGER
            )
        ''')
        self.conn.commit()
    
    def insert_data(self, df: pd.DataFrame):
        df.to_sql('neighborhoods', self.conn, if_exists='replace', index=False)
        self.conn.commit()
    
    def query_all(self):
        return pd.read_sql_query("SELECT * FROM neighborhoods ORDER BY value_score DESC", self.conn)
    
    def query_by_filters(self, county: str, max_rent: float):
        if county != "All California":
            query = "SELECT * FROM neighborhoods WHERE county = ? AND median_rent <= ? ORDER BY value_score DESC"
            return pd.read_sql_query(query, self.conn, params=(county, max_rent))
        else:
            query = "SELECT * FROM neighborhoods WHERE median_rent <= ? ORDER BY value_score DESC"
            return pd.read_sql_query(query, self.conn, params=(max_rent,))
    
    def close(self):
        if self.conn:
            self.conn.close()


def load_data():
    """Load data from CSV files."""
    try:
        rental_df = pd.read_csv('rental_prices.csv')
        amenity_df = pd.read_csv('amenities.csv')
        crime_df = pd.read_csv('crime_data.csv')
        
        # Merge datasets
        df = rental_df.merge(amenity_df, on='name', how='left')
        
        # Extract county from name
        df['county'] = df['name'].str.extract(r'\(([^)]+)\)')[0]
        
        # Merge crime data
        df = df.merge(crime_df, on='county', how='left')
        
        # Add Census data if available
        if USE_CENSUS:
            try:
                enricher = DataEnricher(Config.CENSUS_API_KEY, Config.FRED_API_KEY)
                census_data = enricher.census_fetcher.get_median_income_by_county()
                pop_data = enricher.census_fetcher.get_population_by_county()
                
                if not census_data.empty:
                    df = df.merge(
                        census_data.rename(columns={'county_name': 'county', 'median_income': 'real_median_income'}),
                        on='county',
                        how='left'
                    )
                    df['median_income'] = df['real_median_income'].fillna(75000)
                
                if not pop_data.empty:
                    df = df.merge(
                        pop_data.rename(columns={'county_name': 'county'}),
                        on='county',
                        how='left'
                    )
            except:
                df['median_income'] = 75000
                df['population'] = 500000
        else:
            df['median_income'] = 75000
            df['population'] = 500000
        
        return df
        
    except FileNotFoundError:
        st.error("Data files not found. Please run fetch_data.py first.")
        st.stop()


def calculate_scores(df: pd.DataFrame, weights: Dict) -> pd.DataFrame:
    """Calculate affordability, amenity, safety, and value scores."""
    
    # Affordability score (lower rent-to-income ratio = better)
    df['rent_to_income_ratio'] = (df['median_rent'] * 12) / df['median_income']
    df['affordability'] = 100 - (df['rent_to_income_ratio'] * 100).clip(0, 100)
    
    # Amenity score (normalize by max)
    max_amenities = df['total_amenities'].max()
    df['amenity_score'] = (df['total_amenities'] / max_amenities * 100).fillna(0)
    
    # Safety score (inverse of crime rate, normalized)
    df['crime_rate'] = df['crime_rate'].fillna(df['crime_rate'].median())
    max_crime = df['crime_rate'].max()
    df['safety_score'] = 100 - (df['crime_rate'] / max_crime * 100)
    
    # Value score (weighted combination)
    df['value_score'] = (
        df['affordability'] * weights['affordability'] +
        df['amenity_score'] * weights['amenities'] +
        df['safety_score'] * weights['safety']
    )
    
    df = df.sort_values('value_score', ascending=False)
    df['rank'] = range(1, len(df) + 1)
    
    return df


def main():
    # Title
    st.title("California Rental Value Analyzer")
    st.markdown("Comprehensive analysis of rental neighborhoods across California")
    
    # Load data
    df = load_data()
    
    # Initialize database
    db = DatabaseManager()
    db.connect()
    db.create_table()
    
    # Sidebar
    st.sidebar.title("Filters")
    
    counties = ["All California"] + sorted(df['county'].unique().tolist())
    selected_county = st.sidebar.selectbox("County", counties)
    
    budget = st.sidebar.slider(
        "Maximum Monthly Rent",
        min_value=500,
        max_value=5000,
        value=3000,
        step=100
    )
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Priorities")
    
    aff_weight = st.sidebar.slider("Affordability", 0, 100, 40) / 100
    amen_weight = st.sidebar.slider("Amenities", 0, 100, 30) / 100
    safe_weight = st.sidebar.slider("Safety (Low Crime)", 0, 100, 30) / 100
    
    total_weight = aff_weight + amen_weight + safe_weight
    if total_weight > 0:
        weights = {
            'affordability': aff_weight / total_weight,
            'amenities': amen_weight / total_weight,
            'safety': safe_weight / total_weight
        }
    else:
        weights = {'affordability': 0.4, 'amenities': 0.3, 'safety': 0.3}
    
    # Calculate scores
    df = calculate_scores(df, weights)
    
    # Store in database
    db.insert_data(df)
    
    # Filter data
    filtered_df = db.query_by_filters(selected_county, budget)
    all_df = db.query_all()
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Data Visualizations", "Top Neighborhoods", "Database Queries"])
    
    # TAB 1: VISUALIZATIONS
    with tab1:
        st.header("Market Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Rent vs Amenities scatter
            st.subheader("Rent vs Amenities")
            fig1 = px.scatter(
                filtered_df,
                x='total_amenities',
                y='median_rent',
                size='value_score',
                color='value_score',
                hover_name='name',
                labels={
                    'total_amenities': 'Total Amenities',
                    'median_rent': 'Monthly Rent ($)',
                    'value_score': 'Value Score'
                },
                color_continuous_scale='Viridis'
            )
            fig1.update_layout(height=400)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # County average rent
            st.subheader("Average Rent by County")
            county_rent = all_df.groupby('county')['median_rent'].mean().sort_values(ascending=False).head(10)
            fig2 = px.bar(
                x=county_rent.index,
                y=county_rent.values,
                labels={'x': 'County', 'y': 'Average Rent ($)'},
                color=county_rent.values,
                color_continuous_scale='Blues'
            )
            fig2.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)
        
        # Crime rate by county
        st.subheader("Crime Rate by County (Violent Crimes per 1,000 people)")
        crime_by_county = all_df.groupby('county')['crime_rate'].first().sort_values().head(15)
        fig3 = px.bar(
            x=crime_by_county.index,
            y=crime_by_county.values,
            labels={'x': 'County', 'y': 'Crime Rate'},
            color=crime_by_county.values,
            color_continuous_scale='Reds_r'
        )
        fig3.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)
        st.caption("Data source: California HCI Crime Dataset (2013)")
        
        # Amenity breakdown
        st.subheader("Amenity Breakdown by Neighborhood")
        top_neighborhoods = filtered_df.head(10)
        amenity_breakdown = []
        for _, row in top_neighborhoods.iterrows():
            amenity_breakdown.extend([
                {'Neighborhood': row['name'], 'Type': 'Restaurants', 'Count': row['restaurant_count']},
                {'Neighborhood': row['name'], 'Type': 'Shops', 'Count': row['shop_count']},
                {'Neighborhood': row['name'], 'Type': 'Groceries', 'Count': row['grocery_count']}
            ])
        
        amenity_df = pd.DataFrame(amenity_breakdown)
        fig4 = px.bar(
            amenity_df,
            x='Neighborhood',
            y='Count',
            color='Type',
            barmode='group',
            labels={'Count': 'Number of Amenities'},
            color_discrete_map={'Restaurants': '#FF6B6B', 'Shops': '#4ECDC4', 'Groceries': '#95E1D3'}
        )
        fig4.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig4, use_container_width=True)
    
    # TAB 2: TOP NEIGHBORHOODS
    with tab2:
        st.header("Top Rental Neighborhoods")
        
        if len(filtered_df) == 0:
            st.warning("No neighborhoods match your criteria. Try adjusting your filters.")
        else:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Neighborhoods Found", len(filtered_df))
            with col2:
                st.metric("Avg Rent", f"${filtered_df['median_rent'].mean():.0f}")
            with col3:
                st.metric("Avg Value Score", f"{filtered_df['value_score'].mean():.1f}")
            with col4:
                st.metric("Avg Crime Rate", f"{filtered_df['crime_rate'].mean():.1f}")
            
            st.markdown("---")
            
            # Top 10 table
            st.subheader("Ranked Neighborhoods")
            display_df = filtered_df.head(10)[[
                'rank', 'name', 'median_rent', 
                'restaurant_count', 'shop_count', 'grocery_count',
                'crime_rate', 'affordability', 'amenity_score', 
                'safety_score', 'value_score'
            ]].copy()
            
            display_df.columns = [
                'Rank', 'Neighborhood', 'Rent', 
                'Restaurants', 'Shops', 'Groceries',
                'Crime Rate', 'Afford Score', 'Amenity Score',
                'Safety Score', 'Value Score'
            ]
            
            st.dataframe(
                display_df.style.format({
                    'Rent': '${:.0f}',
                    'Crime Rate': '{:.2f}',
                    'Afford Score': '{:.1f}',
                    'Amenity Score': '{:.1f}',
                    'Safety Score': '{:.1f}',
                    'Value Score': '{:.1f}'
                }),
                use_container_width=True,
                hide_index=True
            )
    
    # TAB 3: SQL QUERIES
    with tab3:
        st.header("Database Queries")
        st.markdown("SQL queries powering this analysis")
        
        st.subheader("Active Filter Query")
        if selected_county != "All California":
            sql = f"""SELECT * FROM neighborhoods
WHERE county = '{selected_county}' 
  AND median_rent <= {budget}
ORDER BY value_score DESC"""
        else:
            sql = f"""SELECT * FROM neighborhoods
WHERE median_rent <= {budget}
ORDER BY value_score DESC"""
        
        st.code(sql, language='sql')
        st.info(f"Query returned {len(filtered_df)} results")
        
        st.markdown("---")
        
        st.subheader("County Aggregation Query")
        agg_sql = """SELECT 
    county,
    COUNT(*) as neighborhood_count,
    AVG(median_rent) as avg_rent,
    AVG(crime_rate) as avg_crime_rate,
    AVG(value_score) as avg_value_score
FROM neighborhoods
GROUP BY county
ORDER BY avg_value_score DESC"""
        
        st.code(agg_sql, language='sql')
        
        county_stats = pd.read_sql_query(agg_sql, db.conn)
        st.dataframe(
            county_stats.style.format({
                'avg_rent': '${:.0f}',
                'avg_crime_rate': '{:.2f}',
                'avg_value_score': '{:.1f}'
            }),
            use_container_width=True,
            hide_index=True
        )
    
    db.close()
    
    # Footer
    st.markdown("---")
    st.caption("Data sources: RentCast API, OpenStreetMap, US Census Bureau, California HCI Crime Data (2013)")


if __name__ == "__main__":
    main()