"""
Enhanced Agent - AI-Powered with FAISS, LLM, and Visualizations

Features:
- OpenAI GPT-4 for natural language to SQL
- FAISS semantic search for complex queries
- Plotly visualizations in responses
- Smart fallback to pattern matching if APIs unavailable
"""

import os
import duckdb
import faiss
import pickle
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from sentence_transformers import SentenceTransformer
import openai

try:
    from agents.gap_analyzer_agent import GapAnalyzerAgent
    from agents.planning_agent import PlanningAgent
except Exception:
    from gap_analyzer_agent import GapAnalyzerAgent
    from planning_agent import PlanningAgent


class EnhancedAgent:
    """AI-powered agent with semantic search and visualizations"""
    
    def __init__(self, db_path: str = "data/healthcare.duckdb"):
        """Initialize enhanced agent"""
        self.db_path = db_path
        self.conn = duckdb.connect(db_path, read_only=True)
        
        # Initialize OpenAI (if available)
        self.openai_client = None
        self.has_openai = False
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            try:
                self.openai_client = openai.OpenAI(api_key=api_key)
                self.has_openai = True
                print("✅ OpenAI GPT-4 available")
            except Exception as e:
                print(f"⚠️  OpenAI not available: {e}")
                print("📌 Using pattern matching fallback")
        else:
            print("📌 No OpenAI API key, using pattern matching")

        # Initialize multi-agents (gap + planning)
        self.gap_agent = None
        self.planning_agent = None
        try:
            self.gap_agent = GapAnalyzerAgent(db_path)
            self.planning_agent = PlanningAgent(db_path)
        except Exception as e:
            print(f"⚠️  Multi-agent init failed: {e}")
        
        # Initialize FAISS (if available)
        self.has_faiss = False
        self.faiss_index = None
        self.faiss_metadata = None
        self.embedding_model = None
        
        if Path('data/faiss_index.bin').exists():
            try:
                self.faiss_index = faiss.read_index('data/faiss_index.bin')
                with open('data/faiss_metadata.pkl', 'rb') as f:
                    self.faiss_metadata = pickle.load(f)
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                self.has_faiss = True
                print("✅ FAISS semantic search available")
            except Exception as e:
                print(f"⚠️  FAISS not available: {e}")
        else:
            print("📌 FAISS index not found, run: python tools/build_faiss_index.py")
        
        print(f"🚀 Enhanced Agent ready (AI: {self.has_openai}, FAISS: {self.has_faiss})")
    
    def handle_query(self, question: str) -> Dict[str, Any]:
        """
        Main entry point - uses AI when available, falls back to patterns
        """
        question_lower = question.lower()
        
        # Try FAISS semantic search first for complex queries
        if self.has_faiss and self._is_semantic_query(question):
            return self._semantic_search(question)
        
        # Route to appropriate handler
        if any(word in question_lower for word in ['gap', 'desert', 'missing', 'need', 'lacking', 'underserved']):
            return self._analyze_gaps(question)
        elif any(word in question_lower for word in ['plan', 'fix', 'improve', 'deploy', 'allocate', 'strategy']):
            return self._generate_plan(question)
        elif any(word in question_lower for word in ['compare', 'versus', 'vs', 'difference']):
            return self._compare_regions(question)
        else:
            return self._answer_facility_query(question)
    
    def _is_semantic_query(self, question: str) -> bool:
        """Detect if query needs semantic search"""
        semantic_keywords = [
            'find', 'look for', 'search', 'similar', 'like', 'specialized',
            'advanced', 'comprehensive', 'full', 'equipped', 'capable'
        ]
        return any(kw in question.lower() for kw in semantic_keywords)
    
    def _semantic_search(self, question: str, k: int = 10) -> Dict[str, Any]:
        """Use FAISS to find semantically similar facilities"""
        # Generate query embedding
        query_embedding = self.embedding_model.encode([question])[0]
        
        # Search FAISS index
        distances, indices = self.faiss_index.search(
            query_embedding.reshape(1, -1).astype('float32'), k
        )
        
        # Get matching facilities
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            facility = self.faiss_metadata[idx]
            facility['similarity_score'] = float(1 / (1 + dist))  # Convert distance to similarity
            results.append(facility)
        
        # Format answer
        answer = f"🔍 **Semantic search results** (found {len(results)} matches):\n\n"
        for i, facility in enumerate(results, 1):
            answer += f"**{i}. {facility['name']}**\n"
            answer += f"   📍 {facility['address_city']}, {facility['address_region']}\n"
            if facility.get('specialties'):
                answer += f"   🏥 {facility['specialties']}\n"
            answer += f"   📊 Relevance: {facility['similarity_score']:.2%}\n\n"
        
        return {
            'answer': answer,
            'data': results,
            'sql': None,
            'type': 'semantic_search',
            'visualization': None
        }
    
    def _answer_facility_query(self, question: str) -> Dict[str, Any]:
        """Answer facility queries - AI-powered or pattern-based"""
        
        # Try AI-generated SQL first
        if self.has_openai:
            try:
                sql_query = self._generate_sql_with_ai(question)
                results = self._execute_query(sql_query)
                answer = self._format_facility_answer(question, results)
                
                return {
                    'answer': answer,
                    'data': results,
                    'sql': sql_query,
                    'type': 'ai_query',
                    'visualization': self._create_viz_if_applicable(question, results)
                }
            except Exception as e:
                print(f"AI query failed: {e}, falling back to patterns")
        
        # Fallback to pattern matching
        return self._pattern_based_query(question)
    
    def _generate_sql_with_ai(self, question: str) -> str:
        """Use GPT-4 to generate SQL from natural language"""
        schema = self._get_schema_description()
        
        prompt = f"""You are a SQL expert. Generate a valid DuckDB SQL query for this question.

Database Schema:
{schema}

User Question: {question}

Requirements:
- Return ONLY the SQL query, no explanation
- Use proper JOINs when querying specialties
- Use LIKE '%keyword%' for text matching
- Limit results to 20 unless counting
- Handle NULL values properly

SQL Query:"""

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a SQL expert for healthcare databases."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        sql = response.choices[0].message.content.strip()
        # Clean up markdown code blocks if present
        sql = sql.replace('```sql', '').replace('```', '').strip()
        return sql
    
    def _pattern_based_query(self, question: str) -> Dict[str, Any]:
        """Pattern matching fallback"""
        question_lower = question.lower()
        sql_query = None
        
        # Count queries
        if "how many" in question_lower:
            location = self._extract_location(question)
            if location:
                sql_query = f"""
                    SELECT COUNT(*) as count, address_city, address_region
                    FROM facilities
                    WHERE LOWER(address_city) LIKE '%{location.lower()}%'
                       OR LOWER(address_region) LIKE '%{location.lower()}%'
                    GROUP BY address_city, address_region
                """
        
        # Specialty queries
        elif any(spec in question_lower for spec in ['cardiac', 'pediatric', 'surgery', 'trauma', 'maternity', 'emergency']):
            specialty = self._extract_specialty(question)
            location = self._extract_location(question)
            
            where_clause = f"LOWER(s.specialty) LIKE '%{specialty}%'"
            if location:
                where_clause += f" AND (LOWER(f.address_city) LIKE '%{location.lower()}%' OR LOWER(f.address_region) LIKE '%{location.lower()}%')"
            
            sql_query = f"""
                SELECT 
                    f.name, 
                    f.address_city, 
                    f.address_region,
                    f.facility_type,
                    s.specialty
                FROM facilities f
                JOIN specialties s ON f.facility_id = s.facility_id
                WHERE {where_clause}
                LIMIT 20
            """
        
        # NGO queries
        elif "ngo" in question_lower:
            location = self._extract_location(question)
            where_clause = "organization_type = 'ngo'"
            if location:
                where_clause += f" AND (LOWER(address_city) LIKE '%{location.lower()}%' OR LOWER(address_region) LIKE '%{location.lower()}%')"
            
            sql_query = f"""
                SELECT name, address_city, address_region, facility_type
                FROM facilities
                WHERE {where_clause}
                LIMIT 20
            """
        
        # Default overview
        else:
            sql_query = """
                SELECT 
                    organization_type,
                    COUNT(*) as count
                FROM facilities
                GROUP BY organization_type
            """
        
        results = self._execute_query(sql_query)
        answer = self._format_facility_answer(question, results)
        
        return {
            'answer': answer,
            'data': results,
            'sql': sql_query,
            'type': 'pattern_query',
            'visualization': self._create_viz_if_applicable(question, results)
        }
    
    def _analyze_gaps(self, question: str) -> Dict[str, Any]:
        """Identify medical deserts with visualizations"""
        specialty = self._extract_specialty(question)
        location = self._extract_location(question)
        
        if self.gap_agent and "desert" in question.lower():
            deserts = self.gap_agent.identify_medical_deserts()
            answer = (
                f"🏜️ **Medical Deserts Summary**\n\n"
                f"Critical (1 facility): {deserts['summary']['critical']} cities\n"
                f"Severe (2 facilities): {deserts['summary']['severe']} cities\n"
                f"Moderate (3-4 facilities): {deserts['summary']['moderate']} cities\n"
            )
            data = deserts['critical_deserts'] + deserts['severe_deserts'] + deserts['moderate_deserts']
            return {
                'answer': answer,
                'data': data,
                'sql': None,
                'type': 'gap_analysis',
                'visualization': None
            }
        
        if specialty:
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
                    SELECT DISTINCT address_region, COUNT(*) as total_facilities
                    FROM facilities
                    WHERE address_region IS NOT NULL AND address_region != ''
                    GROUP BY address_region
                )
                SELECT 
                    ar.address_region,
                    ar.total_facilities,
                    COALESCE(sc.facility_count, 0) as specialty_facilities
                FROM all_regions ar
                LEFT JOIN specialty_coverage sc ON ar.address_region = sc.address_region
                ORDER BY specialty_facilities ASC, ar.total_facilities DESC
            """
        else:
            sql_query = """
                SELECT 
                    address_region,
                    COUNT(*) as total_facilities,
                    SUM(CASE WHEN organization_type = 'facility' THEN 1 ELSE 0 END) as healthcare_facilities,
                    SUM(CASE WHEN organization_type = 'ngo' THEN 1 ELSE 0 END) as ngos
                FROM facilities
                WHERE address_region IS NOT NULL AND address_region != ''
                GROUP BY address_region
                ORDER BY total_facilities ASC
            """
        
        results = self._execute_query(sql_query)
        answer = self._format_gap_answer(question, results, specialty)
        viz = self._create_gap_visualization(results, specialty)
        
        return {
            'answer': answer,
            'data': results,
            'sql': sql_query,
            'type': 'gap_analysis',
            'visualization': viz
        }
    
    def _compare_regions(self, question: str) -> Dict[str, Any]:
        """Compare healthcare coverage between regions"""
        sql_query = """
            SELECT 
                address_region,
                COUNT(*) as total_facilities,
                SUM(CASE WHEN organization_type = 'facility' THEN 1 ELSE 0 END) as facilities,
                SUM(CASE WHEN organization_type = 'ngo' THEN 1 ELSE 0 END) as ngos
            FROM facilities
            WHERE address_region IS NOT NULL AND address_region != ''
            GROUP BY address_region
            ORDER BY total_facilities DESC
            LIMIT 15
        """
        
        results = self._execute_query(sql_query)
        
        # Create comparison visualization
        viz = go.Figure(data=[
            go.Bar(name='Facilities', x=[r['address_region'] for r in results], 
                   y=[r['facilities'] for r in results]),
            go.Bar(name='NGOs', x=[r['address_region'] for r in results], 
                   y=[r['ngos'] for r in results])
        ])
        viz.update_layout(
            title="Healthcare Coverage by Region",
            barmode='stack',
            xaxis_title="Region",
            yaxis_title="Count",
            height=500
        )
        
        answer = "📊 **Regional Comparison:**\n\n"
        for r in results[:10]:
            answer += f"**{r['address_region']}**: {r['total_facilities']} total ({r['facilities']} facilities, {r['ngos']} NGOs)\n"
        
        return {
            'answer': answer,
            'data': results,
            'sql': sql_query,
            'type': 'comparison',
            'visualization': viz
        }
    
    def _generate_plan(self, question: str) -> Dict[str, Any]:
        """Generate actionable plans"""
        location = self._extract_location(question)
        specialty = self._extract_specialty(question)
        
        # Get gap analysis first
        gaps = self._analyze_gaps(question)
        
        # Generate AI-powered recommendations if available
        if self.planning_agent:
            if location:
                plan = self.planning_agent.generate_action_plan(location)
                answer = self.planning_agent.format_plan(plan)
                data = plan.get('nearby_partners', [])
                return {
                    'answer': answer,
                    'data': data,
                    'sql': None,
                    'type': 'planning',
                    'visualization': None
                }
            if specialty:
                plan = self.planning_agent.recommend_specialty_deployment(specialty)
                answer = (
                    f"🎯 **Deploy {specialty.title()} Specialists**\n\n"
                    f"{plan['deployment_strategy']}\n"
                )
                return {
                    'answer': answer,
                    'data': plan.get('recommended_cities', []),
                    'sql': None,
                    'type': 'planning',
                    'visualization': None
                }
            priorities = self.planning_agent.prioritize_cities()
            answer = "📌 **Priority Cities for Intervention**\n\n"
            for row in priorities[:10]:
                answer += f"- {row['address_city']} ({row['address_region']}): gap {row['facility_gap']}\n"
            return {
                'answer': answer,
                'data': priorities,
                'sql': None,
                'type': 'planning',
                'visualization': None
            }
        
        if self.has_openai:
            try:
                plan = self._generate_ai_plan(question, gaps['data'], location, specialty)
            except:
                plan = self._generate_template_plan(location, specialty, gaps)
        else:
            plan = self._generate_template_plan(location, specialty, gaps)
        
        return {
            'answer': plan,
            'data': gaps['data'],
            'sql': gaps['sql'],
            'type': 'planning',
            'visualization': gaps.get('visualization')
        }
    
    def _generate_ai_plan(self, question: str, gap_data: List[Dict], location: str, specialty: str) -> str:
        """Use AI to generate detailed action plan"""
        context = f"Gap analysis data: {gap_data[:5]}"  # First 5 regions
        
        prompt = f"""You are a healthcare planning expert. Generate a detailed, actionable plan.

Question: {question}
Location: {location or 'General'}
Specialty: {specialty or 'All healthcare'}
Current Gap Data: {context}

Generate a comprehensive plan with:
1. Immediate Actions (0-3 months)
2. Short-term Strategy (3-6 months)
3. Long-term Vision (6-18 months)
4. Resource Requirements
5. Success Metrics

Format with clear sections and bullet points."""

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a healthcare planning expert focused on reducing medical deserts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )
        
        return response.choices[0].message.content
    
    def _generate_template_plan(self, location: str, specialty: str, gaps: Dict) -> str:
        """Template-based plan generation"""
        plan = f"🎯 **ACTION PLAN**\n\n"
        
        if specialty and location:
            plan += f"**Focus**: Improve {specialty} care in {location}\n\n"
        elif specialty:
            plan += f"**Focus**: Address {specialty} care gaps\n\n"
        elif location:
            plan += f"**Focus**: Improve healthcare access in {location}\n\n"
        
        plan += f"**Current Situation**\n{gaps['answer']}\n\n"
        plan += """**Phase 1: Immediate Actions (0-3 months)**
• Conduct detailed needs assessment
• Identify partner facilities with existing capabilities
• Deploy mobile health units to underserved areas
• Establish telemedicine connections

**Phase 2: Short-term Strategy (3-6 months)**
• Recruit specialist healthcare workers
• Set up satellite clinics in medical deserts
• Launch community health worker training program
• Secure equipment and supply chains

**Phase 3: Long-term Vision (6-18 months)**
• Build permanent healthcare infrastructure
• Develop regional referral networks
• Create specialist training programs
• Implement quality monitoring systems

**Success Metrics**
• 50% reduction in travel time to care
• 3x increase in specialist consultations
• 90% patient satisfaction rate
• Zero preventable deaths from access delays
"""
        return plan
    
    # Visualization methods
    
    def _create_gap_visualization(self, results: List[Dict], specialty: str = None) -> go.Figure:
        """Create bar chart for gap analysis"""
        if not results:
            return None
        
        # Determine what to visualize
        if specialty:
            regions = [r['address_region'] for r in results[:15]]
            values = [r.get('specialty_facilities', 0) for r in results[:15]]
            title = f"{specialty.title()} Care Coverage by Region"
            ylabel = f"{specialty.title()} Facilities"
        else:
            regions = [r['address_region'] for r in results[:15]]
            values = [r['total_facilities'] for r in results[:15]]
            title = "Total Healthcare Facilities by Region"
            ylabel = "Total Facilities"
        
        # Create color scale (red for low, green for high)
        colors = ['#d32f2f' if v < 5 else '#ffa000' if v < 20 else '#388e3c' for v in values]
        
        fig = go.Figure(data=[
            go.Bar(x=regions, y=values, marker_color=colors)
        ])
        
        fig.update_layout(
            title=title,
            xaxis_title="Region",
            yaxis_title=ylabel,
            height=400,
            showlegend=False
        )
        
        return fig
    
    def _create_viz_if_applicable(self, question: str, results: List[Dict]) -> Optional[go.Figure]:
        """Create visualization if query would benefit from it"""
        if not results or len(results) < 2:
            return None
        
        # Count queries -> pie chart
        if 'count' in results[0] and len(results) > 1:
            labels = [r.get('address_city') or r.get('address_region') or r.get('organization_type') for r in results]
            values = [r['count'] for r in results]
            
            fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
            fig.update_layout(title="Distribution", height=400)
            return fig
        
        return None
    
    # Helper methods
    
    def _execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SQL and return results"""
        try:
            result = self.conn.execute(sql).fetchdf()
            return result.to_dict('records')
        except Exception as e:
            print(f"SQL Error: {e}")
            return []
    
    def _get_schema_description(self) -> str:
        """Get schema for AI context"""
        return """
Tables:
1. facilities (facility_id, name, organization_type, address_city, address_region, facility_type, description)
2. specialties (facility_id, specialty)
3. contact_info (facility_id, phone_numbers, email, website)

Common specialties: cardiology, pediatrics, surgery, trauma, emergency, maternity, obstetrics
Common regions: Greater Accra, Ashanti Region, Western, Eastern, Northern, Central, Volta
        """
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from text"""
        locations = [
            'accra', 'kumasi', 'tema', 'takoradi', 'tamale', 'cape coast',
            'sunyani', 'koforidua', 'ho', 'wa', 'bolgatanga', 'sekondi',
            'greater accra', 'ashanti', 'western', 'eastern', 'northern',
            'central', 'volta', 'upper east', 'upper west', 'brong ahafo', 'oti'
        ]
        
        text_lower = text.lower()
        for location in locations:
            if location in text_lower:
                return location.title()
        return None
    
    def _extract_specialty(self, text: str) -> Optional[str]:
        """Extract specialty from text"""
        specialties = {
            'cardiac': 'cardio', 'heart': 'cardio', 'cardiology': 'cardio',
            'pediatric': 'pediatric', 'children': 'pediatric', 'child': 'pediatric',
            'surgery': 'surgery', 'surgical': 'surgery',
            'trauma': 'trauma', 'emergency': 'emergency',
            'maternity': 'maternity', 'obstetric': 'obstetric', 'maternal': 'maternity'
        }
        
        text_lower = text.lower()
        for keyword, specialty in specialties.items():
            if keyword in text_lower:
                return specialty
        return None
    
    def _format_facility_answer(self, question: str, results: List[Dict]) -> str:
        """Format facility results"""
        if not results:
            return "❌ No facilities found matching your query."
        
        # Count queries
        if 'count' in results[0] and len(results) > 0:
            total = sum(r['count'] for r in results)
            answer = f"📊 Found **{total} facilities** total:\n\n"
            for row in results[:10]:
                location = row.get('address_city') or row.get('address_region') or row.get('organization_type')
                answer += f"• **{location}**: {row['count']} facilities\n"
            return answer
        
        # Facility lists
        answer = f"🏥 Found **{len(results)} facilities**:\n\n"
        for i, row in enumerate(results[:15], 1):
            name = row.get('name', 'Unknown')
            city = row.get('address_city', '')
            region = row.get('address_region', '')
            specialty = row.get('specialty', '')
            
            answer += f"**{i}. {name}**\n"
            if city or region:
                answer += f"   📍 {city}{', ' + region if city and region else region}\n"
            if specialty:
                answer += f"   🏥 {specialty}\n"
            answer += "\n"
        
        if len(results) > 15:
            answer += f"_...and {len(results) - 15} more_\n"
        
        return answer
    
    def _format_gap_answer(self, question: str, results: List[Dict], specialty: str = None) -> str:
        """Format gap analysis"""
        if not results:
            return "No data available for gap analysis."
        
        if specialty:
            answer = f"🔍 **{specialty.title()} Care Coverage Analysis:**\n\n"
            
            gaps = [r for r in results if r.get('specialty_facilities', 0) == 0]
            limited = [r for r in results if 0 < r.get('specialty_facilities', 0) < 3]
            good = [r for r in results if r.get('specialty_facilities', 0) >= 3]
            
            if gaps:
                answer += f"❌ **Critical Gaps** ({len(gaps)} regions with no {specialty} care):\n"
                for r in gaps[:5]:
                    answer += f"• {r['address_region']} - {r.get('total_facilities', 0)} total facilities\n"
                answer += "\n"
            
            if limited:
                answer += f"⚠️ **Limited Coverage** ({len(limited)} regions with 1-2 facilities):\n"
                for r in limited[:5]:
                    answer += f"• {r['address_region']} - {r['specialty_facilities']} {specialty} facilities\n"
                answer += "\n"
            
            if good:
                answer += f"✅ **Adequate Coverage** ({len(good)} regions with 3+ facilities):\n"
                for r in good[:3]:
                    answer += f"• {r['address_region']} - {r['specialty_facilities']} facilities\n"
        else:
            answer = "📊 **Regional Healthcare Coverage:**\n\n"
            
            underserved = [r for r in results if r.get('total_facilities', 0) < 10]
            
            if underserved:
                answer += f"⚠️ **Underserved Regions** ({len(underserved)} regions with <10 facilities):\n"
                for r in underserved[:8]:
                    answer += f"• {r['address_region']}: {r['total_facilities']} facilities "
                    answer += f"({r.get('healthcare_facilities', 0)} hospitals, {r.get('ngos', 0)} NGOs)\n"
        
        return answer


# Test function
if __name__ == "__main__":
    print("🧪 Testing Enhanced Agent\n")
    print("=" * 70)
    
    agent = EnhancedAgent()
    
    # Test queries
    test_questions = [
        "How many hospitals in Accra?",
        "Find trauma centers with advanced equipment",
        "Where are pediatric care gaps?",
        "Compare healthcare between Greater Accra and Ashanti",
        "How to fix cardiac gaps in Northern region?"
    ]
    
    for question in test_questions:
        print(f"\n📝 Q: {question}")
        print("-" * 70)
        result = agent.handle_query(question)
        print(result['answer'][:500])  # First 500 chars
        print(f"\n✓ Type: {result['type']}")
        if result['visualization']:
            print("✓ Visualization: Available")
        print("\n")
