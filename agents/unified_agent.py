"""
Unified Agent - ONE agent that does it all (simplified)

Purpose: Handle queries, gap analysis, and planning in one place
No over-complicated routing - just smart SQL + simple logic
"""

import duckdb
from typing import Dict, List, Any
from pathlib import Path


class UnifiedAgent:
    """One agent to rule them all - simplified approach"""
    
    def __init__(self, db_path: str = "data/healthcare.duckdb"):
        """Initialize unified agent with database connection"""
        self.db_path = db_path
        self.conn = duckdb.connect(db_path, read_only=True)
        print("✅ Unified Agent ready")
    
    def handle_query(self, question: str) -> Dict[str, Any]:
        """
        Main entry point - routes to appropriate handler based on question type
        
        Question types we handle:
        1. Facility queries: "How many hospitals in Accra?"
        2. Gap analysis: "Where are cardiac care gaps?"
        3. Planning: "How to fix gaps in Northern region?"
        """
        question_lower = question.lower()
        
        # Route to appropriate handler
        if any(word in question_lower for word in ['gap', 'desert', 'missing', 'need', 'lacking']):
            return self._analyze_gaps(question)
        elif any(word in question_lower for word in ['plan', 'fix', 'improve', 'deploy', 'allocate']):
            return self._generate_plan(question)
        else:
            return self._answer_facility_query(question)
    
    def _answer_facility_query(self, question: str) -> Dict[str, Any]:
        """
        Answer questions about facilities using SQL pattern matching
        
        Examples:
        - "How many hospitals in Accra?"
        - "Which facilities handle cardiac care?"
        - "Show me NGOs in Kumasi"
        """
        question_lower = question.lower()
        sql_query = None
        
        # Pattern 1: Count facilities in a location
        if "how many" in question_lower:
            # Extract location
            location = self._extract_location(question)
            if location:
                sql_query = f"""
                    SELECT COUNT(*) as count, address_city, address_region
                    FROM facilities
                    WHERE LOWER(address_city) LIKE '%{location.lower()}%'
                       OR LOWER(address_region) LIKE '%{location.lower()}%'
                    GROUP BY address_city, address_region
                """
        
        # Pattern 2: Facilities by specialty
        elif any(specialty in question_lower for specialty in ['cardiac', 'pediatric', 'surgery', 'trauma', 'maternity']):
            specialty = self._extract_specialty(question)
            sql_query = f"""
                SELECT 
                    f.name, 
                    f.address_city, 
                    f.address_region,
                    s.specialty
                FROM facilities f
                JOIN specialties s ON f.facility_id = s.facility_id
                WHERE LOWER(s.specialty) LIKE '%{specialty}%'
                LIMIT 20
            """
        
        # Pattern 3: NGO queries
        elif "ngo" in question_lower:
            location = self._extract_location(question)
            if location:
                sql_query = f"""
                    SELECT name, address_city, address_region
                    FROM facilities
                    WHERE organization_type = 'ngo'
                      AND (LOWER(address_city) LIKE '%{location.lower()}%'
                           OR LOWER(address_region) LIKE '%{location.lower()}%')
                    LIMIT 20
                """
            else:
                sql_query = """
                    SELECT name, address_city, address_region
                    FROM facilities
                    WHERE organization_type = 'ngo'
                    LIMIT 20
                """
        
        # Pattern 4: List facilities in a location
        elif "in" in question_lower:
            location = self._extract_location(question)
            if location:
                sql_query = f"""
                    SELECT name, facility_type, address_city
                    FROM facilities
                    WHERE LOWER(address_city) LIKE '%{location.lower()}%'
                       OR LOWER(address_region) LIKE '%{location.lower()}%'
                    LIMIT 20
                """
        
        # Default: Show overview
        else:
            sql_query = """
                SELECT 
                    organization_type,
                    COUNT(*) as count
                FROM facilities
                GROUP BY organization_type
            """
        
        # Execute query
        try:
            results = self.conn.execute(sql_query).fetchdf().to_dict('records')
            answer = self._format_facility_answer(question, results)
            return {
                'answer': answer,
                'data': results,
                'sql': sql_query,
                'type': 'facility_query'
            }
        except Exception as e:
            return {
                'answer': f"Error: {str(e)}",
                'data': [],
                'sql': sql_query,
                'type': 'error'
            }
    
    def _analyze_gaps(self, question: str) -> Dict[str, Any]:
        """
        Identify medical deserts and gaps
        
        Examples:
        - "Where are cardiac care gaps?"
        - "Which regions lack pediatric facilities?"
        - "Show me medical deserts"
        """
        question_lower = question.lower()
        
        # Check if looking for specific specialty
        specialty = self._extract_specialty(question)
        location = self._extract_location(question)
        
        if specialty:
            # Find regions lacking this specialty
            sql_query = f"""
                WITH specialty_coverage AS (
                    SELECT 
                        f.address_region,
                        COUNT(DISTINCT f.facility_id) as facility_count
                    FROM facilities f
                    JOIN specialties s ON f.facility_id = s.facility_id
                    WHERE LOWER(s.specialty) LIKE '%{specialty}%'
                    GROUP BY f.address_region
                ),
                all_regions AS (
                    SELECT DISTINCT address_region
                    FROM facilities
                    WHERE address_region IS NOT NULL
                )
                SELECT 
                    ar.address_region,
                    COALESCE(sc.facility_count, 0) as {specialty}_facilities
                FROM all_regions ar
                LEFT JOIN specialty_coverage sc ON ar.address_region = sc.address_region
                ORDER BY {specialty}_facilities ASC
            """
        else:
            # General coverage by region
            sql_query = """
                SELECT 
                    address_region,
                    COUNT(*) as total_facilities,
                    SUM(CASE WHEN organization_type = 'facility' THEN 1 ELSE 0 END) as healthcare_facilities,
                    SUM(CASE WHEN organization_type = 'ngo' THEN 1 ELSE 0 END) as ngos
                FROM facilities
                WHERE address_region IS NOT NULL
                GROUP BY address_region
                ORDER BY total_facilities ASC
            """
        
        try:
            results = self.conn.execute(sql_query).fetchdf().to_dict('records')
            answer = self._format_gap_answer(question, results, specialty)
            return {
                'answer': answer,
                'data': results,
                'sql': sql_query,
                'type': 'gap_analysis'
            }
        except Exception as e:
            return {
                'answer': f"Error: {str(e)}",
                'data': [],
                'sql': sql_query,
                'type': 'error'
            }
    
    def _generate_plan(self, question: str) -> Dict[str, Any]:
        """
        Generate actionable plans
        
        Examples:
        - "How to fix cardiac gaps in Northern region?"
        - "Plan to deploy doctors to Volta"
        """
        question_lower = question.lower()
        location = self._extract_location(question)
        specialty = self._extract_specialty(question)
        
        # First, identify the gaps
        gaps = self._analyze_gaps(question)
        
        # Then generate recommendations
        if location and specialty:
            plan = f"""
            🎯 PLAN: Address {specialty} care gaps in {location}
            
            Step 1: Current Situation
            {gaps['answer']}
            
            Step 2: Immediate Actions
            • Partner with nearby facilities that have {specialty} capabilities
            • Deploy mobile clinics to underserved areas
            • Train local healthcare workers in {specialty} care
            
            Step 3: Medium-term (6-12 months)
            • Establish satellite clinic in {location}
            • Recruit specialist doctors for {specialty}
            • Set up telemedicine connection to specialist centers
            
            Step 4: Long-term (1-2 years)
            • Build dedicated {specialty} ward
            • Create training program for local specialists
            • Develop regional referral network
            """
        else:
            plan = f"""
            🎯 GENERAL HEALTHCARE IMPROVEMENT PLAN
            
            Based on gap analysis, here are priority actions:
            
            1. Identify most underserved regions (see gap analysis above)
            2. Assess population needs vs. current capacity
            3. Partner with existing facilities for expansion
            4. Deploy mobile health units to medical deserts
            5. Establish telemedicine infrastructure
            6. Train community health workers
            
            For specific recommendations, ask: "How to fix [specialty] gaps in [region]?"
            """
        
        return {
            'answer': plan,
            'data': gaps['data'],
            'sql': gaps['sql'],
            'type': 'planning'
        }
    
    # Helper methods
    
    def _extract_location(self, text: str) -> str:
        """Extract location from question"""
        # Common Ghana regions and cities
        locations = [
            'accra', 'kumasi', 'tema', 'takoradi', 'tamale', 'cape coast',
            'sunyani', 'koforidua', 'ho', 'wa', 'bolgatanga',
            'greater accra', 'ashanti', 'western', 'eastern', 'northern',
            'central', 'volta', 'upper east', 'upper west', 'brong ahafo'
        ]
        
        text_lower = text.lower()
        for location in locations:
            if location in text_lower:
                return location.title()
        return None
    
    def _extract_specialty(self, text: str) -> str:
        """Extract medical specialty from question"""
        specialties = {
            'cardiac': 'cardio',
            'heart': 'cardio',
            'pediatric': 'pediatric',
            'children': 'pediatric',
            'surgery': 'surgery',
            'trauma': 'trauma',
            'emergency': 'emergency',
            'maternity': 'maternity',
            'obstetric': 'obstetric'
        }
        
        text_lower = text.lower()
        for keyword, specialty in specialties.items():
            if keyword in text_lower:
                return specialty
        return None
    
    def _format_facility_answer(self, question: str, results: List[Dict]) -> str:
        """Format facility query results into readable answer"""
        if not results:
            return "No facilities found matching your query."
        
        # Handle count queries
        if 'count' in results[0]:
            if len(results) == 1:
                count = results[0]['count']
                location = results[0].get('address_city') or results[0].get('address_region')
                return f"There are **{count} facilities** in {location}."
            else:
                answer = "Facility counts by location:\n\n"
                for row in results[:10]:
                    location = row.get('address_city') or row.get('address_region')
                    answer += f"• {location}: {row['count']} facilities\n"
                return answer
        
        # Handle facility lists
        answer = f"Found **{len(results)} facilities**:\n\n"
        for i, row in enumerate(results[:10], 1):
            name = row.get('name', 'Unknown')
            city = row.get('address_city', '')
            facility_type = row.get('facility_type', '')
            specialty = row.get('specialty', '')
            
            answer += f"**{i}. {name}**"
            if city:
                answer += f" - {city}"
            if specialty:
                answer += f" ({specialty})"
            answer += "\n"
        
        if len(results) > 10:
            answer += f"\n_...and {len(results) - 10} more_"
        
        return answer
    
    def _format_gap_answer(self, question: str, results: List[Dict], specialty: str = None) -> str:
        """Format gap analysis results"""
        if not results:
            return "No gap data available."
        
        if specialty:
            answer = f"🔍 **{specialty.title()} Care Coverage by Region:**\n\n"
            
            # Identify regions with gaps
            gaps = [r for r in results if r.get(f'{specialty}_facilities', 0) == 0]
            limited = [r for r in results if 0 < r.get(f'{specialty}_facilities', 0) < 3]
            
            if gaps:
                answer += f"❌ **No {specialty} care:**\n"
                for region in gaps[:5]:
                    answer += f"• {region['address_region']}\n"
                answer += "\n"
            
            if limited:
                answer += f"⚠️ **Limited {specialty} care (1-2 facilities):**\n"
                for region in limited[:5]:
                    count = region.get(f'{specialty}_facilities', 0)
                    answer += f"• {region['address_region']}: {count} facility/facilities\n"
                answer += "\n"
            
            # Show regions with good coverage
            good = [r for r in results if r.get(f'{specialty}_facilities', 0) >= 3]
            if good:
                answer += f"✅ **Good {specialty} coverage:**\n"
                for region in good[:3]:
                    count = region.get(f'{specialty}_facilities', 0)
                    answer += f"• {region['address_region']}: {count} facilities\n"
        else:
            answer = "📊 **Healthcare Coverage by Region:**\n\n"
            
            # Identify underserved regions
            underserved = [r for r in results if r.get('total_facilities', 0) < 10]
            
            if underserved:
                answer += "⚠️ **Underserved regions (< 10 facilities):**\n"
                for region in underserved[:10]:
                    total = region.get('total_facilities', 0)
                    answer += f"• {region['address_region']}: {total} facilities\n"
                answer += "\n"
            
            # Show well-served regions
            well_served = [r for r in results if r.get('total_facilities', 0) >= 50]
            if well_served:
                answer += "✅ **Well-served regions:**\n"
                for region in well_served[:5]:
                    total = region.get('total_facilities', 0)
                    answer += f"• {region['address_region']}: {total} facilities\n"
        
        return answer


# Test function
if __name__ == "__main__":
    print("🧪 Testing Unified Agent\n")
    print("=" * 70)
    
    agent = UnifiedAgent()
    
    # Test queries
    test_questions = [
        "How many hospitals in Accra?",
        "Which facilities handle cardiac care?",
        "Where are pediatric care gaps?",
        "Show me NGOs in Kumasi",
        "How to fix cardiac gaps in Northern region?"
    ]
    
    for question in test_questions:
        print(f"\n📝 Q: {question}")
        print("-" * 70)
        result = agent.handle_query(question)
        print(result['answer'])
        print("\n")
