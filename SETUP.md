# Setup Guide - Bridging Medical Deserts

## 🚀 Quick Start

### Prerequisites
- Python 3.14+ installed
- OpenAI API key with billing enabled

---

## 📋 Setup Steps

### 1. Virtual Environment (DONE ✅)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. OpenAI API Key Setup ⚠️ REQUIRED

**Current Issue**: Your API key has $0 budget allocated

**Fix Steps**:
1. Go to: https://platform.openai.com/settings/organization/billing/overview
2. Click "Add payment method"
3. Add a credit card
4. Set usage limit (recommend $5-$10 for testing)
5. Wait 5-10 minutes for activation

**Your API Key** (already in .env):
```
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
```

### 3. Database Setup (DONE ✅)
```bash
python tools/database_setup.py
```
- ✅ Created DuckDB database
- ✅ Loaded 987 facilities
- ✅ 2168 specialty records

### 4. Geocoding (IN PROGRESS 🔄)
```bash
python scripts/geocode_all.py
```
- Converts city names to coordinates for map display
- Takes ~3-5 minutes (API rate limit: 1 request/second)
- Results cached in `data/geocoding_cache.json`

### 5. Run Streamlit App
```bash
streamlit run app.py
```
- Opens at: http://localhost:8501
- 4 tabs: Overview, Interactive Map, Data Table, Statistics

---

## 🧪 Test AI Agents

Once OpenAI billing is enabled:

### Test Query Agent
```bash
python agents/query_agent.py
```

**Example Questions**:
- "How many facilities are in Accra?"
- "Which hospitals handle cardiac care?"
- "Show me all NGOs in Kumasi"

---

## 📊 Current Status

### ✅ Completed
- [x] Virtual environment setup
- [x] All dependencies installed
- [x] DuckDB database created
- [x] 987 facilities loaded
- [x] Streamlit app running
- [x] Interactive map with Folium
- [x] Database queries working
- [x] Query Agent built (OpenAI)

### 🔄 In Progress
- [ ] Geocoding all facilities (running)
- [ ] OpenAI API billing setup (user action required)

### ⏳ Next Steps
1. Enable OpenAI billing
2. Finish geocoding
3. Test Query Agent
4. Build Gap Analyzer Agent
5. Build Planning Agent
6. Add FAISS vector search

---

## 🗂️ Project Structure

```
bridging-medical-deserts/
├── app.py                    # Streamlit web interface
├── data/
│   ├── ghana_facilities.xlsx # Original data (987 facilities)
│   ├── healthcare.duckdb     # Structured database
│   └── geocoding_cache.json  # Cached coordinates
├── tools/
│   ├── data_loader.py        # Excel data loading
│   ├── database_setup.py     # DuckDB initialization
│   └── geocoding_service.py  # Address → coordinates
├── agents/
│   ├── query_agent.py        # Answer questions with AI
│   ├── gap_analyzer.py       # (TODO) Find medical deserts
│   └── planning_agent.py     # (TODO) Resource planning
├── scripts/
│   └── geocode_all.py        # Batch geocoding
└── requirements.txt          # Python dependencies
```

---

## 🔧 Troubleshooting

### OpenAI API Error: "insufficient_quota"
**Solution**: Add billing to OpenAI account (see step 2 above)

### Streamlit not loading
**Solution**: Check if port 8501 is in use
```bash
lsof -ti:8501  # Check port
kill <PID>     # Kill process if needed
streamlit run app.py
```

### Database not found
**Solution**: Run database setup
```bash
python tools/database_setup.py
```

---

## 📖 Documentation

- **STRATEGY.md**: Full architecture and decision rationale
- **Code comments**: Every function documented
- **This file**: Setup and troubleshooting guide

---

## 🎯 Hackathon Demo Flow

1. **Show Streamlit App** - Interactive map + data exploration
2. **Demo Query Agent** - Natural language queries
3. **Show Medical Deserts** - Gap analysis visualization
4. **Action Plans** - AI-generated resource allocation

**Estimated Build Time**: 4-6 hours total
**Current Progress**: ~60% complete
