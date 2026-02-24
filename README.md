# 🔬 Deep Research Engine

**AI-Powered Deep Research for Engineers** — Ingest PDFs, URLs, and GitHub repos. Get cited engineering reports with a deterministic pipeline. Generate flashcards for study.

![Deep Research Engine](https://img.shields.io/badge/version-0.2-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Python](https://img.shields.io/badge/python-3.11+-yellow) ![Next.js](https://img.shields.io/badge/Next.js-15-black)

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📎 **Ingest Sources** | Upload PDFs, paste URLs, link GitHub repos |
| 📖 **Deep Report** | 5-step pipeline: Plan → Retrieve → Write → Judge → Refine |
| ⚡ **Quick Answer** | Fast direct LLM response for simple questions |
| 🃏 **Flashcards** | Auto-generate Q&A cards + export Anki CSV |
| 🔍 **BM25 Search** | Pure Python keyword search — no GPU, no embeddings |
| 🔄 **LLM Failover** | OpenRouter (free) → Groq automatic fallback |
| 🎯 **Guided Tour** | 11-step onboarding walkthrough for new users |
| 📊 **Quality Judge** | AI verifies every report for citations and accuracy |

## 🏗️ Architecture

```
User → Question + PDFs/URLs → Ingest → BM25 Index
                                       ↓
                    Planner → Retrieve → Writer → Judge → Refine
                                                          ↓
                                          Report + Sources + Flashcards
```

### LLM Strategy: Free-First + Fallback

- **Primary**: OpenRouter (`openrouter/free`) — auto-selects best free model
- **Fallback**: Groq (`llama-3.3-70b-versatile`) — activates on 429/5xx/timeout

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenRouter API key (free at [openrouter.ai/keys](https://openrouter.ai/keys))

### Setup

```bash
# Clone
git clone https://github.com/Gundavenkatasai/deep_research_agent.git
cd deep_research_agent

# Backend
cd backend
pip install -e .
cd ..

# Frontend
cd frontend
npm install
cd ..

# Configure
cp .env.example .env
# Edit .env and add your API keys
```

### Run

```bash
# Backend (terminal 1)
cd backend
uvicorn app.main:app --reload --port 8000

# Frontend (terminal 2)
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## 📁 Project Structure

```
deep_research_agent/
├── backend/
│   └── app/
│       ├── main.py              # FastAPI entry point
│       ├── config.py            # Settings (OpenRouter + Groq)
│       ├── llm_gateway.py       # LLM failover logic
│       ├── database.py          # SQLite models
│       ├── pipeline.py          # Deep report pipeline
│       ├── flashcards.py        # Flashcard generator
│       ├── agents/
│       │   └── router.py        # Brain Router
│       ├── routes/
│       │   ├── chat.py          # /api/answer, /api/report, /api/flashcards
│       │   └── ingest.py        # /api/ingest
│       └── tools/
│           ├── indexer.py       # BM25 search
│           ├── scraper.py       # Web scraper
│           ├── pdf_tool.py      # PDF extractor
│           └── git_tool.py      # GitHub extractor
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx         # Main research UI
│       │   └── about/page.tsx   # About page
│       ├── components/
│       │   ├── chat.tsx         # Research input panel
│       │   ├── report-preview.tsx
│       │   ├── sources-panel.tsx
│       │   ├── flashcards-panel.tsx
│       │   ├── thought-trace.tsx
│       │   └── onboarding-tour.tsx
│       └── lib/
│           └── sse-client.ts    # API client
└── .env                         # API keys
```

## 🔑 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/answer` | POST | Quick LLM answer (SSE) |
| `/api/report` | POST | Deep report pipeline (SSE) |
| `/api/flashcards` | POST | Generate flashcards (SSE) |
| `/api/ingest` | POST | Ingest PDF/URL/GitHub (JSON) |
| `/health` | GET | Health check |

## 📝 Environment Variables

```env
OPENROUTER_API_KEY=sk-or-...     # Required — get free at openrouter.ai
GROQ_API_KEY=gsk_...             # Optional fallback
TAVILY_API_KEY=tvly-...          # Optional web search
```

## 📄 License

MIT
