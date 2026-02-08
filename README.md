# Bridging Medical Deserts

Chat‑first AI + multi‑agent dashboard for healthcare gap analysis in Ghana.

## ✅ Quickstart (Local)

```bash
# 1) Create venv
python -m venv venv
source venv/bin/activate

# 2) Install deps
pip install -r requirements.txt

# 3) Add API key (Claude)
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY=...

# 4) Build data (if database not present)
python tools/database_setup.py

# 5) Build FAISS index (optional but recommended)
python tools/build_faiss_index.py

# 6) Run app
streamlit run app.py
```

Open http://localhost:8501

## 🧭 App Modes

- **AI Chat (default)**: Chat‑first interface with Claude + FAISS + visualizations
- **Multi‑Agent Dashboard**: Query / Gap / Planning / RAG / Combined

## 🔐 Environment Variables

- `ANTHROPIC_API_KEY` – Claude API key
- `OPENAI_API_KEY` – (unused)
- `GOOGLE_API_KEY` / `GEMINI_API_KEY` – for Gemini `QueryAgent` (optional)

## 📁 Project Layout

```
bridging-medical-deserts/
  app.py                   # Chat-first Streamlit app
  app_integrated.py        # Legacy multi-agent app (optional)
  agents/                  # AI agents
  tools/                   # DB, RAG, indexing utilities
  data/                    # Local data (db, embeddings) – not committed
  requirements.txt
```

## 🧪 Testing

```bash
python agents/unified_agent.py
python agents/enhanced_agent.py
```

## 🚫 Notes for GitHub

- `.env` is gitignored.
- Generated data files (db, indexes, embeddings) are ignored.
- Colleagues should run `tools/database_setup.py` to rebuild the DB locally.
