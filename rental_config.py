"""Configuration management for the Rental Value Analyzer."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration."""
    
    # API Keys
    CENSUS_API_KEY = 'd89f2308a0eef3819958d4afe09eb6673a96121e'
    FRED_API_KEY = 'eb9f52a46863eceb6c89aaffb5fedc3c'
    CITY_DATA_API_KEY = os.getenv('CITY_DATA_API_KEY')
    
    # Default settings
    DEFAULT_STATE = os.getenv('DEFAULT_STATE', 'CA')
    DEFAULT_CITY = os.getenv('DEFAULT_CITY', 'Los Angeles')
    
    # California city coordinates for mapping
    CITY_CENTERS = {
        'Los Angeles': (34.0522, -118.2437),
        'San Francisco': (37.7749, -122.4194),
        'San Diego': (32.7157, -117.1611),
        'San Jose': (37.3382, -121.8863),
        'Oakland': (37.8044, -122.2712),
    }
    
    # Census API endpoints
    CENSUS_BASE_URL = "https://api.census.gov/data"
    CENSUS_YEAR = 2021
    
    # FRED API settings
    FRED_BASE_URL = "https://api.stlouisfed.org/fred"
    
    # OpenStreetMap settings
    OSM_NOMINATIM_URL = "https://nominatim.openstreetmap.org"
    OSM_USER_AGENT = "rental-value-analyzer"
    
    # Cache settings
    CACHE_DIR = "data/cache"
    CACHE_EXPIRY_DAYS = 7
    
    # Analysis parameters
    AMENITY_WEIGHTS = {
        'schools': 0.25,
        'transit': 0.20,
        'restaurants': 0.15,
        'parks': 0.15,
        'hospitals': 0.10,
        'shopping': 0.15
    }
    
    # Visualization settings
    MAP_DEFAULT_ZOOM = 12
    COLOR_SCHEME = 'Viridis'
    
    @classmethod
    def validate(cls):
        """Validate that required API keys are present."""
        missing_keys = []
        if not cls.CENSUS_API_KEY:
            missing_keys.append('CENSUS_API_KEY')
        if not cls.FRED_API_KEY:
            missing_keys.append('FRED_API_KEY')
        
        if missing_keys:
            return False, missing_keys
        return True, []
