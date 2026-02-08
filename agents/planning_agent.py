"""
Planning Agent - Generate Resource Allocation Plans

Purpose: Creates actionable plans to address healthcare gaps
Recommends facility placement, resource allocation, partnerships

Works WITHOUT API keys - uses analytics and heuristics
"""

import duckdb
from typing import List, Dict, Any
from collections import defaultdict


class PlanningAgent:
    """Agent that generates healthcare resource allocation plans"""
    
    def __init__(self, db_path: str = "data/healthcare.duckdb"):
        """Initialize Planning Agent"""
        self.db_path = db_path
        self.conn = duckdb.connect(db_path, read_only=True)
        print("✅ Planning Agent initialized")
    
    def prioritize_cities(self, min_facilities: int = 3) -> List[Dict[str, Any]]:
        """
        Prioritize cities for intervention based on need
        
        Args:
            min_facilities: Threshold for adequate coverage
        
        Returns:
            Prioritized list of cities needing intervention
        """
        query = f"""
            SELECT 
                address_city,
                address_region,
                COUNT(*) as current_facilities,
                COUNT(DISTINCT CASE WHEN organization_type = 'facility' THEN facility_id END) as healthcare_facilities,
                COUNT(DISTINCT CASE WHEN organization_type = 'ngo' THEN facility_id END) as ngos,
                {min_facilities} - COUNT(*) as facility_gap
            FROM facilities
            WHERE address_city != ''
            GROUP BY address_city, address_region
            HAVING COUNT(*) < {min_facilities}
            ORDER BY COUNT(*) ASC, address_city
        """
        
        results = self.conn.execute(query).fetchdf()
        
        # Add priority score (1 = highest priority)
        results['priority_score'] = results.apply(
            lambda row: 1 if row['current_facilities'] == 0 
                       else 2 if row['current_facilities'] == 1 
                       else 3,
            axis=1
        )
        
        return results.to_dict('records')
    
    def find_nearby_facilities(self, target_city: str, max_distance_km: int = 50) -> List[Dict[str, Any]]:
        """
        Find facilities near a target city (for partnership opportunities)
        
        Args:
            target_city: City needing intervention
            max_distance_km: Maximum distance to search
        
        Returns:
            Nearby facilities that could provide support
        """
        # For now, find facilities in same region
        query = f"""
            SELECT 
                f.name,
                f.address_city,
                f.address_region,
                f.organization_type,
                f.facility_type,
                COUNT(s.specialty) as specialty_count
            FROM facilities f
            LEFT JOIN specialties s ON f.facility_id = s.facility_id
            WHERE f.address_region = (
                SELECT address_region 
                FROM facilities 
                WHERE LOWER(address_city) = LOWER('{target_city}')
                LIMIT 1
            )
            AND LOWER(f.address_city) != LOWER('{target_city}')
            GROUP BY f.name, f.address_city, f.address_region, f.organization_type, f.facility_type
            ORDER BY specialty_count DESC
            LIMIT 10
        """
        
        results = self.conn.execute(query).fetchdf()
        return results.to_dict('records')
    
    def recommend_specialty_deployment(self, specialty_keyword: str) -> Dict[str, Any]:
        """
        Recommend where to deploy specialists
        
        Args:
            specialty_keyword: Medical specialty to deploy
        
        Returns:
            Recommended cities and rationale
        """
        # Find cities WITHOUT this specialty
        query = f"""
            WITH cities_with_specialty AS (
                SELECT DISTINCT f.address_city
                FROM facilities f
                JOIN specialties s ON f.facility_id = s.facility_id
                WHERE LOWER(s.specialty) LIKE '%{specialty_keyword.lower()}%'
            ),
            all_cities AS (
                SELECT 
                    address_city,
                    address_region,
                    COUNT(*) as total_facilities
                FROM facilities
                WHERE address_city != ''
                GROUP BY address_city, address_region
            )
            SELECT 
                ac.address_city,
                ac.address_region,
                ac.total_facilities
            FROM all_cities ac
            LEFT JOIN cities_with_specialty cws ON ac.address_city = cws.address_city
            WHERE cws.address_city IS NULL
            ORDER BY ac.total_facilities DESC
            LIMIT 20
        """
        
        results = self.conn.execute(query).fetchdf()
        
        return {
            "specialty": specialty_keyword,
            "recommended_cities": results.to_dict('records'),
            "deployment_strategy": f"Deploy {specialty_keyword} specialists to cities with existing infrastructure but lacking this specialty"
        }
    
    def generate_action_plan(self, target_city: str) -> Dict[str, Any]:
        """
        Generate comprehensive action plan for a specific city
        
        Args:
            target_city: City to create plan for
        
        Returns:
            Detailed action plan
        """
        print(f"\n📋 Generating action plan for: {target_city}")
        print("="*70)
        
        # Get current situation
        current_query = f"""
            SELECT 
                COUNT(*) as current_facilities,
                COUNT(DISTINCT organization_type) as org_types,
                COUNT(DISTINCT CASE WHEN organization_type = 'facility' THEN 1 END) as healthcare_count,
                COUNT(DISTINCT CASE WHEN organization_type = 'ngo' THEN 1 END) as ngo_count,
                address_region
            FROM facilities
            WHERE LOWER(address_city) = LOWER('{target_city}')
            GROUP BY address_region
        """
        
        current = self.conn.execute(current_query).fetchdf()
        
        if len(current) == 0:
            return {
                "city": target_city,
                "status": "No existing facilities found",
                "recommendations": ["Conduct needs assessment", "Build new primary care facility"]
            }
        
        current_info = current.iloc[0].to_dict()
        
        # Find nearby facilities for partnerships
        nearby = self.find_nearby_facilities(target_city)
        
        # Generate recommendations
        recommendations = []
        
        if current_info['current_facilities'] == 0:
            recommendations.append("🏗️  Priority 1: Build new primary healthcare facility")
            recommendations.append("🤝 Priority 2: Partner with nearby NGOs for interim services")
        elif current_info['current_facilities'] < 3:
            recommendations.append("📈 Priority 1: Expand existing facility capacity")
            recommendations.append("🏥 Priority 2: Add specialized services (cardiology, pediatrics)")
            recommendations.append("🚑 Priority 3: Establish emergency services")
        
        if current_info['ngo_count'] == 0 and len(nearby) > 0:
            recommendations.append(f"🤝 Partner with NGOs from nearby cities: {', '.join([n['address_city'] for n in nearby[:3]])}")
        
        # Specialty recommendations
        recommendations.append("💉 Deploy mobile health units for underserved areas")
        recommendations.append("📱 Implement telemedicine infrastructure")
        recommendations.append("👨‍⚕️  Recruit and train community health workers")
        
        return {
            "city": target_city,
            "region": current_info['address_region'],
            "current_facilities": int(current_info['current_facilities']),
            "healthcare_facilities": int(current_info['healthcare_count']),
            "ngos": int(current_info['ngo_count']),
            "assessment": "Critical" if current_info['current_facilities'] < 2 else "Moderate need",
            "recommendations": recommendations,
            "nearby_partners": nearby[:5],
            "estimated_timeline": "6-12 months for initial deployment",
            "estimated_cost": f"${100000 * (3 - current_info['current_facilities']):,}" if current_info['current_facilities'] < 3 else "Minimal - focus on optimization"
        }
    
    def create_regional_plan(self, region: str = None) -> Dict[str, Any]:
        """
        Create comprehensive plan for entire region
        
        Args:
            region: Region name (if None, analyze all)
        
        Returns:
            Regional development plan
        """
        print(f"\n🗺️  Creating regional plan for: {region or 'ALL REGIONS'}")
        print("="*70)
        
        if region:
            query = f"""
                SELECT 
                    address_city,
                    COUNT(*) as facilities,
                    COUNT(DISTINCT CASE WHEN organization_type = 'ngo' THEN 1 END) as ngos
                FROM facilities
                WHERE LOWER(address_region) = LOWER('{region}')
                AND address_city != ''
                GROUP BY address_city
                ORDER BY facilities ASC
            """
        else:
            query = """
                SELECT 
                    address_region as region,
                    COUNT(DISTINCT address_city) as cities,
                    COUNT(*) as total_facilities,
                    SUM(CASE WHEN organization_type = 'ngo' THEN 1 ELSE 0 END) as ngos,
                    AVG(CASE WHEN organization_type = 'facility' THEN 1.0 ELSE 0 END) * 100 as facility_percentage
                FROM facilities
                WHERE address_region != ''
                GROUP BY address_region
                ORDER BY total_facilities ASC
            """
        
        results = self.conn.execute(query).fetchdf()
        
        return {
            "region": region or "National",
            "coverage_analysis": results.to_dict('records'),
            "priority_actions": [
                "Focus on underserved cities identified in analysis",
                "Establish referral networks between cities",
                "Deploy mobile clinics to remote areas",
                "Partner with existing NGOs for service expansion"
            ]
        }
    
    def format_plan(self, plan: Dict[str, Any]) -> str:
        """Format action plan as readable text"""
        lines = []
        lines.append("="*70)
        lines.append(f"ACTION PLAN: {plan['city'].upper()}")
        lines.append("="*70)
        lines.append(f"\n📍 Location: {plan['region']}")
        lines.append(f"📊 Current Status: {plan['assessment']}")
        lines.append(f"   - Healthcare Facilities: {plan['healthcare_facilities']}")
        lines.append(f"   - NGOs: {plan['ngos']}")
        lines.append(f"   - Total: {plan['current_facilities']}")
        
        lines.append(f"\n💡 RECOMMENDATIONS:")
        for i, rec in enumerate(plan['recommendations'], 1):
            lines.append(f"   {i}. {rec}")
        
        if plan['nearby_partners']:
            lines.append(f"\n🤝 NEARBY PARTNERSHIP OPPORTUNITIES:")
            for partner in plan['nearby_partners']:
                lines.append(f"   - {partner['name']} in {partner['address_city']}")
        
        lines.append(f"\n⏱️  Timeline: {plan['estimated_timeline']}")
        lines.append(f"💰 Estimated Cost: {plan['estimated_cost']}")
        lines.append("="*70)
        
        return "\n".join(lines)
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Test the Planning Agent"""
    print("📋 PLANNING AGENT TEST")
    print("="*70)
    
    agent = PlanningAgent()
    
    # Test 1: Generate plan for specific city
    print("\n🎯 Test 1: Action plan for Tamale")
    plan = agent.generate_action_plan("Tamale")
    print(agent.format_plan(plan))
    
    # Test 2: Generate plan for underserved city
    print("\n🎯 Test 2: Action plan for Bawku")
    plan2 = agent.generate_action_plan("Bawku")
    print(agent.format_plan(plan2))
    
    # Test 3: Regional plan
    print("\n🎯 Test 3: Regional plan")
    regional = agent.create_regional_plan()
    print(f"\nTop 5 underserved regions:")
    for i, region in enumerate(regional['coverage_analysis'][:5], 1):
        print(f"   {i}. {region['region']}: {region['total_facilities']} facilities across {region['cities']} cities")
    
    agent.close()
    print("\n✅ Planning Agent test complete!")


if __name__ == "__main__":
    main()
