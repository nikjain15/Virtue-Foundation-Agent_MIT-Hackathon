"""
RAG (Retrieval-Augmented Generation) Module

Purpose: Add semantic search capabilities using FAISS
Enables finding facilities based on description similarity

Uses: FAISS for vector search (no API keys needed for embeddings)
"""

import duckdb
import numpy as np
import faiss
from typing import List, Dict, Any
import pickle
from pathlib import Path


class RAGSystem:
    """RAG system for semantic search of healthcare facilities"""
    
    def __init__(self, db_path: str = "data/healthcare.duckdb"):
        """Initialize RAG system"""
        self.db_path = db_path
        self.conn = duckdb.connect(db_path, read_only=True)
        self.index = None
        self.facility_ids = []
        self.embeddings_path = Path("data/facility_embeddings.pkl")
        
        print("✅ RAG System initialized")
    
    def create_simple_embeddings(self):
        """
        Create simple embeddings from facility data
        
        Note: For demo purposes, using TF-IDF-like approach
        In production, would use sentence-transformers or OpenAI embeddings
        """
        print("\n🔄 Creating facility embeddings...")
        
        # Get all facilities with descriptions
        query = """
            SELECT 
                f.facility_id,
                f.name,
                f.description,
                f.facility_type,
                f.address_city,
                GROUP_CONCAT(s.specialty, ' ') as specialties
            FROM facilities f
            LEFT JOIN specialties s ON f.facility_id = s.facility_id
            WHERE f.description IS NOT NULL AND f.description != ''
            GROUP BY f.facility_id, f.name, f.description, f.facility_type, f.address_city
        """
        
        df = self.conn.execute(query).df()
        print(f"  Found {len(df)} facilities with descriptions")
        
        # Create simple bag-of-words embeddings
        # In production, use: sentence-transformers, OpenAI embeddings, etc.
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        # Combine all text fields
        df['combined_text'] = (
            df['name'].fillna('') + ' ' +
            df['description'].fillna('') + ' ' +
            df['facility_type'].fillna('') + ' ' +
            df['specialties'].fillna('')
        )
        
        # Create TF-IDF embeddings
        vectorizer = TfidfVectorizer(max_features=256, stop_words='english')
        embeddings = vectorizer.fit_transform(df['combined_text']).toarray()
        
        # Store facility IDs
        self.facility_ids = df['facility_id'].tolist()
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype('float32'))
        
        # Save for later use
        with open(self.embeddings_path, 'wb') as f:
            pickle.dump({
                'vectorizer': vectorizer,
                'facility_ids': self.facility_ids,
                'index': faiss.serialize_index(self.index)
            }, f)
        
        print(f"✅ Created embeddings for {len(df)} facilities")
        print(f"   Dimension: {dimension}")
        print(f"   Saved to: {self.embeddings_path}")
        
        return vectorizer
    
    def load_embeddings(self):
        """Load pre-computed embeddings"""
        if not self.embeddings_path.exists():
            print("⚠️  No embeddings found. Creating new ones...")
            return self.create_simple_embeddings()
        
        with open(self.embeddings_path, 'rb') as f:
            data = pickle.load(f)
        
        self.facility_ids = data['facility_ids']
        self.index = faiss.deserialize_index(data['index'])
        
        print(f"✅ Loaded embeddings for {len(self.facility_ids)} facilities")
        return data['vectorizer']
    
    def semantic_search(self, query_text: str, k: int = 10) -> List[Dict[str, Any]]:
        """
        Perform semantic search for similar facilities
        
        Args:
            query_text: Search query
            k: Number of results to return
        
        Returns:
            List of similar facilities with scores
        """
        if self.index is None:
            vectorizer = self.load_embeddings()
        else:
            # Load vectorizer
            with open(self.embeddings_path, 'rb') as f:
                data = pickle.load(f)
            vectorizer = data['vectorizer']
        
        # Transform query
        query_embedding = vectorizer.transform([query_text]).toarray().astype('float32')
        
        # Search
        distances, indices = self.index.search(query_embedding, k)
        
        # Get facility details
        results = []
        for i, (idx, dist) in enumerate(zip(indices[0], distances[0])):
            facility_id = self.facility_ids[idx]
            
            # Get full facility info
            facility_query = f"""
                SELECT 
                    f.facility_id,
                    f.name,
                    f.description,
                    f.address_city,
                    f.facility_type,
                    f.organization_type,
                    GROUP_CONCAT(s.specialty, ', ') as specialties
                FROM facilities f
                LEFT JOIN specialties s ON f.facility_id = s.facility_id
                WHERE f.facility_id = '{facility_id}'
                GROUP BY f.facility_id, f.name, f.description, f.address_city, f.facility_type, f.organization_type
            """
            
            facility_df = self.conn.execute(facility_query).df()
            if len(facility_df) > 0:
                facility_info = facility_df.iloc[0].to_dict()
                facility_info['similarity_score'] = float(1 / (1 + dist))  # Convert distance to similarity
                facility_info['rank'] = i + 1
                results.append(facility_info)
        
        return results
    
    def find_similar_facilities(self, facility_id: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Find facilities similar to a given facility
        
        Args:
            facility_id: Facility to find similar to
            k: Number of results
        
        Returns:
            Similar facilities
        """
        # Get facility description
        query = f"""
            SELECT name, description, facility_type
            FROM facilities
            WHERE facility_id = '{facility_id}'
        """
        
        df = self.conn.execute(query).df()
        if len(df) == 0:
            return []
        
        # Use description as query
        query_text = f"{df.iloc[0]['name']} {df.iloc[0]['description']} {df.iloc[0]['facility_type']}"
        
        # Search (k+1 to exclude the facility itself)
        results = self.semantic_search(query_text, k=k+1)
        
        # Filter out the original facility
        results = [r for r in results if r['facility_id'] != facility_id][:k]
        
        return results
    
    def augmented_query(self, question: str) -> Dict[str, Any]:
        """
        RAG-enhanced query: retrieve relevant context, then answer
        
        Args:
            question: User question
        
        Returns:
            Answer with retrieved context
        """
        print(f"\n🔍 RAG Query: {question}")
        
        # Step 1: Retrieve relevant facilities
        relevant = self.semantic_search(question, k=5)
        
        # Step 2: Format context
        context = "Relevant facilities:\n"
        for i, fac in enumerate(relevant, 1):
            context += f"{i}. {fac['name']} in {fac['address_city']}\n"
            context += f"   Type: {fac['facility_type']}\n"
            context += f"   Description: {fac['description'][:100]}...\n"
        
        # Step 3: Generate answer (without AI, using template)
        answer = f"Based on semantic search, I found {len(relevant)} relevant facilities:\n\n"
        for fac in relevant:
            answer += f"• **{fac['name']}** ({fac['address_city']})\n"
            answer += f"  - Type: {fac['facility_type']}\n"
            answer += f"  - Similarity: {fac['similarity_score']:.2%}\n"
        
        return {
            "question": question,
            "retrieved_facilities": relevant,
            "context": context,
            "answer": answer
        }
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Test RAG system"""
    print("🧪 RAG SYSTEM TEST")
    print("="*70)
    
    rag = RAGSystem()
    
    # Create embeddings
    rag.create_simple_embeddings()
    
    # Test 1: Semantic search
    print("\n" + "="*70)
    print("Test 1: Semantic Search")
    print("="*70)
    results = rag.semantic_search("cardiac care emergency hospital", k=5)
    
    print(f"\nFound {len(results)} results:")
    for r in results:
        print(f"\n{r['rank']}. {r['name']}")
        print(f"   Location: {r['address_city']}")
        print(f"   Type: {r['facility_type']}")
        print(f"   Similarity: {r['similarity_score']:.2%}")
    
    # Test 2: Find similar
    print("\n" + "="*70)
    print("Test 2: Find Similar Facilities")
    print("="*70)
    if results:
        first_id = results[0]['facility_id']
        similar = rag.find_similar_facilities(first_id, k=3)
        
        print(f"\nFacilities similar to: {results[0]['name']}")
        for s in similar:
            print(f"  • {s['name']} ({s['address_city']})")
    
    # Test 3: RAG query
    print("\n" + "="*70)
    print("Test 3: RAG-Enhanced Query")
    print("="*70)
    result = rag.augmented_query("maternity care with specialists")
    print(result['answer'])
    
    rag.close()
    print("\n✅ RAG system test complete!")


if __name__ == "__main__":
    # Install scikit-learn if needed
    try:
        import sklearn
    except ImportError:
        print("Installing scikit-learn...")
        import subprocess
        subprocess.run(["pip", "install", "-q", "scikit-learn"])
    
    main()
