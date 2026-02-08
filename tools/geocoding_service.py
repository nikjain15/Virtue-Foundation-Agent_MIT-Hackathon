"""
Geocoding Service - Convert addresses to coordinates

Purpose: Get latitude/longitude for all facilities to show on map
Uses: Nominatim (OpenStreetMap) - free, no API key needed
"""

import pandas as pd
import time
import json
from pathlib import Path
import requests
from typing import Tuple, Optional


class GeocodingService:
    """Handle geocoding of addresses to coordinates"""
    
    def __init__(self, cache_file: str = "data/geocoding_cache.json"):
        """
        Initialize geocoding service
        
        Args:
            cache_file: Path to cache file (avoid repeated API calls)
        """
        self.cache_file = cache_file
        self.cache = self._load_cache()
        self.base_url = "https://nominatim.openstreetmap.org/search"
        
    def _load_cache(self) -> dict:
        """Load cached geocoding results"""
        if Path(self.cache_file).exists():
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_cache(self):
        """Save geocoding cache to file"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def geocode_address(self, city: str, country: str = "Ghana") -> Optional[Tuple[float, float]]:
        """
        Convert city name to coordinates (latitude, longitude)
        
        Args:
            city: City name
            country: Country name (default: Ghana)
        
        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        # Check cache first
        cache_key = f"{city}, {country}"
        if cache_key in self.cache:
            coords = self.cache[cache_key]
            if coords:
                return tuple(coords)
            return None
        
        # Call geocoding API
        try:
            params = {
                'city': city,
                'country': country,
                'format': 'json',
                'limit': 1
            }
            headers = {
                'User-Agent': 'HealthcareFacilityMapper/1.0'  # Required by Nominatim
            }
            
            response = requests.get(self.base_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            results = response.json()
            
            if results and len(results) > 0:
                lat = float(results[0]['lat'])
                lon = float(results[0]['lon'])
                coords = (lat, lon)
                
                # Cache result
                self.cache[cache_key] = coords
                self._save_cache()
                
                print(f"  ✅ {city}: ({lat:.4f}, {lon:.4f})")
                return coords
            else:
                # Cache negative result to avoid repeated lookups
                self.cache[cache_key] = None
                self._save_cache()
                print(f"  ❌ {city}: Not found")
                return None
                
        except Exception as e:
            print(f"  ⚠️  {city}: Error - {str(e)}")
            return None
    
    def geocode_dataframe(self, df: pd.DataFrame, city_column: str = 'address_city') -> pd.DataFrame:
        """
        Add latitude/longitude columns to dataframe
        
        Args:
            df: DataFrame with city column
            city_column: Name of column containing city names
        
        Returns:
            DataFrame with added 'latitude' and 'longitude' columns
        """
        print(f"🌍 Geocoding {len(df)} facilities...")
        print("="*60)
        
        # Get unique cities
        cities = df[city_column].dropna().unique()
        print(f"Found {len(cities)} unique cities\n")
        
        # Geocode each city
        coords_map = {}
        for i, city in enumerate(cities, 1):
            if city == '':
                continue
            
            print(f"[{i}/{len(cities)}] Geocoding: {city}")
            coords = self.geocode_address(city)
            coords_map[city] = coords
            
            # Rate limiting: 1 request per second (Nominatim requirement)
            time.sleep(1)
        
        print("\n" + "="*60)
        print(f"✅ Geocoding complete!")
        successful = sum(1 for v in coords_map.values() if v is not None)
        print(f"   Success: {successful}/{len(cities)} cities ({successful/len(cities)*100:.1f}%)")
        
        # Add coordinates to dataframe
        df['latitude'] = df[city_column].map(lambda city: coords_map.get(city, (None, None))[0] if coords_map.get(city) else None)
        df['longitude'] = df[city_column].map(lambda city: coords_map.get(city, (None, None))[1] if coords_map.get(city) else None)
        
        return df


def main():
    """Test geocoding service"""
    import duckdb
    
    print("🧪 Testing Geocoding Service")
    print("="*60)
    
    # Connect to database
    conn = duckdb.connect("data/healthcare.duckdb", read_only=True)
    
    # Get facilities
    df = conn.execute("""
        SELECT facility_id, name, address_city
        FROM facilities
        WHERE address_city != ''
        LIMIT 20
    """).df()
    
    print(f"Loaded {len(df)} test facilities\n")
    
    # Geocode
    geocoder = GeocodingService()
    df = geocoder.geocode_dataframe(df)
    
    # Show results
    print("\nResults:")
    print(df[['name', 'address_city', 'latitude', 'longitude']].to_string())
    
    conn.close()


if __name__ == "__main__":
    main()
