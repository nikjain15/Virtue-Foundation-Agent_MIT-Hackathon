"""
Bridging Medical Deserts - Main Streamlit Application

Purpose: Web interface for NGO planners to explore Ghana healthcare facilities
Author: MIT Hackathon Team
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import duckdb
import folium
from streamlit_folium import st_folium
import sys
import os
sys.path.append(str(Path(__file__).parent))
from agents.enhanced_agent import EnhancedAgent
from agents.simple_query_agent import SimpleQueryAgent
from agents.gap_analyzer_agent import GapAnalyzerAgent
from agents.planning_agent import PlanningAgent
from tools.rag_system import RAGSystem
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Ghana Healthcare Facilities",
    page_icon="🏥",
    layout="wide"
)

# Title
st.title("🏥 Bridging Medical Deserts - Ghana Healthcare")
st.markdown("**Helping NGOs identify healthcare gaps and plan interventions**")
st.markdown("---")

# Database connection
@st.cache_resource
def get_database_connection():
    """
    Get DuckDB database connection (cached for performance)
    
    Why cache? We only want to connect once, not on every interaction
    """
    db_path = "data/healthcare.duckdb"
    if not Path(db_path).exists():
        st.error(f"❌ Database not found: {db_path}")
        st.info("💡 Run `python tools/database_setup.py` to create the database")
        return None
    return duckdb.connect(db_path, read_only=True)


# Load data from database
@st.cache_data
def load_data_from_db():
    """
    Load healthcare facilities from DuckDB database
    
    Why database instead of Excel?
    - Much faster queries (10-100x)
    - Can filter efficiently
    - Support complex SQL queries
    """
    conn = get_database_connection()
    if conn is None:
        return None
    
    # Query all facilities with contact info
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


# Load facilities with coordinates (for map)
@st.cache_data
def load_facilities_with_locations():
    """
    Load facilities that have geographic coordinates
    
    Note: We need coordinates (latitude, longitude) to show on map
    For now, we'll use city-level coordinates
    """
    # Ghana city coordinates (approximate center points)
    city_coords = {
        'Accra': (5.6037, -0.1870),
        'Kumasi': (6.6885, -1.6244),
        'Tema': (5.6698, 0.0166),
        'Takoradi': (4.8845, -1.7554),
        'Tamale': (9.4034, -0.8424),
        'Cape Coast': (5.1053, -1.2466),
        'Sunyani': (7.3390, -2.3267),
        'Koforidua': (6.0942, -0.2606),
        'Ho': (6.6111, 0.4700),
        'Wa': (10.0603, -2.5095),
        'Bolgatanga': (10.7856, -0.8514),
        'Techiman': (7.5926, -1.9385),
    }
    
    conn = get_database_connection()
    if conn is None:
        return pd.DataFrame()
    
    df = conn.execute("""
        SELECT 
            f.facility_id,
            f.name,
            f.address_city,
            f.organization_type,
            f.facility_type,
            COUNT(s.specialty) as specialty_count
        FROM facilities f
        LEFT JOIN specialties s ON f.facility_id = s.facility_id
        WHERE f.address_city != ''
        GROUP BY f.facility_id, f.name, f.address_city, f.organization_type, f.facility_type
    """).df()
    
    # Add coordinates based on city
    df['latitude'] = df['address_city'].map(lambda city: city_coords.get(city, (None, None))[0])
    df['longitude'] = df['address_city'].map(lambda city: city_coords.get(city, (None, None))[1])
    
    # Only keep rows with valid coordinates
    df = df.dropna(subset=['latitude', 'longitude'])
    
    return df


@st.cache_resource
def init_multi_agents():
    """Initialize multi-agent tools"""
    agents = {
        "query": SimpleQueryAgent(),
        "gap": GapAnalyzerAgent(),
        "planning": PlanningAgent(),
        "rag": RAGSystem()
    }
    try:
        agents["rag"].load_embeddings()
    except Exception:
        agents["rag"].create_simple_embeddings()
    return agents

# Main app
def main():
    """Main application logic"""
    
    # Load the data from database
    with st.spinner('📖 Loading healthcare facility data from database...'):
        df = load_data_from_db()
    
    if df is None:
        st.stop()
    
    # Show success message with database info
    st.success(f"✅ Loaded {len(df)} healthcare facilities from DuckDB database")
    
    # Sidebar filters
    st.sidebar.header("🔍 Filter Facilities")
    
    # Filter by organization type
    org_types = df['organization_type'].unique().tolist()
    selected_org_type = st.sidebar.multiselect(
        "Organization Type:",
        options=org_types,
        default=org_types
    )
    
    # Filter by city
    cities = df['address_city'].dropna().unique().tolist()
    cities.sort()
    selected_cities = st.sidebar.multiselect(
        "City:",
        options=cities,
        default=[]
    )
    
    # Apply filters
    filtered_df = df.copy()
    if selected_org_type:
        filtered_df = filtered_df[filtered_df['organization_type'].isin(selected_org_type)]
    if selected_cities:
        filtered_df = filtered_df[filtered_df['address_city'].isin(selected_cities)]
    
    # Show filtered count
    st.sidebar.markdown(f"**Showing {len(filtered_df)} of {len(df)} facilities**")
    
    # Main content area
    tab_chat, tab1, tab2, tab3, tab4, tab6 = st.tabs([
        "💬 AI Chat",
        "📊 Overview",
        "🗺️ Interactive Map",
        "📋 Data Table",
        "📈 Statistics",
        "🤖 Multi-Agent"
    ])
    
    with tab1:
        st.header("Overview")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Facilities", len(filtered_df))
        
        with col2:
            facilities_count = len(filtered_df[filtered_df['organization_type'] == 'facility'])
            st.metric("Healthcare Facilities", facilities_count)
        
        with col3:
            ngos_count = len(filtered_df[filtered_df['organization_type'] == 'ngo'])
            st.metric("NGOs", ngos_count)
        
        with col4:
            cities_count = filtered_df['address_city'].nunique()
            st.metric("Cities Covered", cities_count)
        
        st.markdown("---")
        
        # Show sample facilities
        st.subheader("Sample Facilities")
        st.dataframe(
            filtered_df[['name', 'address_city', 'organization_type', 'phone_numbers']].head(10),
            width='stretch'
        )
    
    with tab2:
        st.header("🗺️ Ghana Healthcare Facilities Map")
        st.markdown("**Interactive map showing facility locations across Ghana**")
        
        # Load facilities with coordinates
        map_df = load_facilities_with_locations()
        
        # Apply same filters
        if selected_org_type:
            map_df = map_df[map_df['organization_type'].isin(selected_org_type)]
        if selected_cities:
            map_df = map_df[map_df['address_city'].isin(selected_cities)]
        
        if len(map_df) == 0:
            st.warning("⚠️ No facilities to display on map with current filters")
        else:
            st.info(f"📍 Showing {len(map_df)} facilities on map")
            
            # Create map centered on Ghana
            ghana_center = [7.9465, -1.0232]  # Center of Ghana
            m = folium.Map(
                location=ghana_center,
                zoom_start=7,
                tiles='OpenStreetMap'
            )
            
            # Color coding for organization types
            color_map = {
                'facility': 'blue',
                'ngo': 'green'
            }
            
            # Add markers for each facility
            for idx, row in map_df.iterrows():
                color = color_map.get(row['organization_type'], 'gray')
                
                # Create popup with facility info
                popup_html = f"""
                <div style="width: 200px;">
                    <h4>{row['name'][:50]}</h4>
                    <p><b>City:</b> {row['address_city']}</p>
                    <p><b>Type:</b> {row['organization_type']}</p>
                    <p><b>Facility Type:</b> {row['facility_type']}</p>
                    <p><b>Specialties:</b> {row['specialty_count']}</p>
                </div>
                """
                
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=6,
                    popup=folium.Popup(popup_html, max_width=250),
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7,
                    tooltip=row['name'][:50]
                ).add_to(m)
            
            # Add legend
            legend_html = '''
            <div style="position: fixed; 
                        bottom: 50px; right: 50px; width: 150px; height: 90px; 
                        background-color: white; border:2px solid grey; z-index:9999; 
                        font-size:14px; padding: 10px">
                <p><b>Legend</b></p>
                <p><span style="color:blue;">●</span> Healthcare Facility</p>
                <p><span style="color:green;">●</span> NGO</p>
            </div>
            '''
            m.get_root().html.add_child(folium.Element(legend_html))
            
            # Display map in Streamlit
            st_folium(m, width=1200, height=600)
    
    with tab3:
        st.header("Full Data Table")
        st.markdown("**All facility data with search and sort capabilities**")
        
        # Show full dataframe
        st.dataframe(
            filtered_df,
            width='stretch',
            height=500
        )
        
        # Download button
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=csv,
            file_name="ghana_facilities_filtered.csv",
            mime="text/csv"
        )
    
    with tab4:
        st.header("Statistics")
        
        # Organization type distribution
        st.subheader("Organization Types")
        org_type_counts = filtered_df['organization_type'].value_counts()
        st.bar_chart(org_type_counts)
        
        # Cities distribution (top 20)
        st.subheader("Top 20 Cities by Facility Count")
        city_counts = filtered_df['address_city'].value_counts().head(20)
        st.bar_chart(city_counts)
        
        # Data completeness
        st.subheader("Data Completeness")
        completeness = (filtered_df.notna().sum() / len(filtered_df) * 100).sort_values(ascending=False)
        completeness_df = pd.DataFrame({
            'Field': completeness.index,
            'Completeness %': completeness.values
        })
        st.dataframe(completeness_df, width='stretch', height=400)
    
    with tab_chat:
        st.header("💬 AI-Powered Chat Assistant")
        st.markdown("**Ask questions about facilities, gaps, and planning.**")
        st.caption("Tip: Use the quick prompts below or type your own question.")
        
        # Initialize agent (cached)
        @st.cache_resource
        def get_agent():
            return EnhancedAgent()
        
        try:
            agent = get_agent()
            
            # Show capabilities
            col1, col2, col3 = st.columns(3)
            with col1:
                if getattr(agent, "has_openai", False):
                    st.success("🧠 **LLM**\nOpenAI enabled")
                else:
                    st.warning("🧠 **LLM**\nPattern-only mode")
            with col2:
                if getattr(agent, "has_faiss", False):
                    st.success("🔍 **Semantic Search**\nFAISS ready")
                else:
                    st.warning("🔍 **Semantic Search**\nFAISS not ready")
            with col3:
                st.info("📊 **Charts**\nInteractive visuals")
            
            with st.expander("ℹ️ How it works", expanded=False):
                st.markdown(
                    """
                    - Ask a question in natural language.
                    - The agent routes it to SQL, semantic search, or planning.
                    - You can reveal SQL and data for transparency.
                    """
                )
            
            st.markdown("---")
            
            # Initialize chat history
            if 'chat_history' not in st.session_state:
                st.session_state.chat_history = []
            
            # Sample questions with categories
            st.markdown("### 🎯 Try These Questions:")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**📍 Facility Queries**")
                if st.button("How many hospitals in Greater Accra?", key="q1"):
                    st.session_state.pending_question = "How many hospitals in Greater Accra?"
                if st.button("Find trauma centers with ICU", key="q2"):
                    st.session_state.pending_question = "Find trauma centers with ICU capabilities"
                if st.button("List all pediatric hospitals", key="q3"):
                    st.session_state.pending_question = "Which facilities specialize in pediatric care?"
            
            with col2:
                st.markdown("**⚠️ Gap Analysis**")
                if st.button("Where are cardiac care gaps?", key="q4"):
                    st.session_state.pending_question = "Where are cardiac care gaps?"
                if st.button("Which regions lack surgery?", key="q5"):
                    st.session_state.pending_question = "Which regions lack surgical facilities?"
                if st.button("Show medical deserts", key="q6"):
                    st.session_state.pending_question = "Show me the most underserved regions"
            
            with col3:
                st.markdown("**📊 Analysis & Planning**")
                if st.button("Compare Accra vs Kumasi", key="q7"):
                    st.session_state.pending_question = "Compare healthcare between Accra and Kumasi"
                if st.button("Plan for Northern region", key="q8"):
                    st.session_state.pending_question = "Create a plan to improve healthcare in Northern region"
                if st.button("NGO partnership opportunities", key="q9"):
                    st.session_state.pending_question = "Which NGOs could partner for rural health?"
            
            st.markdown("---")
            show_details = st.toggle(
                "Show technical details (SQL & data)",
                value=st.session_state.get("show_details", True),
                key="show_details"
            )
            
            # Chat input
            st.caption("Press Enter to send")
            user_question = st.chat_input("Ask about facilities, gaps, or plans")
            
            if "pending_question" in st.session_state and not user_question:
                user_question = st.session_state.pop("pending_question")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                pass
            with col2:
                if st.session_state.chat_history:
                    if st.button("🗑️ Clear Chat", use_container_width=True):
                        st.session_state.chat_history = []
                        st.rerun()
            
            if user_question:
                # Add question to history
                st.session_state.chat_history.append({
                    'role': 'user',
                    'content': user_question
                })
                
                # Get answer from agent
                with st.spinner("🤔 Thinking with AI..."):
                    result = agent.handle_query(user_question)
                    
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'content': result['answer'],
                        'type': result.get('type'),
                        'sql': result.get('sql'),
                        'data': result.get('data'),
                        'visualization': result.get('visualization')
                    })
                    
                    st.rerun()  # Refresh to show new message
            
            # Display chat history
            st.markdown("### 💬 Conversation")
            
            if not st.session_state.chat_history:
                st.info("👋 Ask a question to get started! Try the sample questions above.")
            
            for i, msg in enumerate(st.session_state.chat_history):
                if msg['role'] == 'user':
                    with st.chat_message("user", avatar="👤"):
                        st.write(msg['content'])
                else:
                    with st.chat_message("assistant", avatar="🤖"):
                        # Show answer
                        st.markdown(msg['content'])
                        
                        # Show visualization if available
                        if 'visualization' in msg and msg['visualization']:
                            st.plotly_chart(msg['visualization'], use_container_width=True)
                        
                        # Show data table in expander
                        if show_details and 'data' in msg and msg['data'] and len(msg['data']) > 0:
                            with st.expander("📋 View Data Table"):
                                df = pd.DataFrame(msg['data'])
                                st.dataframe(df, use_container_width=True)
                        
                        # Show SQL query in expander
                        if show_details and 'sql' in msg and msg['sql']:
                            with st.expander("🔍 View SQL Query"):
                                st.code(msg['sql'], language='sql')
                        
                        # Show query type badge
                        if 'type' in msg:
                            type_emoji = {
                                'ai_query': '🤖 AI-Generated',
                                'semantic_search': '🔍 Semantic Search',
                                'gap_analysis': '⚠️ Gap Analysis',
                                'planning': '📋 Planning',
                                'comparison': '📊 Comparison',
                                'pattern_query': '🔧 Pattern Match'
                            }
                            st.caption(type_emoji.get(msg['type'], msg['type']))
        
        except Exception as e:
            st.error(f"❌ Error initializing enhanced agent: {str(e)}")
            st.info("""
            **Setup Required:**
            1. Install dependencies: `pip install -r requirements.txt`
            2. Build FAISS index: `python tools/build_faiss_index.py`
            3. Set OpenAI key in `.env`: `OPENAI_API_KEY=your-key`
            4. Restart Streamlit
            
            **Current Status:**
            - Database: {}
            - FAISS index: {}
            - OpenAI key: {}
            """.format(
                "✅" if Path('data/healthcare.duckdb').exists() else "❌",
                "✅" if Path('data/faiss_index.bin').exists() else "❌ (run build_faiss_index.py)",
                "✅" if os.getenv('OPENAI_API_KEY') else "❌ (add to .env)"
            ))

    with tab6:
        st.header("🤖 Multi-Agent Dashboard")
        st.markdown("**Run specialized agents for query, gaps, planning, and RAG search.**")

        with st.spinner("⚙️ Initializing agents..."):
            agents = init_multi_agents()

        agent_choice = st.selectbox(
            "Choose an agent:",
            ["Query Agent", "Gap Analyzer", "Planning Agent", "RAG Search", "Combined Analysis"]
        )

        if agent_choice == "Query Agent":
            st.subheader("💬 Query Agent")
            question = st.text_input("Ask a question:", placeholder="e.g., How many facilities are in Accra?")
            if question:
                with st.spinner("🤔 Answering..."):
                    result = agents["query"].answer_question(question)
                st.success("✅ Answer Generated")
                st.write(result.get("answer"))
                st.metric("Results Found", result.get("results_count", 0))
                with st.expander("🔍 See SQL Query"):
                    st.code(result.get("sql_query"), language="sql")
                if result.get("results"):
                    with st.expander("📋 See Raw Results"):
                        st.dataframe(pd.DataFrame(result.get("results")), use_container_width=True)

        elif agent_choice == "Gap Analyzer":
            st.subheader("🏜️ Gap Analyzer")
            analysis_type = st.radio(
                "Analysis Type:",
                ["Regional Overview", "Specialty Gap Analysis", "Medical Deserts"]
            )

            if analysis_type == "Regional Overview":
                with st.spinner("🗺️ Analyzing regional coverage..."):
                    regional = agents["gap"].analyze_regional_coverage()
                st.metric("Total Regions", regional["total_regions"])
                df_regional = pd.DataFrame(regional["regional_breakdown"])
                st.dataframe(df_regional, use_container_width=True)
                st.bar_chart(df_regional.set_index("region")["total_facilities"].head(10))

            elif analysis_type == "Specialty Gap Analysis":
                specialty = st.selectbox(
                    "Select Specialty:",
                    ["cardio", "pediatric", "surgery", "oncology", "dental"]
                )
                if st.button("Analyze Gaps"):
                    with st.spinner(f"🔍 Analyzing {specialty} gaps..."):
                        gaps = agents["gap"].analyze_specialty_gaps(specialty)
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Cities WITH Coverage", gaps["cities_with_coverage"])
                    with col2:
                        st.metric("Cities WITHOUT Coverage", gaps["cities_without_coverage"])
                    if gaps["gap_cities"]:
                        st.subheader(f"⚠️ Cities Lacking {specialty.title()} Care")
                        st.write(", ".join(gaps["gap_cities"][:30]))

            elif analysis_type == "Medical Deserts":
                min_facilities = st.slider("Minimum Facilities for Adequate Coverage:", 1, 10, 5)
                with st.spinner("🏜️ Identifying medical deserts..."):
                    deserts = agents["gap"].identify_medical_deserts(min_facilities)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Critical (1 facility)", deserts["summary"]["critical"])
                with col2:
                    st.metric("Severe (2 facilities)", deserts["summary"]["severe"])
                with col3:
                    st.metric("Moderate (3-4)", deserts["summary"]["moderate"])
                if deserts["critical_deserts"]:
                    st.subheader("🚨 Critical Deserts")
                    st.dataframe(pd.DataFrame(deserts["critical_deserts"]), use_container_width=True)

        elif agent_choice == "Planning Agent":
            st.subheader("📋 Planning Agent")
            city = st.selectbox("Select a city:", sorted(df["address_city"].dropna().unique().tolist()))
            if st.button("Generate Plan"):
                with st.spinner("🧭 Building plan..."):
                    plan = agents["planning"].generate_action_plan(city)
                st.markdown("### ✅ Action Plan")
                st.write(agents["planning"].format_plan(plan))
                if plan.get("nearby_partners"):
                    with st.expander("🤝 Nearby Partners"):
                        st.dataframe(pd.DataFrame(plan.get("nearby_partners")), use_container_width=True)

        elif agent_choice == "RAG Search":
            st.subheader("🔍 RAG Semantic Search")
            query = st.text_input("Search for facilities:", placeholder="e.g., maternity care with specialists")
            if query:
                with st.spinner("🔎 Searching..."):
                    result = agents["rag"].augmented_query(query)
                st.write(result.get("answer"))
                if result.get("retrieved_facilities"):
                    with st.expander("📋 Retrieved Facilities"):
                        st.dataframe(pd.DataFrame(result.get("retrieved_facilities")), use_container_width=True)

        elif agent_choice == "Combined Analysis":
            st.subheader("🧩 Combined Analysis")
            city = st.selectbox(
                "Select a city for combined analysis:",
                [""] + sorted(df["address_city"].dropna().unique().tolist())
            )
            if city:
                with st.spinner("🔬 Running combined analysis..."):
                    plan = agents["planning"].generate_action_plan(city)
                    gaps = agents["gap"].identify_medical_deserts()
                st.markdown("### 📋 City Plan")
                st.write(agents["planning"].format_plan(plan))
                st.markdown("### 🏜️ National Desert Summary")
                st.write(
                    f"Critical: {gaps['summary']['critical']} • "
                    f"Severe: {gaps['summary']['severe']} • "
                    f"Moderate: {gaps['summary']['moderate']}"
                )
            else:
                st.info("Select a city to run combined analysis.")

if __name__ == "__main__":
    main()
