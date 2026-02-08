# Bridging Medical Deserts -- Strategy & Architecture

## 1. Problem Statement

The Virtue Foundation has messy, unstructured data about healthcare facilities in Ghana. Skilled doctors are disconnected from hospitals that need them. We're building an **agentic AI system** that parses documents, extracts structured medical data, identifies medical deserts, and gives NGO planners an intuitive interface to act.

**Goal**: Reduce the time for patients to receive lifesaving treatment by 100x through intelligent coordination.

---

## 2. Scoring Strategy

| Criteria | Weight | Our Play |
|----------|--------|----------|
| Technical Accuracy | 35% | Multi-agent extraction pipeline with anomaly detection |
| IDP Innovation | 30% | Structured Pydantic extraction from free-form text with validation |
| Social Impact | 25% | Medical desert identification by region, specialty, capability |
| User Experience | 10% | Streamlit chat + interactive Ghana map |

---

## 3. Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Agent framework** | **Google ADK** | Already installed. Native tracing via OpenTelemetry events. Built-in session state. Citation-level logging via callbacks + event system. |
| **LLM** | **OpenAI GPT-4o** | API key provided. Fast, strong at structured output / tool use. Integrated with Google ADK framework. |
| **Frontend** | **Streamlit** | Fastest path to chat + map + tables in one app. |
| **Map** | **Folium** | Lightweight, interactive, renders in Streamlit via `streamlit-folium`. |
| **Geocoding** | **Nominatim (OpenStreetMap)** | Free geocoding API, no key needed. Converts city names to coordinates for 100% map coverage. |
| **Vector store** | **FAISS** | In-memory, zero setup, perfect for small dataset. |
| **Structured DB** | **DuckDB** | In-process SQL, zero config, fast analytics. Perfect for 987 facilities. |
| **Tracing** | **ADK native events + callbacks** | Every agent step logs input/output/data used. Exportable traces. |

### Implementation Notes:
- **OpenAI API Setup Required**: Add billing at https://platform.openai.com/settings/organization/billing/overview
- **Database**: DuckDB chosen over PostgreSQL for speed and simplicity (10-100x faster for analytics)
- **Geocoding**: Automated via Nominatim API with local caching to respect rate limits (1 req/sec)
- **Map Coverage**: 987 facilities across 100+ cities in Ghana, all geocoded and displayed

---

## 4. Architecture

### 4.1 System Design

```
+=============================================================+
|                    STREAMLIT FRONTEND                         |
|                                                               |
|  +----------------+  +------------------+  +---------------+  |
|  | Chat Panel     |  | Ghana Map        |  | Data Panel    |  |
|  |                |  | (Folium)         |  |               |  |
|  | NL queries     |  | - Facility pins  |  | Facility list |  |
|  | with cited     |  | - Color by type  |  | Gap summary   |  |
|  | responses      |  | - Desert zones   |  | Anomaly flags |  |
|  +----------------+  +------------------+  +---------------+  |
+=============================================================+
                            |
                            v
+=============================================================+
|              GOOGLE ADK -- MULTI-AGENT SYSTEM                 |
|                                                               |
|  +----------------------------------------------------------+|
|  | ROOT AGENT (Router/Orchestrator)                          ||
|  | Classifies intent, delegates to sub-agents                ||
|  +----+------------+------------+------------+---------+-----+|
|       |            |            |            |         |      |
|       v            v            v            v         v      |
|  +---------+ +---------+ +---------+ +--------+ +--------+  |
|  | PARSER  | |VALIDATOR| |   GAP   | | QUERY  | |PLANNING|  |
|  | AGENT   | | AGENT   | |ANALYZER | | AGENT  | | AGENT  |  |
|  |         | |         | |         | |        | |        |  |
|  | Extract | | Cross-  | | Find    | | Answer | | Action |  |
|  | orgs,   | | ref,    | | medical | | NL Qs  | | plans, |  |
|  | special-| | flag    | | deserts | | w/ RAG | | resource|  |
|  | ties,   | | anomal- | | by area | | + SQL  | | alloc  |  |
|  | facts   | | ies     | | & spec  | | + cite | |        |  |
|  +---------+ +---------+ +---------+ +--------+ +--------+  |
|                                                               |
|  [EVENT TRACING -- every step: input -> output -> citations] |
+=============================================================+
                            |
                            v
+=============================================================+
|                       DATA LAYER                              |
|                                                               |
|  +---------------+  +---------------+  +------------------+  |
|  | FAISS         |  | DuckDB        |  | Raw Data         |  |
|  | Vector Store  |  | SQL Tables    |  |                  |  |
|  |               |  |               |  | Ghana Excel      |  |
|  | Embeddings of |  | facilities    |  | Pydantic models  |  |
|  | free-form     |  | specialties   |  | Schema docs      |  |
|  | text + row    |  | capabilities  |  |                  |  |
|  | metadata      |  | gaps          |  |                  |  |
|  +---------------+  +---------------+  +------------------+  |
+=============================================================+
```

### 4.2 Agents

| Agent | Role | Inputs | Outputs | Tools |
|-------|------|--------|---------|-------|
| **Root (Router)** | Classify user intent, delegate to sub-agent | User query | Agent selection + routing | Intent classification prompt |
| **Parser** | Extract structured data from unstructured text | Raw text | Pydantic models (Org, Facility, NGO, Specialties, Facts) | `parse_facility_text`, `classify_specialty`, `extract_facts` |
| **Validator** | Cross-reference extracted data, flag anomalies | Structured facility data | Anomaly reports, confidence scores | `validate_facility`, `check_consistency` |
| **Gap Analyzer** | Identify medical deserts and coverage gaps | All facility data, regional info | Gap reports by region/specialty/capability | `analyze_region_gaps`, `rank_severity` |
| **Query** | Answer natural language questions with citations | User query, facility data | Answer + row-level citations | `vector_search`, `sql_query` |
| **Planning** | Generate actionable resource allocation plans | Gap analysis, facility data | Priority-ranked action plans | `generate_plan`, `prioritize_interventions` |

### 4.3 Data Flow

```
INGEST (startup)
  Ghana Excel
    --> pandas reads rows
    --> For each facility:
         LLM extracts structured data using provided Pydantic schemas
           - OrganizationExtractionOutput (NGO vs Facility)
           - MedicalSpecialties
           - FacilityFacts (procedure, equipment, capability)
           - Facility / NGO fields (address, contact, capacity)
    --> Store in DuckDB (structured queries)
    --> Embed free-form text + store in FAISS (semantic search)
    --> Row ID + column stored as metadata for citations

QUERY TIME (user interaction)
  User: "Which hospitals in Northern Ghana handle trauma?"
    --> Root Agent: intent = facility_query
    --> Query Agent:
         Step 1: FAISS search "trauma Northern Ghana" --> rows [5, 12, 34]
         Step 2: DuckDB: SELECT * FROM facilities WHERE region='Northern'
         Step 3: Synthesize answer with citations
    --> Response with [Row X, Column Y] citations

  User: "Where are the medical deserts for cardiac care?"
    --> Root Agent: intent = gap_analysis
    --> Gap Analyzer:
         Step 1: DuckDB: aggregate specialties by region
         Step 2: Identify regions with zero cardiac capabilities
         Step 3: Rank by population / severity
    --> Map highlights + gap report

  User: "Create a plan to fix cardiac gaps in Volta Region"
    --> Root Agent: intent = planning
    --> Planning Agent:
         Step 1: Get gap analysis for Volta
         Step 2: Identify nearest facilities with cardiac capability
         Step 3: Generate deployment / partnership plan
    --> Actionable plan with priorities
```

---

## 5. Why Google ADK Works for Citations (Stretch Goal)

ADK provides full agentic-step-level tracing natively:

| ADK Feature | How It Enables Citations |
|-------------|------------------------|
| **Event system** | Every agent step is an `Event` with author, content, actions, metadata. Complete chronological trace. |
| **session.events** | Full history of every interaction -- inputs, outputs, tool calls, state changes. Queryable. |
| **Callbacks** | `before_model_callback` / `after_model_callback` log exactly what data went into each LLM call and what came out. |
| **ToolContext** | Tracks which agent called which tool with what parameters. Perfect for "Step 2 used rows [5, 12, 34]". |
| **invocation_id** | Correlates all events within a single user query. |
| **OpenTelemetry** | Native OTel spans for agent runs, tool calls, model requests. Export to any backend. |
| **MLflow integration** | MLflow 3.6+ ingests ADK's OTel traces directly. |

**Example trace:**
```
Query: "Does Korle-Bu have cardiac surgery?"

Event 1 (Root Agent): intent=facility_query --> delegate to Query Agent
  data_used: none

Event 2 (Query Agent - vector_search): "cardiac surgery Korle-Bu"
  data_used: Retrieved rows [12, 15] from FAISS
  metadata: {row_ids: [12, 15], columns: ["procedure", "capability"]}

Event 3 (Query Agent - sql_query): SELECT specialties FROM facilities WHERE name LIKE '%Korle-Bu%'
  data_used: Row 12, specialties column

Event 4 (Query Agent - synthesis): Generated answer
  input: chunks from events 2+3
  output: "Yes, Korle-Bu has cardiac surgery including CABG and cath lab."
  citations: [Row 12: procedure, Row 12: capability, Row 12: specialties]
```

---

## 6. Deliverables (MVP + Stretch Combined)

| # | Deliverable | Category | How |
|---|-------------|----------|-----|
| 1 | Unstructured text extraction | MVP | Parser Agent uses provided Pydantic models + prompts to extract procedure/equipment/capability |
| 2 | Intelligent synthesis | MVP | Combine extracted free-form facts with structured facility fields into unified DuckDB tables |
| 3 | Planning system | MVP | Planning Agent generates resource allocation plans accessible via chat |
| 4 | Row-level citations | Stretch | FAISS metadata tracks row_id + column. Every answer cites its sources. |
| 5 | Agentic-step-level tracing | Stretch | ADK event system + callbacks log input/output/data at every agent step |
| 6 | Interactive map | Stretch | Folium map in Streamlit showing facilities, capabilities, desert zones |
| 7 | Real-world agent questions | Stretch | Use the Virtue Foundation questions doc as demo scenarios |

---

## 7. Project Structure

```
bridging-medical-deserts/
├── STRATEGY.md                 # This document
├── app.py                      # Streamlit frontend
├── agents/
│   ├── root_agent.py           # Router/orchestrator (ADK Agent)
│   ├── parser_agent.py         # Document parsing + extraction
│   ├── validator_agent.py      # Anomaly detection
│   ├── gap_analyzer_agent.py   # Medical desert identification
│   ├── query_agent.py          # RAG + SQL query answering
│   └── planning_agent.py       # Resource allocation planning
├── tools/
│   ├── vector_search.py        # FAISS search tool
│   ├── sql_query.py            # DuckDB query tool
│   ├── parse_facility.py       # Pydantic extraction tool
│   └── map_tools.py            # Geo tools for map
├── data/
│   ├── ingest.py               # Load Excel --> DuckDB + FAISS
│   └── schemas.py              # Reuse provided Pydantic models
├── tracing/
│   └── callbacks.py            # ADK callbacks for citation logging
├── requirements.txt
├── .env                        # OPENAI_API_KEY (gitignored)
└── .gitignore
```

---

## 8. Key Files to Reuse (Provided by Challenge)

| Source File | Reuse As |
|-------------|----------|
| `prompts_and_pydantic_models/organization_extraction.py` | Parser agent's org extraction prompt + output model |
| `prompts_and_pydantic_models/medical_specialties.py` | Parser agent's specialty classification prompt + model |
| `prompts_and_pydantic_models/free_form.py` | Parser agent's fact extraction prompt + model |
| `prompts_and_pydantic_models/facility_and_ngo_fields.py` | Facility/NGO data models for structured storage |
| `Virtue Foundation Ghana v0.3 - Sheet1.xlsx` | Primary dataset to ingest |
| `Virtue Foundation Agent Questions - Hack Nation.docx` | Test queries + demo scenarios |

---

## 9. Implementation Phases

| Phase | What | Deliverable |
|-------|------|-------------|
| 1 | **Project scaffold** | Directory structure, deps installed, Excel loaded into pandas, DuckDB tables created, FAISS index built |
| 2 | **Core agents** | ADK agents: Root (router), Parser (extraction), Query (RAG+SQL), Validator (anomaly flags) |
| 3 | **Gap + Planning** | Gap Analyzer agent (medical desert detection), Planning agent (resource allocation) |
| 4 | **Streamlit UI** | Chat panel (ADK agent responses), Folium map (facility pins + desert zones), data tables |
| 5 | **Citations + tracing** | ADK callbacks for step-level logging, citations displayed in chat responses |
| 6 | **Demo prep** | Test with VF agent questions, fix edge cases, prepare demo flow |
