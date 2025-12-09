# California Rental Value Analyzer

Analyzes rental neighborhoods across California using real data from multiple APIs.

## Files You Need

1. **RentalAnalyzer.py** - Main Streamlit app
2. **setup_data_fetch.py** - One-time data fetching script
3. **rental_config.py** - API configuration (with your Census/FRED keys)
4. **rental_api_helpers.py** - API helper functions
5. **CSV files** - Sample data (rental_prices.csv, amenities.csv, crime_data.csv)

## Setup

### Step 1: Get RentCast API Key
1. Sign up at https://app.rentcast.io/app/api
2. Get your free API key (50 calls/month)
3. Open `fetch_data.py` and add your key on line 11

### Step 2: Run Data Fetcher (ONE TIME)
```bash
python3 setup_data_fetch.py
```

This will:
- Call RentCast API for 45 neighborhoods (uses 45 of your 50 free calls)
- Call OpenStreetMap API for amenity counts (FREE, unlimited)
- Process crime data from Excel file
- Save everything to CSV files

### Step 3: Run the App
```bash
streamlit run RentalAnalyzer.py
```

## Data Sources

**Real data:**
- Rental prices: RentCast API
- Amenity counts: OpenStreetMap Overpass API
- Crime rates: California HCI Crime Dataset (2013)
- Demographics: US Census Bureau API (optional, if config.py present)

**45 Neighborhoods:**
- 15 Los Angeles
- 12 San Francisco
- 10 San Diego
- 8 San Jose

## Features

### Tab 1: Data Visualizations
- Scatter plot: Rent vs Amenities
- Bar chart: Average rent by county
- Bar chart: Crime rates by county

### Tab 2: Top Neighborhoods
- Ranked list based on your filters
- Adjustable weights for affordability, amenities, safety
- Filter by county and budget

### Tab 3: Database Queries
- See actual SQL queries being used
- SQLite database powers all filtering
- County aggregation statistics

## Notes

- RentCast free tier = 50 calls/month
- We use 45 calls for neighborhoods, leaving 5 for testing
- Data is cached in CSV files so app runs fast
- Census API integration is optional (requires rental_config.py)
- Crime data is from 2013 (most recent public dataset)
