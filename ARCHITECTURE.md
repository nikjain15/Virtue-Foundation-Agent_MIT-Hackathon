# Architecture Overview

## 🎯 System Design

Multi-agent system for healthcare gap analysis in Ghana using:
- **AI**: OpenAI GPT-4 (natural language → SQL, planning)
- **Search**: FAISS (semantic search on facility descriptions)
- **Analysis**: Pattern matching + SQL analytics
- **UI**: Streamlit (chat-first interface)
- **Data**: DuckDB (987 healthcare facilities)

---

## 🤖 Agents

### 1. **Enhanced Agent** (`agents/enhanced_agent.py`)
**Purpose**: Main AI orchestrator with multi-modal capabilities
- Uses OpenAI GPT-4o-mini for SQL generation + planning
- FAISS semantic search for complex facility queries
- Multi-agent delegation (gap analysis, planning)
- Query routing (facility → gap → plan → compare)
- Visualization generation (Plotly charts)

**Key Methods**:
- `handle_query()` – Main entry point, routes to appropriate handler
- `_generate_sql_with_ai()` – OpenAI → SQL
- `_semantic_search()` – FAISS similarity search
- `_analyze_gaps()` – Identifies medical deserts
- `_generate_plan()` – Creates action plans
- `_compare_regions()` – Regional comparison charts

### 2. **Gap Analyzer Agent** (`agents/gap_analyzer_agent.py`)
**Purpose**: Identify healthcare deserts and specialty gaps
- No API keys required; pure SQL analytics
- Identifies regions/cities lacking specific specialties
- Categorizes severity (critical/severe/moderate)
- Regional coverage analysis

**Key Methods**:
- `identify_medical_deserts()` – Find underserved cities
- `analyze_specialty_gaps()` – Gaps by medical specialty
- `analyze_regional_coverage()` – Regional distribution

### 3. **Planning Agent** (`agents/planning_agent.py`)
**Purpose**: Generate actionable resource allocation plans
- No API keys required; heuristics-based
- Prioritizes cities by need
- Recommends specialty deployment
- Generates comprehensive action plans with timelines & costs
- Identifies partnership opportunities

**Key Methods**:
- `generate_action_plan()` – City-specific plan
- `prioritize_cities()` – Ranking by intervention need
- `recommend_specialty_deployment()` – Where to deploy specialists
- `find_nearby_facilities()` – Partnership discovery
- `create_regional_plan()` – Regional strategy

### 4. **Simple Query Agent** (`agents/simple_query_agent.py`)
**Purpose**: Fallback pattern-based querying (no AI needed)
- Pattern matching for common questions
- Works completely offline
- No API keys required

**Use Case**: Backup when OpenAI unavailable

### 5. **RAG System** (`tools/rag_system.py`)
**Purpose**: Semantic search with retrieval-augmented generation
- TF-IDF embeddings (no external embeddings API)
- FAISS indexing for fast similarity search
- Context retrieval for facility descriptions

**Key Methods**:
- `semantic_search()` – Find similar facilities
- `augmented_query()` – RAG-enhanced Q&A
- `find_similar_facilities()` – Facility recommendations

---

## 🛠️ Tools

### Data Pipeline
- `database_setup.py` – Load facilities → DuckDB
- `data_loader.py` – Excel/CSV ingestion
- `build_faiss_index.py` – Create semantic search index

### Analytics
- `geocoding_service.py` – Address → coordinates
- `medical_specialties.py` – Extract specialty keywords
- `organization_extraction.py` – Parse org types
- `facility_and_ngo_fields.py` – Field extraction
- `free_form.py` – Parse text descriptions

---

## 🎨 Frontend

### Streamlit App (`app.py`)
**Tabs** (chat-first):
1. **💬 AI Chat** – Multi-agent chat interface
   - Quick question buttons
   - Chat history with SQL/data transparency
   - Visualizations
   - Technical details toggle

2. **📊 Overview** – Key metrics + sample facilities

3. **🗺️ Interactive Map** – Folium map with facility pins

4. **📋 Data Table** – Searchable facility list

5. **📈 Statistics** – Charts & analytics

6. **🤖 Multi-Agent Dashboard** – Direct agent access
   - Query Agent
   - Gap Analyzer
   - Planning Agent
   - RAG Search
   - Combined Analysis

---

## 📊 Data Schema

### Facilities Table
- `facility_id`, `name`, `organization_type` (facility/ngo)
- `address_line1`, `address_city`, `address_region`, `address_country`
- `facility_type`, `description`

### Specialties Table
- `facility_id`, `specialty` (cardio, pediatric, surgery, etc.)

### Contact Info Table
- `facility_id`, `phone_numbers`, `email`, `website`

---

## 🔄 Query Flow

```
User Question
    ↓
Enhanced Agent (handle_query)
    ↓
Route to:
  • Semantic Search (FAISS) – complex, similarity-based
  • Gap Analysis – "desert", "lacking", "gap"
  • Planning – "plan", "fix", "improve"
  • Comparison – "compare", "versus"
  • Facility Query – default
    ↓
AI or Pattern Matching (fallback)
    ↓
SQL Query Execution (DuckDB)
    ↓
Format Answer + Visualizations
    ↓
Display in Streamlit Chat
```

---

## 🔐 Dependencies

### Core
- `streamlit` – UI
- `duckdb` – Database
- `openai` – GPT-4
- `faiss-cpu` – Vector search
- `folium` + `streamlit-folium` – Maps
- `plotly` – Visualizations

### NLP/ML
- `sentence-transformers` – Embeddings (FAISS)
- `scikit-learn` – TF-IDF (RAG)
- `tiktoken` – Token counting

---

## 🚀 Running the System

### Local Development
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python tools/database_setup.py      # Build DB
python tools/build_faiss_index.py   # Build embeddings
streamlit run app.py                # Run UI
```

### Testing Agents Standalone
```bash
python -m agents.enhanced_agent
python -m agents.gap_analyzer_agent
python -m agents.planning_agent
python -m agents.simple_query_agent
```

---

## ✅ Feature Completeness Checklist

- [x] **Query Agent**: Natural language Q&A with OpenAI + FAISS
- [x] **Gap Analyzer**: Medical desert identification by region/specialty
- [x] **Planning Agent**: Action plans, prioritization, deployment recommendations
- [x] **RAG System**: Semantic search with TF-IDF embeddings
- [x] **Streamlit Chat**: Multi-tab interface, history, visualizations
- [x] **Multi-Agent Dashboard**: Direct agent access
- [x] **Fallback Modes**: Works without API keys via patterns
- [x] **Data Pipeline**: Excel → DuckDB → Analysis
- [x] **Geocoding**: City-level coordinates for mapping
- [x] **Visualizations**: Plotly charts (gap analysis, comparisons)

---

## 🎯 Next Steps (Optional Enhancements)

1. **Caching**: Add Redis for query results
2. **Export**: PDF/Excel report generation
3. **Alerts**: Monitoring for critical gaps
4. **User Auth**: Login system for production
5. **Batch Processing**: Analyze multiple regions
6. **Mobile UI**: Responsive design for tablets
7. **Tracing**: OpenTelemetry integration for agent flow
