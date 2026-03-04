# Deep Research Engine: Complete Architecture & How It Works

*Making AI research transparent, intelligent, and reproducible.*

## Table of Contents

1. [What This App Does](#what-this-app-does)
2. [The Big Picture](#the-big-picture)
3. [The Research Pipeline (Step by Step)](#the-research-pipeline-step-by-step)
4. [Core Components](#core-components)
5. [Technology Stack](#technology-stack)
6. [Models & LLMs Used](#models--llms-used)
7. [Data Flow](#data-flow)
8. [API Endpoints](#api-endpoints)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)

---

## What This App Does

### For Regular Users

Think of this app as **a smart research assistant**. You give it a question, and it:

1. **Remembers** documents you've uploaded (PDFs, web links, GitHub code)
2. **Thinks** about what information is relevant
3. **Searches** both your uploaded documents AND the live web
4. **Writes** a comprehensive research report with citations
5. **Checks** its own work and improves if needed
6. Lets you **export flashcards** for studying

**Example workflow:**
- Upload a company's annual report (PDF)
- Paste their website URL
- Ask: "What are their main revenue streams?"
- Get back a cited report explaining revenue sources with exact quotes from the report

### For Developers

This app is a **deterministic AI research pipeline** built with:
- **Frontend**: Modern React (Next.js 15) with real-time streaming
- **Backend**: FastAPI with async SQLite and vector search
- **LLM**: Multi-provider support (OpenRouter, Groq, OpenAI, etc.) with fallbacks
- **Search**: Dual-mode local (BM25) + web (DuckDuckGo/Tavily)

It demonstrates enterprise-grade patterns:
- SSE (Server-Sent Events) for real-time streaming
- Circuit breaker for rate-limit handling
- Async/await for scalability
- Pydantic validation for data integrity
- Docker & cloud-native deployment

---

## The Big Picture

```
┌──────────────────────────────────────────────────────────────┐
│                       USER'S BROWSER                          │
│  Next.js Frontend (React 19) ← SSE stream ← FastAPI Backend   │
│  - Chat interface        - Pipeline animation                 │
│  - Document management   - Real-time progress                 │
│  - Report viewer         - Citation display                   │
└──────────────────────────┬───────────────────────────────────┘
                           │
                    POST /api/answer, /api/report
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                    FastAPI BACKEND                            │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │            THE RESEARCH PIPELINE                       │  │
│  │                                                        │  │
│  │  1️⃣  PLAN    → Break question into 3-5 sub-questions  │  │
│  │  2️⃣  RETRIEVE → Search your documents + web           │  │
│  │  3️⃣  WRITE   → AI synthesizes findings into report    │  │
│  │  4️⃣  JUDGE   → AI scores quality (0-10)              │  │
│  │  5️⃣  REFINE  → If score < 7, improve weak sections   │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │           SUPPORTING SYSTEMS                           │  │
│  │                                                        │  │
│  │  LLM Gateway    → Multi-provider with fallback chain  │  │
│  │  Search Tools   → Local BM25 + Web (DuckDuckGo/Tavily)│  │
│  │  Document DB    → SQLite with chunking & embedding    │  │
│  │  Vector Search  → Pinecone (optional)                 │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  Storage: SQLite (Source, ChunkRow, ReportRow tables)        │
│  Embeddings: sentence-transformers → Cohere → OpenAI        │
└───────────────────────────────────────────────────────────────┘
```

---

## The Research Pipeline (Step by Step)

### 1️⃣ PLAN Phase

**What happens:** The AI reads your question and breaks it down.

```
User Question: "What's the competitive advantage of Tesla in EVs?"
                          ↓
                   LLM (with instruct)
                          ↓
Generated Sub-questions:
  1. What are Tesla's key technical innovations?
  2. How does Tesla's manufacturing scale compare to competitors?
  3. What's Tesla's battery technology advantage?
  4. How strong is Tesla's brand & customer loyalty?
  5. What's their software/AI advantage?
```

**Why this matters:** Breaking it down helps the AI find more relevant information instead of doing a single broad search.

**Code location:** [backend/app/pipeline.py](backend/app/pipeline.py) - `run_deep_report()` function

---

### 2️⃣ RETRIEVE Phase

**What happens:** For each sub-question, the system searches your uploaded documents.

```
Sub-question: "What's Tesla's battery technology advantage?"
                          ↓
         Search in your documents using BM25
                          ↓
Found matches:
  - Document 1: "Tesla's cells achieve 90% efficiency..."
  - Document 2: "Gigafactory enables 10x production scale..."
  - Document 3: "Maxwell acquisition gave nail-free battery tech..."
```

**How it works:**
1. When you upload a PDF or URL, the app breaks it into **chunks** (250-word snippets)
2. Each chunk is indexed using **BM25** (standard search algorithm)
3. For each sub-question, the top 3-5 chunks are retrieved
4. Retrieved chunks are scored by relevance

**Technology:** BM25 is the same algorithm used in Elasticsearch and modern search engines.

**Code location:** [backend/app/tools/indexer.py](backend/app/tools/indexer.py) - `search_chunks()`

---

### 3️⃣ WEB SEARCH Phase

**What happens:** The system searches the live web for additional context.

```
Retrieved chunks + sub-questions
                    ↓
            Web Search (DuckDuckGo or Tavily)
                    ↓
Results with snippets and URLs:
  - "Tesla's Q4 2024 earnings hit record $33B..."
  - "Competitors announce EV battery breakthroughs..."
  - "Tesla stock soars on FSD improvements..."
```

**Why this matters:** Your uploaded documents might be old. Web search keeps the report fresh and current.

**Tools:**
- **DuckDuckGo**: Free, no API key needed, good for general queries
- **Tavily**: Premium option, uses AI to find more relevant results

**Code location:** [backend/app/tools/search.py](backend/app/tools/search.py)

---

### 4️⃣ WRITE Phase

**What happens:** The AI synthesizes all retrieved information into a structured report.

```
Plan: [5 sub-questions]
Retrieved chunks: [15 relevant passages from your docs]
Web results: [5 web search results]
                          ↓
                    LLM (Llama 3.3 70B)
                          ↓
Output: Markdown report with:
  - Clear sections (one per sub-question)
  - Cited quotes with source attribution
  - Synthesis of contradictions/consensus
  - 2000-3000 word structured analysis
```

**Example output:**
```markdown
## Tesla's Battery Technology Advantage

Tesla's competitive edge stems from three key innovations:

1. **Cell Design**: "Tesla's cells achieve 90% efficiency compared to industry standard 85%..." 
   (Source: Tesla Annual Report 2024, p. 42)

2. **Manufacturing Scale**: "Gigafactory enables 10x production cycle time reduction..."
   (Source: Q4 Earnings, Jan 2024)

3. **Maxwell Acquisition**: The 2020 acquisition of Maxwell Technologies gave Tesla...
   (Source: News, Jan 21, 2024)
```

**Code location:** [backend/app/pipeline.py](backend/app/pipeline.py) - `write_report()` phase

---

### 5️⃣ JUDGE Phase

**What happens:** The AI scores the report (0-10) on quality, completeness, and accuracy.

```
Generated report
        ↓
LLM Evaluation:
  ✓ Contains citations from sources? Yes (8/10)
  ✓ Covers all sub-questions? Yes (9/10)
  ✓ Logical flow & synthesis? Yes (7/10)
  ✓ Acknowledges uncertainties? No (5/10)
        ↓
       Score: 7.3 / 10
```

**Why this matters:** If the score is < 7.0, the system automatically refines weak sections instead of returning a mediocre report.

**Code location:** [backend/app/pipeline.py](backend/app/pipeline.py) - `judge_report()` phase

---

### 6️⃣ REFINE Phase (if needed)

**What happens:** If the score is low, the AI improves specific weak sections.

```
Report with low scores:
  - Missed coverage on "financial metrics"
  - Lacks quantitative data
        ↓
LLM (targeted):
  "Improve the Financial Performance section
   with specific metrics and growth rates..."
        ↓
Updated report with better section
        ↓
Re-evaluate → Score improves to 8.2 / 10
```

**Limits:** Max 2 refinement attempts to prevent infinite loops.

**Code location:** [backend/app/pipeline.py](backend/app/pipeline.py) - `refine_report()` phase

---

## Core Components

### Frontend (Next.js React)

**Main purpose:** User interface for research and result visualization

**Key files:**
- **[page.tsx](frontend/src/app/page.tsx)** — Main chat interface with intro hero screen
  - Input panel (ask questions, request reports/flashcards)
  - Pipeline tracker (shows progress through 5 phases)
  - Tabbed output (Report, Sources, Flashcards)
  - Settings & theme toggle

- **[components/chat.tsx](frontend/src/components/chat.tsx)** — Input form
  - Question input
  - Source selection (which uploaded docs to search)
  - Report type: Quick Answer vs. Deep Report
  - Web search toggle

- **[components/report-preview.tsx](frontend/src/components/report-preview.tsx)** — Report display
  - Markdown rendering with syntax highlighting
  - Real-time streaming (text appears as it's generated)
  - Pipeline tracker animation
  - Citation tooltips on hover

- **[components/sources-panel.tsx](frontend/src/components/sources-panel.tsx)** — Document management
  - Upload PDF, paste URL, clone GitHub
  - List all ingested sources
  - View relevant chunks per source
  - Delete sources

- **[components/flashcards-panel.tsx](frontend/src/components/flashcards-panel.tsx)** — Study tools
  - Flip animation to reveal answers
  - CSV/JSON export for external tools
  - Auto-generated from reports

- **[lib/sse-client.ts](frontend/src/lib/sse-client.ts)** — Real-time streaming
  - Connects to backend SSE stream
  - Parses thought, report, done, sources, flashcards events
  - Handles errors and reconnection

### Backend (FastAPI Python)

**Main purpose:** AI logic, document management, data persistence

**Key files:**
- **[main.py](backend/app/main.py)** — FastAPI app setup
  - CORS configuration
  - Lifespan (startup/shutdown hooks)
  - Health check endpoint
  - Route registration

- **[pipeline.py](backend/app/pipeline.py)** — The research pipeline
  - `run_deep_report()` — Orchestrates all 5 phases
  - `plan_phase()` — Generate sub-questions
  - `retrieve_phase()` — Search documents
  - `web_search_phase()` — Search the web
  - `write_phase()` — Compose the report
  - `judge_phase()` — Score quality
  - `refine_phase()` — Improve if needed

- **[routes/chat.py](backend/app/routes/chat.py)** — SSE endpoints
  - POST `/api/answer` — Quick Q&A
  - POST `/api/report` — Deep research report
  - POST `/api/flashcards` — Generate study cards
  - Real-time SSE streaming for all

- **[routes/ingest.py](backend/app/routes/ingest.py)** — Document ingestion
  - POST `/api/ingest` — Upload PDF, URL, or GitHub repo
  - Chunking & embedding
  - Storage in SQLite + vector DB (optional)

- **[llm_gateway.py](backend/app/llm_gateway.py)** — Multi-provider LLM
  - OpenRouter (primary)
  - Groq (fallback)
  - OpenAI, Gemini, DeepSeek, Grok (optional)
  - Circuit breaker (cooldown on rate limits)
  - Auto-failover on errors

- **[database.py](backend/app/database.py)** — SQLAlchemy models
  - `Source` — Ingested documents (PDF, URL, GitHub)
  - `ChunkRow` — Text chunks with embeddings
  - `ReportRow` — Generated reports with scores

- **[dal.py](backend/app/dal.py)** — Data access layer
  - CRUD operations for sources & chunks
  - Search queries
  - Report storage

- **[tools/search.py](backend/app/tools/search.py)** — Web & local search
  - DuckDuckGo integration
  - Tavily integration
  - Result aggregation

- **[tools/scraper.py](backend/app/tools/scraper.py)** — URL content extraction
  - Trafilatura for clean HTML parsing
  - BeautifulSoup4 fallback
  - Handles articles, blogs, docs

- **[tools/pdf_tool.py](backend/app/tools/pdf_tool.py)** — PDF parsing
  - PyMuPDF (fitz) for extraction
  - Page-aware chunking
  - Preserves formatting

- **[tools/git_tool.py](backend/app/tools/git_tool.py)** — GitHub integration
  - Shallow clone (fast)
  - Extracts .md, .py, key documentation files
  - Ignores node_modules, build artifacts

- **[tools/embedder.py](backend/app/tools/embedder.py)** — Embedding service
  - sentence-transformers (local, free)
  - Falls back to Cohere
  - Falls back to OpenAI
  - Enables semantic search

- **[flashcards.py](backend/app/flashcards.py)** — Flashcard generation
  - Extracts key Q&A pairs from reports
  - Robust JSON parsing (handles LLM variations)
  - Validates quality (both front & back non-empty)

---

## Technology Stack

| Layer | Technology | Why This Choice |
|-------|-----------|-----------------|
| **Frontend Framework** | Next.js 15 (React 19) | SSR, built-in API routes, fast builds, great DX |
| **Frontend Styling** | Tailwind CSS + Lucide icons | Utility-first, dark mode out-of-box, complete icon library |
| **Backend Framework** | FastAPI | Async/await, concurrent requests, auto API docs, Pydantic validation |
| **Backend Async** | asyncio + aiosqlite | Non-blocking I/O, better resource usage, handles concurrent requests |
| **Database** | SQLite + SQLAlchemy ORM | No setup required, portable, async support via aiosqlite, NullPool for concurrency |
| **Real-time Communication** | SSE (Server-Sent Events) | Simpler than WebSockets, unidirectional (perfect for streaming), no connection overhead |
| **LLM Client** | OpenAI Python library | Compatible with OpenRouter, Groq, Ollama, etc. via base_url override |
| **Search (Local)** | BM25 (via Whoosh) | Fast full-text indexing, no external dependencies, ranked retrieval |
| **Search (Web)** | DuckDuckGo API + Tavily | Free tier, good coverage, no IP blocking issues |
| **Web Scraping** | Trafilatura + BeautifulSoup4 | Trafilatura for clean extraction, BS4 fallback, handles JavaScript rendering limitations gracefully |
| **PDF Parsing** | PyMuPDF (fitz) + pymupdf4llm | High accuracy, maintains structure, supports all PDF types |
| **Git Integration** | GitPython | Pure Python, simple shallow clone, fast |
| **Text Embedding** | sentence-transformers | Free, fast, good quality (~384D vectors), offline capable |
| **Vector DB (Optional)** | Pinecone | Managed service, low ops, free tier available |
| **Deployment (Backend)** | Docker + Railway/Render | Container isolation, cloud-ready, free tier available |
| **Deployment (Frontend)** | Vercel | Next.js native, auto-scaling, free tier, built-in analytics |

---

## Models & LLMs Used

### Primary Model: Meta Llama 3.3 70B Instruct

**Provider:** OpenRouter (via API)  
**Cost:** FREE tier available  
**Why this model:**
- Instruction-tuned (good for structured tasks like planning, writing reports)
- 70B parameters (large enough for complex reasoning)
- Performs well on citation & evidence-based tasks
- GGUF quantized version available for local Ollama

**Use cases in pipeline:**
- Plan phase (breaking down questions)
- Write phase (composing reports)
- Judge phase (scoring quality)
- Refine phase (improving weak sections)

### Fallback Model: Llama 3.3 70B Versatile

**Provider:** Groq  
**Cost:** FREE tier (rate-limited)  
**Why this model:**
- Same 70B size (consistency)
- Groq's TPU inference = very fast
- Acts as backup if OpenRouter quota exhausted
- Different rate limits = coverage

---

### Embedding Model: sentence-transformers

**Model:** `all-MiniLM-L6-v2` (384 dimensions)  
**Cost:** FREE (runs locally)  
**Why this model:**
- Fast inference on CPU
- Good semantic understanding
- Small (~22 MB)
- No API calls needed

**Fallback chain:**
1. **Local sentence-transformers** → `all-MiniLM-L6-v2` (0 cost)
2. **Cohere** → `embed-english-v3.0` (if API key provided)
3. **OpenAI** → `text-embedding-3-small` (if other options fail)

---

### Other Supported LLM Providers

You can switch at runtime via UI settings or .env:

| Provider | Model | Free? | Quality | Speed |
|----------|-------|-------|---------|-------|
| **OpenRouter** | Llama 3.3 70B | ✅ Yes | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Groq** | Llama 3.3 70B | ✅ Limited | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Ollama** | Local models | ✅ Yes (self-hosted) | ⭐⭐⭐⭐ | Varies |
| **OpenAI** | GPT-4o-mini | ❌ Paid | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Google Gemini** | Gemini Pro | ⚠️ Limited free | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **DeepSeek** | Chat | ⚠️ Limited free | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Grok (xAI)** | Grok-2 | ❌ Paid | ⭐⭐⭐⭐ | ⭐⭐ |

---

## Data Flow

### Uploading a Document

```
User uploads PDF (example: "Tesla Annual Report 2024.pdf")
                    ↓
        [Frontend] → POST /api/ingest
                    ↓
        [Backend] Receives file
                    ↓
            Extract text using PyMuPDF
            ↓
    Split into ~250-word chunks
            ↓
    For each chunk:
      1. Embed using sentence-transformers
      2. Index in BM25 search
      3. Store in SQLite (ChunkRow table)
            ↓
Response: {
  "source_id": "uuid-123",
  "title": "Tesla Annual Report 2024",
  "chunk_count": 47,
  "tokens": 12345
}
```

### Asking a Question

```
User asks: "What's Tesla's competitive advantage?"
                    ↓
        [Frontend] → POST /api/report
                    ↓
        [Backend] Starts SSE stream
                    ↓
    1. PLAN: Generate sub-questions
       → SSE: {"type": "thought", "message": "Analyzing question..."}
                    ↓
    2. RETRIEVE: Search for relevant chunks
       → Query BM25 index for each sub-question
       → Get top 3-5 results per sub-question
       → SSE: {"type": "thought", "message": "Found 15 relevant chunks"}
                    ↓
    3. WEB SEARCH: Search DuckDuckGo
       → Query: "Tesla competitive advantage EVs 2024"
       → Get 5 web results with snippets
       → SSE: {"type": "thought", "message": "Web search complete"}
                    ↓
    4. WRITE: Compose report
       → Send to LLM: chunks + web results + plan
       → LLM generates markdown report
       → SSE: {"type": "report_chunk", "content": "## Overview\nTesla's..."}
       → SSE: {"type": "sources", "sources": [...]} (list of cited docs)
                    ↓
    5. JUDGE: Score quality
       → LLM evaluates report
       → SSE: {"type": "thought", "message": "Quality score: 8.2/10"}
                    ↓
    6. REFINE: Improve if needed
       → If score < 7, run refinement
       → Otherwise, done
                    ↓
       → SSE: {"type": "done", "report_id": "uuid-456"}
                    ↓
    [Frontend] Receives all SSE events in order
    → Displays pipeline animation
    → Shows streaming report text
    → Lists sources with citations
```

### Generating Flashcards

```
User clicks "Generate Flashcards" on a report
                    ↓
        [Frontend] → POST /api/flashcards
                    ↓
    [Backend] Receives report content
                    ↓
        LLM prompt: "Extract 10 key Q&A pairs from this report"
                    ↓
    LLM returns JSON array:
    [
      {"front": "What is Tesla's main competitive advantage?", 
       "back": "Tesla's competitive advantage stems from..."},
      {"front": "In what year did Tesla acquire Maxwell?", 
       "back": "2020"}
    ]
                    ↓
    Backend validates & filters:
      - Both front & back non-empty? Keep it
      - Any < 5 chars? Skip (too short)
                    ↓
    SSE: {"type": "flashcards", "cards": [...], "csv": "..."}
                    ↓
    [Frontend] Displays flashcards with flip animation
              Allows CSV export for Quizlet, Anki, etc.
```

---

## API Endpoints

### POST `/api/answer`

Quick Q&A from your documents + web.

**Request:**
```json
{
  "question": "What's Tesla's revenue?",
  "source_ids": ["uuid-1", "uuid-2"],
  "allow_web_search": true
}
```

**Response (SSE stream):**
```
event: thought
data: {"message": "Searching documents..."}

event: report_chunk
data: {"content": "Tesla's revenue for 2024...", "done": false}

event: sources
data: {"sources": [{"source_id": "uuid-1", "title": "Annual Report", "url": "..."}]}

event: done
data: {"report_id": "uuid-abc", "evaluation_score": 0.85, "quality_warning": false}
```

---

### POST `/api/report`

Deep research report (full 5-step pipeline).

**Request:**
```json
{
  "question": "What's Tesla's competitive advantage in EVs?",
  "source_ids": ["uuid-1"],
  "depth": "deep",
  "allow_web_search": true
}
```

**Response (SSE stream):**
Similar to `/api/answer`, but longer and more detailed.

---

### POST `/api/flashcards`

Generate study flashcards from a report.

**Request:**
```json
{
  "report_id": "uuid-abc",
  "report_content": "## Tesla Report\n...",
  "question": "What's Tesla's competitive advantage in EVs?"
}
```

**Response (SSE stream):**
```
event: flashcards
data: {
  "cards": [
    {"front": "What is Tesla's main competitive advantage?", "back": "..."},
    ...
  ],
  "csv": "Front,Back\nWhat is...,..."
}
```

---

### POST `/api/ingest`

Upload documents.

**Request:**
```json
{
  "source_type": "pdf",  // pdf, url, github
  "file": <binary>,      // for pdf
  "url": "https://...",  // for url
  "repo_url": "https://github.com/..." // for github
}
```

**Response:**
```json
{
  "source_id": "uuid-123",
  "title": "Document Title",
  "source_type": "pdf",
  "chunk_count": 45,
  "tokens": 12345
}
```

---

### GET `/api/settings`

Get current settings (which LLM, search provider, etc.).

**Response:**
```json
{
  "llm_provider": "openrouter",
  "llm_model": "meta-llama/llama-3.3-70b-instruct:free",
  "web_search_provider": "duckduckgo",
  "available_providers": ["openrouter", "groq", "openai", "gemini", ...]
}
```

---

### PUT `/api/settings`

Update runtime settings.

**Request:**
```json
{
  "llm_provider": "groq",
  "llm_model": "llama-3.3-70b-versatile",
  "web_search_provider": "tavily"
}
```

---

### GET `/health`

Health check (used by deployment cron jobs).

**Response:**
```json
{
  "status": "healthy",
  "version": "0.2.0",
  "openrouter": true,
  "groq": true
}
```

---

## Deployment

### Quick Start (Local)

```bash
# 1. Clone
git clone https://github.com/Svamsi2006/deep-research-engine.git
cd deep_research_agent

# 2. Setup backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
cp ../.env.example ../.env
# Edit .env with OPENROUTER_API_KEY

# 3. Setup frontend
cd ../frontend
npm install

# 4. Run (separate terminals)
# Terminal 1 (backend):
cd backend && uvicorn app.main:app --reload

# Terminal 2 (frontend):
cd frontend && npm run dev

# Open http://localhost:3000
```

### Docker

```bash
docker-compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

### Render.com (Backend) + Vercel (Frontend)

**See:** [README.md](README.md#deployment) for steps.

Key steps:
1. Push to GitHub
2. Connect Render to GitHub → auto-deploy backend
3. Connect Vercel to GitHub → auto-deploy frontend
4. Set env vars in dashboards
5. Set `BACKEND_URL` in Vercel to your Render URL

---

## Troubleshooting

### "No sources appearing in Sources tab"

**Cause:** Sources retrieved but URLs not properly mapped.  
**Fix:** 
1. Check backend logs: `docker logs <backend-container>`
2. Verify ingestion succeeded: Check if source appears in Sources panel
3. Try refresh: Close/reopen browser

**Code location:** [backend/app/dal.py](backend/app/dal.py) - `get_source_titles_and_chunks()`

---

### "Flashcards not generating"

**Cause:** LLM returned malformed JSON.  
**Fix:**
1. Check LLM provider status (Settings → switch to Groq backup)
2. Verify report content is detailed enough (flashcards need material)
3. Check backend logs for JSON parsing errors

**Code location:** [backend/app/flashcards.py](backend/app/flashcards.py) - `_extract_json_array()`

---

### "Report quality score very low (< 5/10)"

**Cause:** Retrieved chunks don't contain enough relevant information.  
**Fix:**
1. Upload more documents related to the question
2. Enable web search (toggle "Search the web")
3. Ask a more specific question

---

### "429 Too Many Requests" errors

**Cause:** Hit LLM provider rate limit.  
**Fix:**
1. Your request triggered fallback chain (circuit breaker active)
2. Wait 60 seconds (cooldown period)
3. Add API key for alternative provider (Settings)
4. Use Groq (higher rate limits than OpenRouter free tier)

**Code location:** [backend/app/llm_gateway.py](backend/app/llm_gateway.py) - `CircuitBreaker` class

---

### "Backend not connecting from frontend"

**Cause:** API proxy misconfiguration.  
**Fix:**
1. Check `BACKEND_URL` env var in frontend
2. Verify backend is running (`curl http://localhost:8000/health`)
3. Check browser console for CORS errors
4. Ensure `.env` has correct URLs

**Code location:** [frontend/next.config.js](frontend/next.config.js) - rewrites section

---

## Architecture Highlights

### Why This Design?

1. **Deterministic Pipeline** → Reproducible results, easy debugging
2. **Multi-Step Approach** → Better reasoning (Plan → Retrieve → Write → Judge)
3. **Real-time Streaming** → User sees progress, not blank loading screen
4. **Multi-Provider LLM** → No vendor lock-in, built-in fallbacks
5. **Local-First Search** → Fast retrieval from your own docs
6. **Async Backend** → Handles concurrent requests efficiently
7. **Modular Code** → Easy to add new tools, providers, or search methods

### What Makes It Different?

Unlike typical RAG systems that just do: **Query → Search → Answer**

This system adds:
- **Planning** (decompose the question)
- **Web Augmentation** (combine local + web)
- **Quality Judgment** (self-score and refine)
- **Real-time UX** (see progress, not just final answer)

This leads to **more accurate, well-sourced, current reports** that you can actually trust.

---

## Next Steps

- **Try uploading a PDF** and asking questions
- **Check the `/about` page** for UI walkthrough
- **Read the [README.md](README.md)** for developer setup
- **Explore `backend/app/` source** to understand each component
- **File issues or suggestions** on GitHub

---

**Built with ❤️ using FastAPI, Next.js, and free-tier LLMs**
