"""
Query Agent - Answer questions about healthcare facilities

Purpose: Use AI to answer natural language questions about facilities
Example: "Which hospitals in Accra handle cardiac care?"

Uses: Google ADK + Gemini AI + DuckDB queries
"""

import os
from typing import List, Dict, Any
import duckdb
from google import genai
from google.genai import types


class QueryAgent:
    """AI agent that answers questions about healthcare facilities"""
    
    def __init__(self, db_path: str = "data/healthcare.duckdb"):
        """
        Initialize Query Agent
        
        Args:
            db_path: Path to DuckDB database
        """
        self.db_path = db_path
        self.conn = duckdb.connect(db_path, read_only=True)
        
        # Initialize Google Gemini client (FREE - no API key needed)
        try:
            self.client = genai.Client()
            print("✅ Using Google Gemini (FREE) with Google ADK framework")
        except Exception as e:
            print(f"⚠️  Error initializing Gemini: {e}")
            print("💡 Trying with API key...")
            api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
            if api_key:
                self.client = genai.Client(api_key=api_key)
                print("✅ Using Google Gemini with API key")
            else:
                raise ValueError("Could not initialize Gemini client")
        
    def get_database_schema(self) -> str:
        """Get database schema information for AI context"""
        schema = """
        DATABASE SCHEMA:
        
        1. facilities table:
           - facility_id (unique ID)
           - name (facility name)
           - organization_type (facility or ngo)
           - address_city (city location)
           - address_region (region/state)
           - facility_type (hospital, clinic, etc.)
           - description (text description)
        
        2. specialties table:
           - facility_id (links to facilities)
           - specialty (medical specialty like cardiology, pediatrics)
        
        3. contact_info table:
           - facility_id (links to facilities)
           - phone_numbers
           - email
           - website
        """
        return schema
    
    def execute_sql(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results
        
        Args:
            query: SQL query string
        
        Returns:
            List of dictionaries (rows)
        """
        try:
            result = self.conn.execute(query).fetchdf()
            return result.to_dict('records')
        except Exception as e:
            return [{"error": str(e)}]
    
    def answer_question(self, question: str) -> Dict[str, Any]:
        """
        Answer a natural language question about facilities
        
        Process:
        1. Send question + schema to GPT-4
        2. GPT-4 generates SQL query
        3. Execute SQL query
        4. GPT-4 formats the answer
        
        Args:
            question: Natural language question
        
        Returns:
            Dictionary with answer and metadata
        """
        print(f"\n🤔 Question: {question}")
        print("="*70)
        
        # Step 1: Generate SQL query from question
        print("📝 Generating SQL query with Gemini...")
        
        system_prompt = f"""You are a helpful assistant that converts natural language questions into SQL queries.

{self.get_database_schema()}

Generate a SQL query to answer the user's question. Return ONLY the SQL query, no explanation.

Rules:
- Use proper SQL syntax for DuckDB
- Join tables as needed
- Use WHERE clauses for filtering
- Limit results to 10 unless user asks for more
- For specialty searches, JOIN with specialties table
"""
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=f"{system_prompt}\n\nQuestion: {question}",
                config=types.GenerateContentConfig(
                    temperature=0,
                )
            )
            
            sql_query = response.text.strip()
            # Remove markdown code blocks if present
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            
            print(f"✅ Generated SQL:\n{sql_query}\n")
            
        except Exception as e:
            print(f"❌ Error generating SQL: {e}")
            return {
                "question": question,
                "error": str(e),
                "answer": "Sorry, I couldn't generate a query for that question."
            }
        
        print(f"✅ Generated SQL:\n{sql_query}\n")
        
        # Step 2: Execute query
        print("🔍 Executing query...")
        results = self.execute_sql(sql_query)
        
        if results and 'error' in results[0]:
            print(f"❌ SQL Error: {results[0]['error']}")
            return {
                "question": question,
                "sql_query": sql_query,
                "error": results[0]['error'],
                "answer": "Sorry, I couldn't execute that query."
            }
        
        print(f"✅ Found {len(results)} results\n")
        
        # Step 3: Format answer
        print("💬 Generating answer with Gemini...")
        
        answer_prompt = f"""Based on the SQL query results, provide a clear, concise answer to the user's question.

Question: {question}

SQL Results: {results[:10]}  

Provide a natural language answer that:
- Directly answers the question
- Mentions specific facility names when relevant
- Includes numbers/counts when applicable
- Is helpful and informative
"""
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=answer_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                )
            )
            
            answer = response.text.strip()
            print(f"✅ Answer generated\n")
            
        except Exception as e:
            print(f"❌ Error generating answer: {e}")
            answer = f"Found {len(results)} results but couldn't format the answer."
        
        return {
            "question": question,
            "sql_query": sql_query,
            "results_count": len(results),
            "results": results[:10],  # Limit to 10 for display
            "answer": answer
        }
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Test the Query Agent"""
    print("🤖 QUERY AGENT TEST")
    print("="*70)
    
    # Initialize agent
    agent = QueryAgent()
    
    # Test questions
    questions = [
        "How many facilities are in Accra?",
        "Which hospitals in Kumasi handle cardiac care?",
        "Show me all NGOs",
    ]
    
    for question in questions:
        result = agent.answer_question(question)
        print("\n" + "="*70)
        print(f"ANSWER: {result['answer']}")
        print("="*70)
        input("\nPress Enter to continue to next question...")
    
    agent.close()


if __name__ == "__main__":
    main()

        
    def get_database_schema(self) -> str:
        """Get database schema information for AI context"""
        schema = """
        DATABASE SCHEMA:
        
        1. facilities table:
           - facility_id (unique ID)
           - name (facility name)
           - organization_type (facility or ngo)
           - address_city (city location)
           - address_region (region/state)
           - facility_type (hospital, clinic, etc.)
           - description (text description)
        
        2. specialties table:
           - facility_id (links to facilities)
           - specialty (medical specialty like cardiology, pediatrics)
        
        3. contact_info table:
           - facility_id (links to facilities)
           - phone_numbers
           - email
           - website
        """
        return schema
    
    def execute_sql(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results
        
        Args:
            query: SQL query string
        
        Returns:
            List of dictionaries (rows)
        """
        try:
            result = self.conn.execute(query).fetchdf()
            return result.to_dict('records')
        except Exception as e:
            return [{"error": str(e)}]
    
    def answer_question(self, question: str) -> Dict[str, Any]:
        """
        Answer a natural language question about facilities
        
        Process:
        1. Send question + schema to Gemini
        2. Gemini generates SQL query
        3. Execute SQL query
        4. Gemini formats the answer
        
        Args:
            question: Natural language question
        
        Returns:
            Dictionary with answer and metadata
        """
        print(f"\n🤔 Question: {question}")
        print("="*70)
        
        # Step 1: Generate SQL query from question
        print("📝 Generating SQL query using Google Gemini...")
        
        system_prompt = f"""You are a helpful assistant that converts natural language questions into SQL queries.

{self.get_database_schema()}

Generate a SQL query to answer the user's question. Return ONLY the SQL query, no explanation.

Rules:
- Use proper SQL syntax for DuckDB
- Join tables as needed
- Use WHERE clauses for filtering
- Limit results to 10 unless user asks for more
- For specialty searches, JOIN with specialties table
"""
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=f"{system_prompt}\n\nQuestion: {question}",
                config=types.GenerateContentConfig(
                    temperature=0,
                )
            )
            
            sql_query = response.text.strip()
            # Remove markdown code blocks if present
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            
            print(f"✅ Generated SQL:\n{sql_query}\n")
            
        except Exception as e:
            print(f"❌ Error generating SQL: {e}")
            return {
                "question": question,
                "error": str(e),
                "answer": "Sorry, I couldn't generate a query for that question."
            }
        
        # Step 2: Execute query
        print("🔍 Executing query...")
        results = self.execute_sql(sql_query)
        
        if results and 'error' in results[0]:
            print(f"❌ SQL Error: {results[0]['error']}")
            return {
                "question": question,
                "sql_query": sql_query,
                "error": results[0]['error'],
                "answer": "Sorry, I couldn't execute that query."
            }
        
        print(f"✅ Found {len(results)} results\n")
        
        # Step 3: Format answer
        print("💬 Generating answer...")
        
        answer_prompt = f"""Based on the SQL query results, provide a clear, concise answer to the user's question.

Question: {question}

SQL Results: {results[:10]}  

Provide a natural language answer that:
- Directly answers the question
- Mentions specific facility names when relevant
- Includes numbers/counts when applicable
- Is helpful and informative
"""
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=answer_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                )
            )
            
            answer = response.text.strip()
            print(f"✅ Answer generated\n")
            
        except Exception as e:
            print(f"❌ Error generating answer: {e}")
            answer = f"Found {len(results)} results but couldn't format the answer."
        
        return {
            "question": question,
            "sql_query": sql_query,
            "results_count": len(results),
            "results": results[:10],  # Limit to 10 for display
            "answer": answer
        }
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Test the Query Agent"""
    print("🤖 QUERY AGENT TEST (Google Gemini)")
    print("="*70)
    
    # Initialize agent
    agent = QueryAgent()
    
    # Test questions
    questions = [
        "How many facilities are in Accra?",
        "Which hospitals in Kumasi handle cardiac care?",
        "Show me all NGOs",
    ]
    
    for question in questions:
        result = agent.answer_question(question)
        print("\n" + "="*70)
        print(f"💬 ANSWER: {result['answer']}")
        print("="*70)
        input("\nPress Enter to continue to next question...")
    
    agent.close()


if __name__ == "__main__":
    main()
