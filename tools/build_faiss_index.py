"""
Build FAISS Vector Index for Semantic Search

Purpose: Create embeddings of facility data for semantic search
This allows natural language queries like "Find trauma centers near coast"
"""

import duckdb
import faiss
import numpy as np
import pickle
from pathlib import Path
from sentence_transformers import SentenceTransformer

def build_faiss_index():
    """Build FAISS index from facility data"""
    
    print("🔨 Building FAISS Index...")
    print("=" * 70)
    
    # Load embedding model (open-source, runs locally)
    print("📥 Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')  # Fast, 384 dimensions
    print("✅ Model loaded\n")
    
    # Connect to database
    print("📊 Loading facility data...")
    conn = duckdb.connect('data/healthcare.duckdb', read_only=True)
    
    # Get facilities with specialties
    query = """
        SELECT 
            f.facility_id,
            f.name,
            f.organization_type,
            f.address_city,
            f.address_region,
            f.facility_type,
            f.description,
            GROUP_CONCAT(s.specialty, ', ') as specialties
        FROM facilities f
        LEFT JOIN specialties s ON f.facility_id = s.facility_id
        GROUP BY f.facility_id, f.name, f.organization_type, 
                 f.address_city, f.address_region, f.facility_type, f.description
    """
    
    df = conn.execute(query).df()
    print(f"✅ Loaded {len(df)} facilities\n")
    
    # Create searchable text for each facility
    print("📝 Creating searchable text...")
    texts = []
    for _, row in df.iterrows():
        text_parts = [
            f"Name: {row['name']}",
            f"Type: {row['organization_type']}",
            f"Location: {row['address_city']}, {row['address_region']}",
        ]
        
        if row['facility_type']:
            text_parts.append(f"Facility Type: {row['facility_type']}")
        
        if row['specialties']:
            text_parts.append(f"Specialties: {row['specialties']}")
        
        if row['description']:
            text_parts.append(f"Description: {row['description']}")
        
        texts.append(" | ".join(text_parts))
    
    print(f"✅ Created {len(texts)} text documents\n")
    
    # Generate embeddings
    print("🧠 Generating embeddings (this takes ~30 seconds)...")
    embeddings = model.encode(texts, show_progress_bar=True)
    print(f"✅ Generated embeddings: {embeddings.shape}\n")
    
    # Build FAISS index
    print("🔍 Building FAISS index...")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)  # L2 distance (cosine similarity alternative)
    index.add(embeddings.astype('float32'))
    print(f"✅ Index built with {index.ntotal} vectors\n")
    
    # Save index and metadata
    print("💾 Saving index and metadata...")
    Path('data').mkdir(exist_ok=True)
    
    # Save FAISS index
    faiss.write_index(index, 'data/faiss_index.bin')
    
    # Save metadata (facility info for each embedding)
    metadata = df.to_dict('records')
    with open('data/faiss_metadata.pkl', 'wb') as f:
        pickle.dump(metadata, f)
    
    print("✅ Saved:")
    print("  - data/faiss_index.bin (FAISS index)")
    print("  - data/faiss_metadata.pkl (facility metadata)")
    print("\n" + "=" * 70)
    print("✅ FAISS index ready!")
    print("\nNow you can use semantic search like:")
    print('  - "Find trauma centers near the coast"')
    print('  - "Hospitals with advanced cardiac care"')
    print('  - "Pediatric clinics in rural areas"')
    
if __name__ == "__main__":
    build_faiss_index()
