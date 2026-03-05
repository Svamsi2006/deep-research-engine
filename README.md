# Deep Research Agent

A full-stack AI research engine that ingests PDFs, URLs, and GitHub repos, then produces cited engineering reports using a deterministic pipeline: **Plan → Retrieve → Write → Judge → Refine**.

Built with FastAPI + Next.js 15. Uses free-tier LLM models via OpenRouter with Groq as a fallback.

![Pipeline](https://img.shields.io/badge/pipeline-Plan→Retrieve→Write→Judge→Refine-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ New in V0.4: Modern Chat Interface

**Claude/Gemini-Style UI** — Professional centered chat experience with:
- **Action Bar** — 5 modes (Deep Research, Web Search, Analyze PDF, Paste URL, Flashcards) above input
- **Rounded Input** — Oval-shaped chat box (28px radius) with auto-resize textarea
- **Selection Highlighting** — Active action glows with #4F46E5 accent and shadow effect
- **Plus Icon Toggle** — Expand/collapse actions with smooth rotation animation
- **Smart Keyboard** — Enter sends, Shift+Enter adds newline
- **Dark Theme** — #0D0D0D background, #4F46E5 (Indigo) accent, professional color palette
- **Centered Layout** — Max-width chat messages with action bar and input at bottom
- **Attach Button** — Paperclip icon for file uploads (left side of input)
- **Conditional Send** — Send button enabled only when message is present

📖 [**Implementation Status**](IMPLEMENTATION_STATUS.md) | 📖 [**Roadmap**](next.md)

---

## Features

- **Deep Research Reports** — Multi-step pipeline generates structured, cited reports with real-time SSE progress streaming
- **Source Ingestion** — Upload PDFs, scrape URLs, or clone GitHub repos. Content is chunked, embedded, and stored for retrieval
- **Cited Answers** — Quick Q&A with inline citations drawn from your ingested sources
- **Web Search** — DuckDuckGo (free, no key) + Tavily (optional, higher quality) for live web augmentation
- **Flashcard Generation** — Auto-generate study flashcards from any report (JSON + CSV export)
- **Multi-Provider LLM** — Switch between 7 LLM providers at runtime via the UI settings panel
- **Smart Fallbacks** — Circuit breaker with 60s cooldown on rate limits, automatic provider failover
- **Embeddings** — Local sentence-transformers (free) → Cohere → OpenAI fallback chain
- **Vector Search** — Pinecone integration for persistent semantic search across ingested documents
- **Real-Time UI** — Pipeline stage tracker, loading animations, and thought-trace timeline

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Next.js 15 Frontend                      │
│  Chat UI ←→ SSE Stream ←→ /api/* proxy → FastAPI backend        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                        FastAPI Backend                           │
│                                                                  │
│  Routes:  /api/answer    /api/report    /api/ingest              │
│           /api/flashcards /api/settings  /health                 │
│                                                                  │
│  Pipeline: Plan → Retrieve → Web Search → Write → Judge → Refine│
│                                                                  │
│  LLM Gateway ──→ OpenRouter (primary)                            │
│                  Groq (fallback)                                 │
│                  + 5 more runtime-switchable providers            │
│                                                                  │
│  Tools:  DuckDuckGo / Tavily  │  Trafilatura scraper             │
│          GitPython cloner     │  PyMuPDF PDF parser              │
│          sentence-transformers │  Pinecone vector DB              │
│                                                                  │
│  Storage: SQLite (sources + chunks + reports)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 15, React 19, Tailwind CSS, SSE streaming |
| **Backend** | FastAPI, SSE-Starlette, Pydantic v2 |
| **LLM** | OpenAI-compatible client → OpenRouter / Groq / Ollama / OpenAI / Gemini / DeepSeek / Grok |
| **Search** | DuckDuckGo (LangChain), Tavily API |
| **Scraping** | Trafilatura, BeautifulSoup4, httpx |
| **PDF** | PyMuPDF + pymupdf4llm |
| **Git** | GitPython (shallow clone + key file extraction) |
| **Embeddings** | sentence-transformers → Cohere → OpenAI |
| **Vector DB** | Pinecone (optional) |
| **Database** | SQLite + aiosqlite (async) |
| **Deployment** | Docker Compose, Railway, Vercel |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- An [OpenRouter API key](https://openrouter.ai/keys) (free tier available)

### 1. Clone & configure

```bash
git clone https://github.com/your-username/deep_research_agent.git
cd deep_research_agent
cp .env.example .env
# Edit .env with your API keys (minimum: OPENROUTER_API_KEY)
```

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) — the frontend proxies API calls to the backend automatically.

### Docker (alternative)

```bash
docker-compose up --build
```

This starts the backend on `:8000` and frontend on `:3000`.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENROUTER_API_KEY` | **Yes** | — | Primary LLM provider (free models available) |
| `GROQ_API_KEY` | Recommended | — | Fallback LLM (fast inference) |
| `TAVILY_API_KEY` | Optional | — | Higher-quality web search (DuckDuckGo works without a key) |
| `COHERE_API_KEY` | Optional | — | Embedding fallback (between local & OpenAI) |
| `OPENAI_API_KEY` | Optional | — | Last-resort embeddings + optional LLM provider |
| `PINECONE_API_KEY` | Optional | — | Persistent vector search across documents |
| `GOOGLE_API_KEY` | Optional | — | Gemini LLM provider |
| `DEEPSEEK_API_KEY` | Optional | — | DeepSeek LLM provider |
| `GROK_API_KEY` | Optional | — | Grok LLM provider |
| `AI_PROVIDER` | Optional | `openrouter` | Active LLM provider (configurable via UI) |
| `WEB_SEARCH_PROVIDER` | Optional | `duckduckgo` | `duckduckgo` or `tavily` |
| `DATABASE_URL` | Optional | `sqlite+aiosqlite:///./oracle.db` | Database connection string |

See [.env.example](.env.example) for the full template.

---

## Project Structure

```
deep_research_agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, lifespan, CORS, routes
│   │   ├── config.py            # pydantic-settings (reads .env)
│   │   ├── pipeline.py          # Deep Report pipeline (Plan→Retrieve→Write→Judge→Refine)
│   │   ├── llm_gateway.py       # Unified LLM client, circuit breaker, fallback chain
│   │   ├── database.py          # SQLAlchemy async models (Source, ChunkRow, ReportRow)
│   │   ├── dal.py               # Data access layer
│   │   ├── formatting.py        # Perplexity-style answer formatting with citations
│   │   ├── flashcards.py        # Flashcard generation from reports
│   │   ├── graph/
│   │   │   └── models.py        # Shared DTOs (SearchResult, ScrapedDocument, RepoInfo, etc.)
│   │   ├── routes/
│   │   │   ├── chat.py          # SSE endpoints: /answer, /report, /flashcards
│   │   │   ├── ingest.py        # Source ingestion: /ingest (PDF, URL, GitHub)
│   │   │   └── settings.py      # Runtime settings: /settings (GET, PUT)
│   │   └── tools/
│   │       ├── search.py        # Web search (DuckDuckGo + Tavily)
│   │       ├── scraper.py       # URL content extraction (trafilatura + BS4)
│   │       ├── pdf_tool.py      # PDF parsing (PyMuPDF)
│   │       ├── git_tool.py      # GitHub repo cloning + file extraction
│   │       ├── embedder.py      # Embedding service (ST → Cohere → OpenAI)
│   │       ├── indexer.py       # Text chunking + BM25 indexing
│   │       └── pinecone_client.py # Pinecone vector DB client
│   ├── tests/
│   │   ├── test_search.py       # Search tool tests
│   │   └── test_scraper.py      # Scraper + URL classifier tests
│   ├── pyproject.toml           # Python dependencies
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # Main chat page
│   │   │   ├── about/page.tsx   # About / architecture page
│   │   │   └── api/             # Next.js API route proxies
│   │   ├── components/
│   │   │   ├── chat.tsx              # Main chat interface
│   │   │   ├── modern-sidebar.tsx    # Collapsible sidebar (dark theme)
│   │   │   ├── modern-header.tsx     # Sticky header (dark theme)
│   │   │   ├── modern-input.tsx      # Message input with actions (dark theme)
│   │   │   ├── chat-messages.tsx     # WhatsApp-style message bubbles
│   │   │   ├── canvas-editor.tsx     # Full-screen document viewer
│   │   │   ├── report-preview-card.tsx  # Report preview with gradient
│   │   │   ├── report-preview.tsx    # Report renderer + pipeline animation
│   │   │   ├── sources-panel.tsx     # Source management sidebar
│   │   │   ├── flashcards-panel.tsx  # Flashcard viewer
│   │   │   ├── settings-dialog.tsx   # Runtime settings UI
│   │   │   └── onboarding-tour.tsx   # First-use onboarding
│   │   └── lib/
│   │       ├── sse-client.ts    # SSE stream consumer
│   │       └── utils.ts         # Tailwind merge utilities
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── .gitignore
```

---

## Deep Report Pipeline

The core research pipeline runs 5 deterministic steps, streaming SSE events for each:

```
1. PLAN     → LLM decomposes the question into 3-5 sub-questions
2. RETRIEVE → BM25 search over ingested chunks per sub-question
3. WEB      → DuckDuckGo / Tavily search for additional context
4. WRITE    → LLM synthesizes evidence into a structured report
5. JUDGE    → LLM scores the report (0-10); if < 7, triggers REFINE
6. REFINE   → LLM improves weak sections (max 2 retries)
```

All steps emit real-time SSE events displayed in the pipeline tracker UI.

---

## LLM Providers

The gateway supports 7 providers through an OpenAI-compatible client:

| Provider | Base URL | Free Tier | Notes |
|----------|----------|-----------|-------|
| **OpenRouter** | `openrouter.ai/api/v1` | Yes | Primary — Llama 3.3 70B free |
| **Groq** | `api.groq.com/openai/v1` | Yes | Fast fallback — Llama 3.3 70B |
| **Ollama** | `localhost:11434/v1` | Local | Self-hosted models |
| **OpenAI** | `api.openai.com/v1` | No | GPT-4o-mini and above |
| **Gemini** | `generativelanguage.googleapis.com/v1beta/openai` | Limited | Google AI |
| **DeepSeek** | `api.deepseek.com/v1` | Limited | DeepSeek Chat |
| **Grok** | `api.x.ai/v1` | Limited | xAI Grok |

Switch providers at runtime via the UI settings panel or by updating `.env`.

**Circuit Breaker**: After a 429 rate-limit response, the provider is blocked for 60 seconds to prevent wasted retries.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/answer` | Quick cited answer (SSE stream) |
| `POST` | `/api/report` | Deep research report (SSE stream) |
| `POST` | `/api/flashcards` | Generate flashcards from a report |
| `POST` | `/api/ingest` | Ingest PDF / URL / GitHub repo |
| `GET`  | `/api/settings` | Get current runtime settings |
| `PUT`  | `/api/settings` | Update runtime settings |
| `GET`  | `/health` | Health check |

---

## Deployment

### Railway

The backend includes `railway.toml` and `Procfile` for one-click Railway deployment:

```bash
# Install Railway CLI
railway login
railway up
```

### Vercel (Frontend)

```bash
cd frontend
vercel --prod
```

Set `NEXT_PUBLIC_API_URL` to your Railway backend URL.

### Docker

```bash
docker-compose up --build -d
```

---

## Development

```bash
# Run backend tests
cd backend
pip install -e ".[dev]"
pytest tests/ -v

# Run frontend lint
cd frontend
npm run lint

# Build frontend
npm run build
```

---

## License

MIT
