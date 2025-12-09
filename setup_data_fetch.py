"""
Update Amenities Data - Fetches fresh OpenStreetMap data
Run this to refresh amenity counts without touching rent or crime data
"""
import requests
import pandas as pd
import time

# 45 California Neighborhoods
NEIGHBORHOODS = {
    'Los Angeles': [
        ("Hollywood", 34.0928, -118.3287),
        ("Santa Monica", 34.0195, -118.4912),
        ("Venice", 33.9850, -118.4695),
        ("Downtown LA", 34.0522, -118.2437),
        ("Silver Lake", 34.0870, -118.2704),
        ("Culver City", 34.0211, -118.3965),
        ("Pasadena", 34.1478, -118.1445),
        ("West Hollywood", 34.0900, -118.3617),
        ("Koreatown", 34.0579, -118.3009),
        ("Beverly Hills", 34.0736, -118.4004),
        ("Long Beach", 33.7701, -118.1937),
        ("Burbank", 34.1808, -118.3090),
        ("Westwood", 34.0633, -118.4456),
        ("Brentwood", 34.0536, -118.4772),
        ("Manhattan Beach", 33.8847, -118.4109),
    ],
    'San Francisco': [
        ("Mission District", 37.7599, -122.4148),
        ("SoMa", 37.7749, -122.4194),
        ("Castro", 37.7609, -122.4350),
        ("Pacific Heights", 37.7931, -122.4358),
        ("Marina District", 37.8024, -122.4381),
        ("Nob Hill", 37.7919, -122.4155),
        ("Richmond District", 37.7787, -122.4645),
        ("Sunset District", 37.7479, -122.4822),
        ("Potrero Hill", 37.7578, -122.3979),
        ("Haight-Ashbury", 37.7692, -122.4481),
        ("North Beach", 37.8006, -122.4104),
        ("Chinatown", 37.7941, -122.4078),
    ],
    'San Diego': [
        ("Gaslamp Quarter", 32.7115, -117.1597),
        ("La Jolla", 32.8328, -117.2713),
        ("Pacific Beach", 32.7967, -117.2357),
        ("Hillcrest", 32.7486, -117.1664),
        ("North Park", 32.7411, -117.1297),
        ("Little Italy", 32.7209, -117.1698),
        ("Ocean Beach", 32.7475, -117.2489),
        ("Point Loma", 32.7341, -117.2407),
        ("Mission Bay", 32.7642, -117.2267),
        ("Del Mar", 32.9595, -117.2653),
    ],
    'San Jose': [
        ("Downtown San Jose", 37.3382, -121.8863),
        ("Willow Glen", 37.3044, -121.8896),
        ("Santana Row", 37.3207, -121.9483),
        ("Japantown", 37.3469, -121.8950),
        ("Rose Garden", 37.3399, -121.9190),
        ("Almaden Valley", 37.2091, -121.8355),
        ("Cambrian Park", 37.2527, -121.9297),
        ("Evergreen", 37.3155, -121.7906),
    ],
}


def fetch_osm_amenities() -> pd.DataFrame:
    """Fetch amenity counts from OpenStreetMap."""
    print("Fetching amenity data from OpenStreetMap...")
    print("This will take about 5-10 minutes (3 API calls per neighborhood)...\n")
    results = []
    
    total = sum(len(neighborhoods) for neighborhoods in NEIGHBORHOODS.values())
    count = 0
    
    for city, neighborhoods in NEIGHBORHOODS.items():
        for name, lat, lon in neighborhoods:
            count += 1
            print(f"[{count}/{total}] {name}...")
            
            try:
                # Count restaurants
                restaurant_query = f"""
                [out:json][timeout:25];
                (
                  node["amenity"="restaurant"](around:1000,{lat},{lon});
                  way["amenity"="restaurant"](around:1000,{lat},{lon});
                );
                out count;
                """
                
                # Count shops
                shop_query = f"""
                [out:json][timeout:25];
                (
                  node["shop"](around:1000,{lat},{lon});
                  way["shop"](around:1000,{lat},{lon});
                );
                out count;
                """
                
                # Count grocery stores
                grocery_query = f"""
                [out:json][timeout:25];
                (
                  node["shop"="supermarket"](around:1000,{lat},{lon});
                  way["shop"="supermarket"](around:1000,{lat},{lon});
                );
                out count;
                """
                
                overpass_url = "http://overpass-api.de/api/interpreter"
                
                # Get restaurant count
                response = requests.get(overpass_url, params={'data': restaurant_query}, timeout=30)
                restaurants = 0
                if response.status_code == 200:
                    data = response.json()
                    if 'elements' in data and len(data['elements']) > 0:
                        restaurants = data['elements'][0].get('tags', {}).get('total', 0)
                time.sleep(1)
                
                # Get shop count
                response = requests.get(overpass_url, params={'data': shop_query}, timeout=30)
                shops = 0
                if response.status_code == 200:
                    data = response.json()
                    if 'elements' in data and len(data['elements']) > 0:
                        shops = data['elements'][0].get('tags', {}).get('total', 0)
                time.sleep(1)
                
                # Get grocery count
                response = requests.get(overpass_url, params={'data': grocery_query}, timeout=30)
                groceries = 0
                if response.status_code == 200:
                    data = response.json()
                    if 'elements' in data and len(data['elements']) > 0:
                        groceries = data['elements'][0].get('tags', {}).get('total', 0)
                time.sleep(1)
                
                total_amenities = restaurants + shops + groceries
                
                results.append({
                    'name': f"{name} ({city})",
                    'restaurant_count': restaurants,
                    'shop_count': shops,
                    'grocery_count': groceries,
                    'total_amenities': total_amenities
                })
                
                print(f"  -> Restaurants: {restaurants}, Shops: {shops}, Groceries: {groceries}, Total: {total_amenities}")
                
            except Exception as e:
                print(f"  -> ERROR: {e}")
                results.append({
                    'name': f"{name} ({city})",
                    'restaurant_count': 0,
                    'shop_count': 0,
                    'grocery_count': 0,
                    'total_amenities': 0
                })
    
    df = pd.DataFrame(results)
    df.to_csv('amenities.csv', index=False)
    print(f"\n✓ Saved amenity data for {len(df)} neighborhoods to amenities.csv")
    return df


if __name__ == "__main__":
    print("=" * 60)
    print("AMENITY DATA UPDATER")
    print("=" * 60)
    print("\nThis will fetch fresh amenity counts from OpenStreetMap")
    print("for all 45 neighborhoods.\n")
    print("Note: This takes 5-10 minutes due to API rate limiting.")
    print("=" * 60)
    
    choice = input("\nProceed? (yes/no): ")
    
    if choice.lower() == 'yes':
        amenity_df = fetch_osm_amenities()
        
        print("\n" + "=" * 60)
        print("AMENITY UPDATE COMPLETE!")
        print("=" * 60)
        print("\nUpdated file: amenities.csv")
        print("\nYou can now run: streamlit run RentalAnalyzer.py")
    else:
        print("Cancelled.")