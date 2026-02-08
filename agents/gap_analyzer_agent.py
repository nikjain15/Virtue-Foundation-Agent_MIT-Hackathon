"""
Gap Analyzer Agent - Identify Medical Deserts

Purpose: Analyze healthcare gaps by region and specialty
Identifies areas lacking specific medical services

Works WITHOUT API keys - uses SQL analytics
"""

import duckdb
from typing import List, Dict, Any
from collections import defaultdict


class GapAnalyzerAgent:
    """Agent that identifies medical deserts and healthcare gaps"""
    
    def __init__(self, db_path: str = "data/healthcare.duckdb"):
        """Initialize Gap Analyzer Agent"""
        self.db_path = db_path
        self.conn = duckdb.connect(db_path, read_only=True)
        print("✅ Gap Analyzer Agent initialized")
    
    def analyze_specialty_gaps(self, specialty_keyword: str = None) -> Dict[str, Any]:
        """
        Analyze gaps in medical specialties across regions
        
        Args:
            specialty_keyword: Filter by specialty (e.g., 'cardio', 'pediatric')
        
        Returns:
            Dictionary with gap analysis results
        """
        print(f"\n🔍 Analyzing specialty gaps...")
        
        if specialty_keyword:
            query = f"""
                SELECT 
                    f.address_city,
                    f.address_region,
                    COUNT(DISTINCT f.facility_id) as facility_count,
                    COUNT(DISTINCT s.specialty) as specialty_count,
                    GROUP_CONCAT(DISTINCT s.specialty, ', ') as specialties
                FROM facilities f
                LEFT JOIN specialties s ON f.facility_id = s.facility_id
                WHERE LOWER(s.specialty) LIKE '%{specialty_keyword.lower()}%'
                GROUP BY f.address_city, f.address_region
                ORDER BY facility_count DESC
            """
        else:
            query = """
                SELECT 
                    f.address_city,
                    f.address_region,
                    COUNT(DISTINCT f.facility_id) as facility_count,
                    COUNT(DISTINCT s.specialty) as specialty_count
                FROM facilities f
                LEFT JOIN specialties s ON f.facility_id = s.facility_id
                WHERE f.address_city != ''
                GROUP BY f.address_city, f.address_region
                ORDER BY facility_count DESC
            """
        
        results = self.conn.execute(query).fetchdf()
        
        # Find cities with NO facilities for this specialty
        if specialty_keyword:
            all_cities_query = """
                SELECT DISTINCT address_city, address_region
                FROM facilities
                WHERE address_city != ''
            """
            all_cities = self.conn.execute(all_cities_query).fetchdf()
            
            cities_with_specialty = set(results['address_city'].tolist())
            all_cities_set = set(all_cities['address_city'].tolist())
            
            # Cities lacking this specialty
            gap_cities = all_cities_set - cities_with_specialty
            
            return {
                "specialty": specialty_keyword,
                "cities_with_coverage": len(cities_with_specialty),
                "cities_without_coverage": len(gap_cities),
                "gap_cities": sorted(list(gap_cities)),
                "coverage_details": results.to_dict('records')
            }
        else:
            return {
                "total_cities": len(results),
                "coverage_summary": results.to_dict('records')
            }
    
    def identify_medical_deserts(self, min_facilities: int = 5) -> Dict[str, Any]:
        """
        Identify medical deserts (underserved areas)
        
        Args:
            min_facilities: Minimum facilities for adequate coverage
        
        Returns:
            List of underserved cities
        """
        print(f"\n🏜️ Identifying medical deserts (cities with < {min_facilities} facilities)...")
        
        query = f"""
            SELECT 
                address_city,
                address_region,
                COUNT(*) as facility_count,
                COUNT(DISTINCT organization_type) as org_type_count
            FROM facilities
            WHERE address_city != ''
            GROUP BY address_city, address_region
            HAVING facility_count < {min_facilities}
            ORDER BY facility_count ASC
        """
        
        results = self.conn.execute(query).fetchdf()
        
        # Categorize severity
        critical = results[results['facility_count'] == 1]
        severe = results[(results['facility_count'] > 1) & (results['facility_count'] < 3)]
        moderate = results[(results['facility_count'] >= 3) & (results['facility_count'] < min_facilities)]
        
        return {
            "total_underserved_cities": len(results),
            "critical_deserts": critical.to_dict('records'),  # Only 1 facility
            "severe_deserts": severe.to_dict('records'),      # 2 facilities
            "moderate_deserts": moderate.to_dict('records'),  # 3-4 facilities
            "summary": {
                "critical": len(critical),
                "severe": len(severe),
                "moderate": len(moderate)
            }
        }
    
    def analyze_regional_coverage(self) -> Dict[str, Any]:
        """
        Analyze healthcare coverage by region
        
        Returns:
            Regional distribution of facilities
        """
        print(f"\n🗺️ Analyzing regional coverage...")
        
        query = """
            SELECT 
                COALESCE(address_region, 'Unknown') as region,
                COUNT(*) as total_facilities,
                SUM(CASE WHEN organization_type = 'facility' THEN 1 ELSE 0 END) as facilities,
                SUM(CASE WHEN organization_type = 'ngo' THEN 1 ELSE 0 END) as ngos,
                COUNT(DISTINCT address_city) as cities_covered
            FROM facilities
            GROUP BY address_region
            ORDER BY total_facilities DESC
        """
        
        results = self.conn.execute(query).fetchdf()
        
        return {
            "total_regions": len(results),
            "regional_breakdown": results.to_dict('records')
        }
    
    def get_gap_summary(self, specialty: str = None) -> str:
        """
        Get a formatted summary of healthcare gaps
        
        Args:
            specialty: Optional specialty to focus on
        
        Returns:
            Human-readable gap analysis summary
        """
        print("\n📊 Generating gap summary report...")
        print("="*70)
        
        summary_lines = []
        summary_lines.append("HEALTHCARE GAP ANALYSIS SUMMARY")
        summary_lines.append("="*70)
        
        # Regional coverage
        regional = self.analyze_regional_coverage()
        summary_lines.append(f"\n📍 REGIONAL COVERAGE:")
        summary_lines.append(f"   Total regions: {regional['total_regions']}")
        for region in regional['regional_breakdown'][:5]:
            summary_lines.append(
                f"   - {region['region']}: {region['total_facilities']} facilities "
                f"({region['cities_covered']} cities)"
            )
        
        # Medical deserts
        deserts = self.identify_medical_deserts()
        summary_lines.append(f"\n🏜️ MEDICAL DESERTS:")
        summary_lines.append(f"   Critical (1 facility): {deserts['summary']['critical']} cities")
        summary_lines.append(f"   Severe (2 facilities): {deserts['summary']['severe']} cities")
        summary_lines.append(f"   Moderate (3-4 facilities): {deserts['summary']['moderate']} cities")
        
        if deserts['critical_deserts']:
            summary_lines.append(f"\n   🚨 CRITICAL CITIES (only 1 facility):")
            for city in deserts['critical_deserts'][:10]:
                summary_lines.append(f"      - {city['address_city']}, {city['address_region']}")
        
        # Specialty gaps (if specified)
        if specialty:
            gaps = self.analyze_specialty_gaps(specialty)
            summary_lines.append(f"\n💉 SPECIALTY GAP: {specialty.upper()}")
            summary_lines.append(f"   Cities WITH coverage: {gaps['cities_with_coverage']}")
            summary_lines.append(f"   Cities WITHOUT coverage: {gaps['cities_without_coverage']}")
            
            if gaps['gap_cities']:
                summary_lines.append(f"\n   ⚠️  Cities lacking {specialty}:")
                for city in gaps['gap_cities'][:15]:
                    summary_lines.append(f"      - {city}")
        
        summary_lines.append("\n" + "="*70)
        
        return "\n".join(summary_lines)
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Test the Gap Analyzer Agent"""
    print("🔬 GAP ANALYZER AGENT TEST")
    print("="*70)
    
    agent = GapAnalyzerAgent()
    
    # Test 1: General gap summary
    print("\n" + agent.get_gap_summary())
    
    # Test 2: Cardiac care gaps
    print("\n\nAnalyzing cardiac care gaps...")
    cardiac_gaps = agent.get_gap_summary(specialty="cardio")
    print(cardiac_gaps)
    
    # Test 3: Pediatric care gaps
    print("\n\nAnalyzing pediatric care gaps...")
    pediatric_gaps = agent.get_gap_summary(specialty="pediatric")
    print(pediatric_gaps)
    
    agent.close()
    print("\n✅ Gap Analyzer Agent test complete!")


if __name__ == "__main__":
    main()
