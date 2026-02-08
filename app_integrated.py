"""
Integrated Streamlit App - All Agents Combined

Integrates:
- Query Agent (simple pattern matching)
- Gap Analyzer Agent
- Planning Agent
- Your enhanced/unified agents (importable)
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import duckdb
import folium
from streamlit_folium import st_folium
import sys

# Import all agents
from agents.simple_query_agent import SimpleQueryAgent
from agents.gap_analyzer_agent import GapAnalyzerAgent
from agents.planning_agent import PlanningAgent
from tools.rag_system import RAGSystem

# Try to import your agents (if available)
try:
    from agents.enhanced_agent import EnhancedAgent
    ENHANCED_AVAILABLE = True
except:
    ENHANCED_AVAILABLE = False

try:
    from agents.unified_agent import UnifiedAgent
    UNIFIED_AVAILABLE = True
except:
    UNIFIED_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Ghana Healthcare - AI Agents",
    page_icon="🏥",
    layout="wide"
)

# Initialize agents (cached)
@st.cache_resource
def init_agents():
    """Initialize all agents"""
    agents = {
        'query': SimpleQueryAgent(),
        'gap': GapAnalyzerAgent(),
        'planning': PlanningAgent(),
        'rag': RAGSystem()
    }
    # Load RAG embeddings
    try:
        agents['rag'].load_embeddings()
    except:
        st.info("💡 First time? Creating RAG embeddings... (takes 30 seconds)")
        agents['rag'].create_simple_embeddings()
    
    return agents

# Database connection
@st.cache_resource
def get_database_connection():
    """Get DuckDB database connection"""
    db_path = "data/healthcare.duckdb"
    if not Path(db_path).exists():
        st.error(f"❌ Database not found: {db_path}")
        return None
    return duckdb.connect(db_path, read_only=True)

# Load data from database
@st.cache_data
def load_data_from_db():
    """Load facilities from database"""
    conn = get_database_connection()
    if conn is None:
        return None
    
    query = """
        SELECT 
            f.facility_id,
            f.name,
            f.organization_type,
            f.address_line1,
            f.address_city,
            f.address_region,
            f.address_country,
            f.facility_type,
            f.description,
            c.phone_numbers,
            c.email,
            c.website
        FROM facilities f
        LEFT JOIN contact_info c ON f.facility_id = c.facility_id
    """
    
    df = conn.execute(query).df()
    return df

# Title
st.title("🏥 Bridging Medical Deserts - AI Agent System")
st.markdown("**Multi-Agent System for Healthcare Gap Analysis & Planning**")
st.markdown("---")

# Initialize agents
agents = init_agents()

# Sidebar - Agent Selector
st.sidebar.header("🤖 AI Agent Selection")
agent_choice = st.sidebar.selectbox(
    "Choose an agent:",
    ["Query Agent", "Gap Analyzer", "Planning Agent", "RAG Search (NEW)", "Combined Analysis"]
)

st.sidebar.markdown("---")
st.sidebar.header("🔍 Filters")

# Load data
with st.spinner('📖 Loading data...'):
    df = load_data_from_db()

if df is None:
    st.stop()

# Filters
org_types = df['organization_type'].unique().tolist()
selected_org_type = st.sidebar.multiselect(
    "Organization Type:",
    options=org_types,
    default=org_types
)

cities = df['address_city'].dropna().unique().tolist()
cities.sort()
selected_city = st.sidebar.selectbox(
    "Select City for Analysis:",
    options=[""] + cities
)

# Main content based on agent selection
if agent_choice == "Query Agent":
    st.header("💬 Query Agent - Ask Questions")
    st.markdown("**Ask natural language questions about healthcare facilities**")
    
    # Predefined questions
    quick_questions = [
        "How many facilities are in Accra?",
        "Show me all NGOs",
        "Which hospitals handle cardiac care?",
    ]
    
    col1, col2 = st.columns([3, 1])
    with col1:
        user_question = st.text_input("Ask a question:", placeholder="e.g., How many facilities are in Kumasi?")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        use_example = st.selectbox("Or use example:", [""] + quick_questions)
    
    if use_example:
        user_question = use_example
    
    if user_question:
        with st.spinner('🤔 Processing question...'):
            result = agents['query'].answer_question(user_question)
        
        st.success("✅ Answer Generated")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("💬 Answer:")
            st.write(result['answer'])
        
        with col2:
            st.subheader("📊 Details:")
            st.metric("Results Found", result['results_count'])
        
        with st.expander("🔍 See SQL Query"):
            st.code(result['sql_query'], language='sql')
        
        with st.expander("📋 See Raw Results"):
            if result['results']:
                st.dataframe(pd.DataFrame(result['results']))

elif agent_choice == "Gap Analyzer":
    st.header("🏜️ Gap Analyzer - Medical Desert Identification")
    st.markdown("**Identify underserved areas and specialty gaps**")
    
    analysis_type = st.radio(
        "Analysis Type:",
        ["Regional Overview", "Specialty Gap Analysis", "Medical Deserts"]
    )
    
    if analysis_type == "Regional Overview":
        with st.spinner('🗺️ Analyzing regional coverage...'):
            regional = agents['gap'].analyze_regional_coverage()
        
        st.subheader("📍 Regional Coverage")
        df_regional = pd.DataFrame(regional['regional_breakdown'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Regions", regional['total_regions'])
        with col2:
            st.metric("Total Facilities", df_regional['total_facilities'].sum())
        
        st.dataframe(df_regional, width='stretch')
        
        # Chart
        st.bar_chart(df_regional.set_index('region')['total_facilities'].head(10))
    
    elif analysis_type == "Specialty Gap Analysis":
        specialty = st.selectbox(
            "Select Specialty:",
            ["cardio", "pediatric", "surgery", "oncology", "dental"]
        )
        
        if st.button("Analyze Gaps"):
            with st.spinner(f'🔍 Analyzing {specialty} gaps...'):
                gaps = agents['gap'].analyze_specialty_gaps(specialty)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Cities WITH Coverage", gaps['cities_with_coverage'])
            with col2:
                st.metric("Cities WITHOUT Coverage", gaps['cities_without_coverage'])
            
            if gaps['gap_cities']:
                st.subheader(f"⚠️ Cities Lacking {specialty.title()} Care:")
                st.write(", ".join(gaps['gap_cities'][:30]))
                
                if len(gaps['gap_cities']) > 30:
                    st.info(f"...and {len(gaps['gap_cities']) - 30} more cities")
    
    elif analysis_type == "Medical Deserts":
        min_facilities = st.slider("Minimum Facilities for Adequate Coverage:", 1, 10, 5)
        
        with st.spinner('🏜️ Identifying medical deserts...'):
            deserts = agents['gap'].identify_medical_deserts(min_facilities)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Critical (1 facility)", deserts['summary']['critical'], delta="Highest Priority", delta_color="inverse")
        with col2:
            st.metric("Severe (2 facilities)", deserts['summary']['severe'])
        with col3:
            st.metric("Moderate (3-4)", deserts['summary']['moderate'])
        
        tab1, tab2, tab3 = st.tabs(["🚨 Critical", "⚠️ Severe", "📊 Moderate"])
        
        with tab1:
            if deserts['critical_deserts']:
                st.dataframe(pd.DataFrame(deserts['critical_deserts']), width='stretch')
        
        with tab2:
            if deserts['severe_deserts']:
                st.dataframe(pd.DataFrame(deserts['severe_deserts']), width='stretch')
        
        with tab3:
            if deserts['moderate_deserts']:
                st.dataframe(pd.DataFrame(deserts['moderate_deserts']), width='stretch')

elif agent_choice == "RAG Search (NEW)":
    st.header("🔍 RAG - Semantic Search")
    st.markdown("**Find facilities by meaning, not just keywords**")
    st.info("💡 RAG uses AI embeddings to understand context and find similar facilities")
    
    search_query = st.text_input(
        "Semantic Search:",
        placeholder="e.g., 'maternity care with specialists', 'emergency cardiac surgery'"
    )
    
    num_results = st.slider("Number of results:", 3, 20, 10)
    
    if search_query:
        with st.spinner('🔍 Searching with semantic understanding...'):
            results = agents['rag'].semantic_search(search_query, k=num_results)
        
        st.success(f"✅ Found {len(results)} relevant facilities")
        
        # Display results
        for result in results:
            with st.expander(f"🏥 {result['name']} - {result['address_city']} (Match: {result['similarity_score']:.0%})"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Type**: {result['facility_type']}")
                    st.write(f"**Location**: {result['address_city']}")
                    if result['specialties']:
                        st.write(f"**Specialties**: {result['specialties']}")
                
                with col2:
                    st.metric("Relevance", f"{result['similarity_score']:.0%}")
                    st.metric("Rank", result['rank'])
                
                if result['description']:
                    st.markdown("**Description:**")
                    st.write(result['description'][:300] + "...")

elif agent_choice == "Planning Agent":
    st.header("📋 Planning Agent - Resource Allocation")
    st.markdown("**Generate actionable plans to address healthcare gaps**")
    
    if selected_city:
        st.info(f"🎯 Generating action plan for: **{selected_city}**")
        
        with st.spinner('📋 Creating action plan...'):
            plan = agents['planning'].generate_action_plan(selected_city)
        
        # Display plan
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Facilities", plan['current_facilities'])
        with col2:
            st.metric("Assessment", plan['assessment'])
        with col3:
            st.metric("Timeline", plan['estimated_timeline'])
        
        st.subheader("💡 Recommendations:")
        for i, rec in enumerate(plan['recommendations'], 1):
            st.write(f"{i}. {rec}")
        
        if plan.get('nearby_partners'):
            with st.expander("🤝 Partnership Opportunities"):
                partners_df = pd.DataFrame(plan['nearby_partners'])
                st.dataframe(partners_df[['name', 'address_city', 'organization_type']], width='stretch')
        
        st.info(f"💰 **Estimated Cost**: {plan['estimated_cost']}")
    
    else:
        st.warning("⚠️ Please select a city from the sidebar to generate an action plan")
        
        # Show priority cities
        st.subheader("🎯 Priority Cities for Intervention")
        with st.spinner('Analyzing priorities...'):
            priorities = agents['planning'].prioritize_cities()
        
        df_priorities = pd.DataFrame(priorities[:20])
        st.dataframe(df_priorities, width='stretch')

elif agent_choice == "Combined Analysis":
    st.header("🔬 Combined Multi-Agent Analysis")
    st.markdown("**Comprehensive analysis using all agents**")
    
    if selected_city:
        st.info(f"🎯 Running full analysis for: **{selected_city}**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("1️⃣ Current Situation")
            with st.spinner('Querying data...'):
                result = agents['query'].answer_question(f"How many facilities are in {selected_city}?")
            st.write(result['answer'])
        
        with col2:
            st.subheader("2️⃣ Gap Analysis")
            with st.spinner('Analyzing gaps...'):
                # Check if city is a medical desert
                deserts = agents['gap'].identify_medical_deserts()
                is_desert = any(d['address_city'].lower() == selected_city.lower() 
                               for d in deserts['critical_deserts'] + deserts['severe_deserts'])
            
            if is_desert:
                st.error("🏜️ This is a medical desert!")
            else:
                st.success("✅ Adequate coverage detected")
        
        st.subheader("3️⃣ Action Plan")
        with st.spinner('Generating plan...'):
            plan = agents['planning'].generate_action_plan(selected_city)
        
        st.write(f"**Assessment**: {plan['assessment']}")
        st.write(f"**Timeline**: {plan['estimated_timeline']}")
        st.write(f"**Cost**: {plan['estimated_cost']}")
        
        with st.expander("📋 See Full Recommendations"):
            for i, rec in enumerate(plan['recommendations'], 1):
                st.write(f"{i}. {rec}")
    
    else:
        st.warning("⚠️ Please select a city from the sidebar for combined analysis")
        
        # Show summary
        st.subheader("📊 System Overview")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Facilities", len(df))
        
        with col2:
            deserts = agents['gap'].identify_medical_deserts()
            st.metric("Medical Deserts", deserts['total_underserved_cities'])
        
        with col3:
            regional = agents['gap'].analyze_regional_coverage()
            st.metric("Regions Covered", regional['total_regions'])

# Footer
st.markdown("---")
st.markdown("**🤖 Multi-Agent System**: Query + Gap Analysis + Planning + **RAG (NEW)**")
st.markdown("**📊 Data Source**: 987 healthcare facilities | **🔍 RAG**: 658 facilities with semantic search")
st.markdown("**💡 RAG Status**: ✅ Using FAISS + TF-IDF embeddings for semantic similarity")
