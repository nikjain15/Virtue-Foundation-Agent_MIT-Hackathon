"""
Geocode All Facilities - Add coordinates to database

Purpose: Geocode all 987 facilities and store coordinates in database
"""

import duckdb
import pandas as pd
import sys
sys.path.append('.')
from tools.geocoding_service import GeocodingService


def main():
    print("🗺️ GEOCODING ALL FACILITIES")
    print("="*70)
    
    # Connect to database
    print("\n📂 Connecting to database...")
    conn = duckdb.connect("data/healthcare.duckdb")
    
    # Get all facilities
    print("📥 Loading facilities from database...")
    df = conn.execute("""
        SELECT facility_id, name, address_city, address_country
        FROM facilities
        WHERE address_city != ''
    """).df()
    
    print(f"✅ Loaded {len(df)} facilities with city information\n")
    
    # Geocode
    geocoder = GeocodingService()
    df = geocoder.geocode_dataframe(df, city_column='address_city')
    
    # Count successful geocodes
    geocoded = df[df['latitude'].notna()]
    print(f"\n📊 Geocoded {len(geocoded)}/{len(df)} facilities ({len(geocoded)/len(df)*100:.1f}%)")
    
    # Add coordinates column to database
    print("\n📥 Updating database with coordinates...")
    
    # Drop existing coordinates table if exists
    conn.execute("DROP TABLE IF EXISTS facility_coordinates")
    
    # Create coordinates table
    conn.execute("""
        CREATE TABLE facility_coordinates (
            facility_id VARCHAR PRIMARY KEY,
            latitude DOUBLE,
            longitude DOUBLE,
            FOREIGN KEY (facility_id) REFERENCES facilities(facility_id)
        )
    """)
    
    # Insert coordinates
    coords_df = df[['facility_id', 'latitude', 'longitude']].copy()
    conn.register('coords_temp', coords_df)
    conn.execute("""
        INSERT INTO facility_coordinates
        SELECT * FROM coords_temp
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """)
    
    # Verify
    count = conn.execute("SELECT COUNT(*) FROM facility_coordinates").fetchone()[0]
    print(f"✅ Inserted {count} coordinate records into database")
    
    # Show sample
    print("\n📋 Sample geocoded facilities:")
    sample = conn.execute("""
        SELECT f.name, f.address_city, c.latitude, c.longitude
        FROM facilities f
        JOIN facility_coordinates c ON f.facility_id = c.facility_id
        LIMIT 5
    """).df()
    print(sample.to_string(index=False))
    
    conn.close()
    print("\n✅ Geocoding complete!")


if __name__ == "__main__":
    main()
