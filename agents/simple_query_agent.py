"""
Simple Query Agent - Answer questions WITHOUT external AI APIs

Purpose: Demo version that works without API keys
Uses basic SQL generation logic
"""

import duckdb
from typing import List, Dict, Any


class SimpleQueryAgent:
    """Simple agent that answers questions using predefined SQL patterns"""
    
    def __init__(self, db_path: str = "data/healthcare.duckdb"):
        """Initialize Simple Query Agent"""
        self.db_path = db_path
        self.conn = duckdb.connect(db_path, read_only=True)
        print("✅ Using Simple Query Agent (No API keys needed)")
    
    def generate_sql(self, question: str) -> str:
        """
        Generate SQL based on keywords in question
        Simple pattern matching - no AI needed
        """
        question_lower = question.lower()
        
        # Pattern 1: Count facilities in a city
        if "how many" in question_lower and "in" in question_lower:
            # Extract city name
            words = question.split()
            if "in" in words:
                city_idx = words.index("in") + 1
                if city_idx < len(words):
                    city = words[city_idx].strip("?.,")
                    return f"SELECT COUNT(*) as count FROM facilities WHERE LOWER(address_city) = LOWER('{city}')"
        
        # Pattern 2: Show all NGOs
        if "ngo" in question_lower:
            return "SELECT name, address_city FROM facilities WHERE organization_type = 'ngo' LIMIT 10"
        
        # Pattern 3: Facilities by specialty
        if "cardiac" in question_lower or "heart" in question_lower:
            return """
                SELECT DISTINCT f.name, f.address_city, s.specialty
                FROM facilities f
                JOIN specialties s ON f.facility_id = s.facility_id
                WHERE LOWER(s.specialty) LIKE '%cardio%'
                LIMIT 10
            """
        
        # Default: Show all facilities
        return "SELECT name, address_city, organization_type FROM facilities LIMIT 10"
    
    def execute_sql(self, query: str) -> List[Dict[str, Any]]:
        """Execute SQL query"""
        try:
            result = self.conn.execute(query).fetchdf()
            return result.to_dict('records')
        except Exception as e:
            return [{"error": str(e)}]
    
    def format_answer(self, question: str, results: List[Dict]) -> str:
        """Format results into natural language"""
        if not results:
            return "No results found."
        
        if 'error' in results[0]:
            return f"Error: {results[0]['error']}"
        
        # If it's a count query
        if 'count' in results[0]:
            return f"There are {results[0]['count']} facilities in that location."
        
        # If it's a list of facilities
        answer = f"Found {len(results)} results:\n"
        for i, row in enumerate(results[:5], 1):
            facility_name = row.get('name', 'Unknown')
            city = row.get('address_city', 'Unknown')
            answer += f"{i}. {facility_name} in {city}\n"
        
        if len(results) > 5:
            answer += f"...and {len(results) - 5} more"
        
        return answer
    
    def answer_question(self, question: str) -> Dict[str, Any]:
        """Answer a question"""
        print(f"\n🤔 Question: {question}")
        print("="*70)
        
        # Generate SQL
        print("📝 Generating SQL...")
        sql_query = self.generate_sql(question)
        print(f"✅ Generated SQL:\n{sql_query}\n")
        
        # Execute
        print("🔍 Executing query...")
        results = self.execute_sql(sql_query)
        print(f"✅ Found {len(results)} results\n")
        
        # Format answer
        print("💬 Generating answer...")
        answer = self.format_answer(question, results)
        print(f"✅ Answer generated\n")
        
        return {
            "question": question,
            "sql_query": sql_query,
            "results_count": len(results),
            "results": results,
            "answer": answer
        }
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    print("🤖 SIMPLE QUERY AGENT TEST (No API Keys Needed)")
    print("="*70)
    
    agent = SimpleQueryAgent()
    
    # Test questions
    questions = [
        "How many facilities are in Accra?",
        "Show me all NGOs",
        "Which hospitals handle cardiac care?",
    ]
    
    for question in questions:
        result = agent.answer_question(question)
        print("\n" + "="*70)
        print(f"💬 ANSWER: {result['answer']}")
        print("="*70)
        print("\nPress Enter to continue...")
        input()
    
    agent.close()
