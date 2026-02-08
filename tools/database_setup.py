"""
Database Setup - DuckDB initialization and data loading

Purpose: 
- Load healthcare facility data into DuckDB for fast SQL queries
- Create structured tables for facilities, specialties, and capabilities

Why DuckDB?
- Fast analytics queries (10-100x faster than traditional databases)
- No server needed (runs in-process)
- Perfect for 987 facilities dataset
"""

import duckdb
import pandas as pd
from pathlib import Path
import json


class HealthcareDatabase:
    """Manages DuckDB database for healthcare facilities"""
    
    def __init__(self, db_path: str = "data/healthcare.duckdb"):
        """
        Initialize database connection
        
        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """Open database connection"""
        print(f"📂 Connecting to database: {self.db_path}")
        self.conn = duckdb.connect(self.db_path)
        print("✅ Connected to database")
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("🔒 Database connection closed")
    
    def create_tables(self):
        """
        Create database schema (tables structure)
        
        Tables:
        1. facilities - Main facility information
        2. specialties - Medical specialties per facility
        3. contact_info - Phone, email, website per facility
        """
        print("\n📋 Creating database tables...")
        
        # Main facilities table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS facilities (
                facility_id VARCHAR PRIMARY KEY,
                name VARCHAR,
                organization_type VARCHAR,
                address_line1 VARCHAR,
                address_city VARCHAR,
                address_region VARCHAR,
                address_country VARCHAR,
                facility_type VARCHAR,
                description TEXT,
                source_url VARCHAR
            )
        """)
        print("  ✅ Created 'facilities' table")
        
        # Specialties table (one facility can have multiple specialties)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS specialties (
                id INTEGER PRIMARY KEY,
                facility_id VARCHAR,
                specialty VARCHAR,
                FOREIGN KEY (facility_id) REFERENCES facilities(facility_id)
            )
        """)
        print("  ✅ Created 'specialties' table")
        
        # Contact information table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS contact_info (
                facility_id VARCHAR PRIMARY KEY,
                phone_numbers VARCHAR,
                email VARCHAR,
                website VARCHAR,
                FOREIGN KEY (facility_id) REFERENCES facilities(facility_id)
            )
        """)
        print("  ✅ Created 'contact_info' table")
        
        print("✅ All tables created successfully\n")
    
    def load_data_from_excel(self, excel_path: str):
        """
        Load data from Excel file into DuckDB
        
        Args:
            excel_path: Path to Excel file
        """
        print(f"📖 Loading data from: {excel_path}")
        
        # Read Excel file
        df = pd.read_excel(excel_path, engine='openpyxl')
        print(f"  ✅ Loaded {len(df)} facilities from Excel")
        
        # Insert into facilities table
        print("\n📥 Inserting data into 'facilities' table...")
        facilities_df = df[[
            'unique_id', 'name', 'organization_type', 
            'address_line1', 'address_city', 'address_stateOrRegion',
            'address_country', 'facilityTypeId', 'description', 'source_url'
        ]].copy()
        
        facilities_df.columns = [
            'facility_id', 'name', 'organization_type',
            'address_line1', 'address_city', 'address_region',
            'address_country', 'facility_type', 'description', 'source_url'
        ]
        
        # Convert to string to avoid type issues
        facilities_df = facilities_df.fillna('')
        
        self.conn.execute("DELETE FROM facilities")  # Clear existing data
        self.conn.register('facilities_temp', facilities_df)
        self.conn.execute("""
            INSERT INTO facilities 
            SELECT * FROM facilities_temp
        """)
        print(f"  ✅ Inserted {len(facilities_df)} facilities")
        
        # Insert contact information
        print("\n📥 Inserting data into 'contact_info' table...")
        contact_df = df[[
            'unique_id', 'phone_numbers', 'email', 'officialWebsite'
        ]].copy()
        contact_df.columns = ['facility_id', 'phone_numbers', 'email', 'website']
        contact_df = contact_df.fillna('')
        
        self.conn.execute("DELETE FROM contact_info")
        self.conn.register('contact_temp', contact_df)
        self.conn.execute("""
            INSERT INTO contact_info
            SELECT * FROM contact_temp
        """)
        print(f"  ✅ Inserted {len(contact_df)} contact records")
        
        # Parse and insert specialties
        print("\n📥 Parsing and inserting specialties...")
        specialties_data = []
        spec_id = 1
        
        for idx, row in df.iterrows():
            facility_id = row['unique_id']
            specialties_str = row.get('specialties', '')
            
            if pd.notna(specialties_str) and specialties_str:
                try:
                    # Parse JSON array of specialties
                    specialties_list = json.loads(specialties_str)
                    for specialty in specialties_list:
                        specialties_data.append({
                            'id': spec_id,
                            'facility_id': facility_id,
                            'specialty': specialty
                        })
                        spec_id += 1
                except (json.JSONDecodeError, TypeError):
                    # Handle non-JSON format
                    pass
        
        if specialties_data:
            specialties_df = pd.DataFrame(specialties_data)
            self.conn.execute("DELETE FROM specialties")
            self.conn.register('specialties_temp', specialties_df)
            self.conn.execute("""
                INSERT INTO specialties
                SELECT * FROM specialties_temp
            """)
            print(f"  ✅ Inserted {len(specialties_data)} specialty records")
        else:
            print("  ⚠️  No specialties found to insert")
        
        print("\n✅ All data loaded successfully!")
    
    def get_statistics(self):
        """Get database statistics"""
        print("\n" + "="*60)
        print("DATABASE STATISTICS")
        print("="*60)
        
        # Total facilities
        result = self.conn.execute("SELECT COUNT(*) FROM facilities").fetchone()
        print(f"Total Facilities: {result[0]}")
        
        # By organization type
        result = self.conn.execute("""
            SELECT organization_type, COUNT(*) as count
            FROM facilities
            GROUP BY organization_type
        """).fetchall()
        print("\nBy Organization Type:")
        for org_type, count in result:
            print(f"  - {org_type}: {count}")
        
        # By city (top 5)
        result = self.conn.execute("""
            SELECT address_city, COUNT(*) as count
            FROM facilities
            WHERE address_city != ''
            GROUP BY address_city
            ORDER BY count DESC
            LIMIT 5
        """).fetchall()
        print("\nTop 5 Cities:")
        for city, count in result:
            print(f"  - {city}: {count}")
        
        # Specialties count
        result = self.conn.execute("SELECT COUNT(*) FROM specialties").fetchone()
        print(f"\nTotal Specialty Records: {result[0]}")
        
        print("="*60 + "\n")


def main():
    """Main function to initialize database"""
    print("🚀 Healthcare Database Setup")
    print("="*60)
    
    # Initialize database
    db = HealthcareDatabase()
    db.connect()
    
    try:
        # Create tables
        db.create_tables()
        
        # Load data
        excel_path = "data/ghana_facilities.xlsx"
        if Path(excel_path).exists():
            db.load_data_from_excel(excel_path)
            db.get_statistics()
        else:
            print(f"❌ Excel file not found: {excel_path}")
            print("   Please ensure the file exists before running setup.")
        
    finally:
        db.close()
    
    print("✅ Database setup complete!")


if __name__ == "__main__":
    main()
