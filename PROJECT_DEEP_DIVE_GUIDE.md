# Deep Research Agent - Complete Project Deep Dive

This document explains the project from two perspectives:
- Technical deep dive (for engineers)
- Plain-language explanation (for non-technical stakeholders)

It also includes:
- End-to-end workflow (step by step)
- Tooling and model choices
- Why these choices were made vs alternatives
- Future optimization roadmap
- Exact locations of system prompts in the codebase
- Project structure map
- Ready-to-use 10-slide PPT content

---

## 1. Project Overview (One Paragraph)

Deep Research Agent is a full-stack research assistant that ingests sources (PDF, URL, GitHub repo), indexes them, retrieves the most relevant evidence using hybrid search (BM25 + vector similarity), and generates either a quick answer or a structured deep report through a deterministic pipeline: Plan -> Retrieve -> (Optional Web Search) -> Write -> Judge -> Refine. Responses are streamed to the UI in real time using SSE.

---

## 2. How It Works (Technical Deep Dive)

### 2.1 Runtime Architecture

- Frontend: Next.js app with React components and a browser-side SSE client.
- Backend: FastAPI service exposing chat/report/ingest/settings endpoints.
- Communication: Frontend sends requests to relative `/api/*` routes; Next.js proxy forwards to backend.
- Streaming: Backend emits Server-Sent Events (`thought`, `report`, `sources`, `done`, etc.); frontend renders progressive updates.

Primary runtime entrypoints:
- Backend app boot: `backend/app/main.py`
- Frontend proxy route: `frontend/src/app/api/chat/route.ts`
- SSE consumer: `frontend/src/lib/sse-client.ts`

### 2.2 Core Backend Flow

1. Ingestion (`/api/ingest`):
- Source types: `pdf`, `url`, `github`
- Extract text via:
  - PDF parser (`backend/app/tools/pdf_tool.py`)
  - URL scraper (`backend/app/tools/scraper.py`)
  - Git repo extractor (`backend/app/tools/git_tool.py`)
- Chunk text with section-aware chunking (`backend/app/tools/indexer.py`)
- Generate embeddings (`backend/app/tools/embedder.py`)
- Persist source + chunks + embeddings in DB; optionally upsert vectors to Pinecone.

2. Quick Answer (`/api/answer`):
- Uses chat route logic in `backend/app/routes/chat.py`
- Builds a system+history+user prompt (with optional source and web context)
- Calls `call_llm(...)` via `backend/app/llm_gateway.py`
- Formats response with citations (`backend/app/formatting.py`)
- Streams result over SSE.

3. Deep Report (`/api/report`):
- Executes pipeline in `backend/app/pipeline.py`
- Deterministic sequence:
  - Planner: decomposes question into sub-questions
  - Retrieval: hybrid search across chunks
  - Optional web search + scraping
  - Writer: drafts engineering report with citations
  - Judge: scores report quality
  - Refine: improves if below threshold
- Streams pipeline thoughts and report chunks.

4. Flashcards (`/api/flashcards`):
- Generates 5-8 cards from report content in `backend/app/flashcards.py`
- Returns JSON cards and TSV/CSV export payload.

### 2.3 Data and State

- Primary DB: SQLite async URL from settings (`database_url`)
- Main persisted entities include sources, chunks, reports, users, conversations, and messages.
- Runtime settings are configurable via `/api/settings` and written back to `.env`.

---

## 3. How It Works (Non-Technical, Clear Explanation)

Think of this project like a research team with specialized roles:

1. Librarian (Ingest)
- You upload files/links.
- The system reads them, organizes them into small pieces, and stores them.

2. Finder (Search)
- When you ask a question, it finds the most relevant pieces.
- It does this two ways:
  - Keyword matching (exact words)
  - Meaning matching (semantic similarity)

3. Writer (Generate)
- It writes an answer/report using only relevant evidence.
- It cites sources so you can verify claims.

4. Reviewer (Quality Check)
- It checks if the report is good enough.
- If weak, it rewrites weak parts automatically.

5. Presenter (Streaming UI)
- You do not wait for a big final output.
- You see progress step by step in real time.

Business value:
- Faster analysis from large mixed sources
- Better trust through cited outputs
- Flexible model/provider selection to manage cost, speed, and reliability

---

## 4. Tools Used and What They Do

### Backend framework
- FastAPI: API routes, async handlers, SSE streaming integration
- Pydantic Settings: environment-driven config management

### LLM and routing
- OpenAI-compatible client (`openai` Python SDK) for multi-provider interoperability
- Providers supported at runtime:
  - OpenRouter
  - Groq
  - Ollama
  - OpenAI
  - Gemini
  - DeepSeek
  - Grok
- Gateway features:
  - Provider fallback chain
  - Circuit breaker on 429 errors
  - Token estimation + input truncation

### Retrieval and indexing
- BM25 keyword search (custom implementation)
- Vector similarity using embeddings
- Reciprocal Rank Fusion (RRF) to combine BM25 + vector rankings

### Ingestion and extraction
- PDF: `pymupdf4llm` with PyMuPDF fallback
- Web scraping: `httpx`, `trafilatura`, `BeautifulSoup`
- GitHub repo extraction: `GitPython`

### Embeddings
- Primary: sentence-transformers `all-MiniLM-L6-v2` (local/free)
- Fallbacks: Cohere -> OpenAI embeddings

### Storage
- SQLite for local structured persistence
- Pinecone optional vector DB for scalable semantic search

### Frontend
- Next.js + React + Tailwind
- SSE client for real-time streaming UX

---

## 5. Models Used (Configured and Default)

Default runtime model settings (from config/presets in code):
- OpenRouter default: `meta-llama/llama-3.3-70b-instruct:free`
- Groq default: `llama-3.3-70b-versatile`
- OpenAI preset: `gpt-4o-mini`
- Gemini preset: `gemini-2.0-flash`
- DeepSeek preset: `deepseek-chat`
- Ollama preset: `llama3.1:8b`
- Grok preset: `grok-2-latest`

Important: model/provider are runtime-configurable via `/api/settings`, so actual model used can change per deployment.

---

## 6. Workflow Process (Step by Step)

### A. Source ingestion workflow

1. User uploads PDF / URL / GitHub link in UI.
2. Frontend calls `/api/ingest`.
3. Backend extracts clean text from source.
4. Text is chunked with overlap.
5. Embeddings are generated (if available).
6. Source + chunks + vectors are stored.
7. Source ID returned to frontend for future retrieval.

### B. Quick answer workflow

1. User asks question and optionally selects sources.
2. Frontend calls `/api/answer` and opens SSE stream.
3. Backend builds prompt context from selected chunks/history.
4. LLM gateway routes call to selected provider/model.
5. Answer is formatted with references.
6. SSE events stream thoughts and final answer back.

### C. Deep report workflow

1. User asks deep question.
2. Frontend calls `/api/report`.
3. Planner creates sub-questions.
4. Retrieval collects top evidence chunks.
5. Optional web search adds fresh external evidence.
6. Writer generates structured report with citations.
7. Judge scores quality.
8. If score is low and depth is deep, Refiner improves report.
9. Final report and source list are streamed and persisted.

### D. Flashcards workflow

1. User clicks flashcards after report generation.
2. Frontend calls `/api/flashcards`.
3. Backend prompts LLM for 5-8 Q/A cards.
4. Cards returned as JSON and CSV-friendly format.

---

## 7. Why This Design vs Other Options

### Why deterministic pipeline instead of one-shot prompting?
- Better traceability (you can see each stage)
- Easier debugging when quality drops
- More controllable quality loop (judge/refine)

### Why hybrid search (BM25 + vector) instead of only one?
- BM25 catches exact keyword hits
- Vector search catches semantic matches
- RRF fusion improves robustness across varied query styles

### Why SSE streaming instead of waiting for full response?
- Better perceived responsiveness
- Users can monitor progress and trust the process
- Supports long-running report generation UX

### Why multi-provider gateway instead of single model provider?
- Improves resilience during rate limits/outages
- Lets users optimize for speed/cost/quality dynamically
- Reduces vendor lock-in

### Why local-first embeddings with cloud fallback?
- Local embeddings reduce cost and external dependency
- Cloud fallback preserves functionality when local model is unavailable

### Why SQLite + optional Pinecone?
- SQLite keeps local dev simple and portable
- Pinecone enables scaling semantic search beyond local constraints

---

## 8. System Prompt Locations (Exact Map)

These are the main system prompts passed to the model:

- Planner prompt constant:
  - `backend/app/pipeline.py:60`
  - Variable: `PLANNER_SYSTEM`

- Writer prompt constant:
  - `backend/app/pipeline.py:132`
  - Variable: `WRITER_SYSTEM`

- Judge prompt constant:
  - `backend/app/pipeline.py:203`
  - Variable: `JUDGE_SYSTEM`

- Refiner prompt constant:
  - `backend/app/pipeline.py:238`
  - Variable: `REFINE_SYSTEM`

- Quick answer prompt constant:
  - `backend/app/routes/chat.py:193`
  - Variable: `ANSWER_SYSTEM`

- Flashcard generation prompt constant:
  - `backend/app/flashcards.py:36`
  - Variable: `FLASHCARD_SYSTEM`

Where prompts are actually injected into messages:
- `backend/app/pipeline.py:74`
- `backend/app/pipeline.py:184`
- `backend/app/pipeline.py:215`
- `backend/app/pipeline.py:252`
- `backend/app/routes/chat.py:264`
- `backend/app/flashcards.py:85`

---

## 9. Project Structure (Practical View)

- `backend/app/main.py`
  - FastAPI app startup, CORS, route registration, health checks
- `backend/app/routes/`
  - `chat.py`: answer/report/flashcards streaming endpoints
  - `ingest.py`: source ingestion and chunk persistence
  - `settings.py`: runtime provider/search settings API
- `backend/app/pipeline.py`
  - Multi-step deep report orchestration
- `backend/app/llm_gateway.py`
  - Provider routing, fallback, circuit breaker, token controls
- `backend/app/tools/`
  - `search.py`, `scraper.py`, `pdf_tool.py`, `git_tool.py`, `indexer.py`, `embedder.py`, `pinecone_client.py`
- `frontend/src/components/`
  - `chat.tsx` and related UX components
- `frontend/src/app/api/chat/route.ts`
  - Proxy to backend API
- `frontend/src/lib/sse-client.ts`
  - Event stream parser and client helpers

---

## 10. Future Optimization Tasks

### Reliability and quality
- Add automatic re-judge after refine (optional configurable second pass)
- Introduce structured citation verification (check each citation maps to known source span)
- Add prompt versioning and A/B evaluation harness

### Retrieval quality
- Add query rewriting before retrieval for hard questions
- Add reranker model for top-k chunk reranking
- Tune chunk size/overlap per source type (PDF vs code repo vs web article)

### Performance and cost
- Cache embeddings/content hashes to skip duplicate work
- Add response caching for repeated questions on same source set
- Adaptive model selection by task complexity and token budget

### Product and UX
- Surface confidence and evidence coverage score in UI
- Add source grounding heatmap (which section supported which claim)
- Add user-level governance controls (PII filters, allowed domains)

### Engineering and operations
- Expand test coverage for SSE contract and failure modes
- Add distributed queue for heavy ingestion/report jobs
- Add observability: request tracing, token/cost metrics, retrieval metrics

---

## 11. Non-Technical Executive Summary (Very Clear)

If you explain this project to a business stakeholder:

- This platform reads uploaded files and links, then answers questions with evidence.
- It is not just a chatbot; it follows a step-by-step research process.
- It can think in stages, check itself, and improve answers before final output.
- It streams progress live, so users can see what it is doing.
- It supports multiple AI providers, reducing risk and controlling cost.
- It is designed so teams can trust outputs more because answers include source grounding.

---

## 12. 10-Slide PPT Content (Ready to Use)

### Slide 1 - Title
- Deep Research Agent
- Evidence-Driven AI Research Platform
- FastAPI + Next.js + Hybrid Retrieval + Multi-Provider LLM

### Slide 2 - Problem Statement
- Teams spend too much time reading fragmented technical sources
- One-shot chatbots often miss context or hallucinate
- Need: fast, explainable, source-grounded research outputs

### Slide 3 - Solution Overview
- Ingest PDFs, URLs, and GitHub repos
- Retrieve relevant evidence using hybrid search
- Generate answers/reports with citations
- Stream real-time progress and results

### Slide 4 - Architecture
- Frontend: Next.js chat experience
- Backend: FastAPI orchestration engine
- LLM Gateway: dynamic provider/model routing + fallback
- Storage: SQLite + optional Pinecone

### Slide 5 - Workflow (Step by Step)
- Ingest -> Chunk -> Embed -> Store
- Plan -> Retrieve -> Web -> Write -> Judge -> Refine
- Stream output + persist artifacts

### Slide 6 - Model and Tooling Stack
- Providers: OpenRouter, Groq, OpenAI, Gemini, DeepSeek, Grok, Ollama
- Tools: Trafilatura, BeautifulSoup, PyMuPDF, GitPython
- Retrieval: BM25 + vector + RRF fusion

### Slide 7 - Why This Design
- Deterministic pipeline improves traceability and quality
- Hybrid retrieval improves relevance and coverage
- Multi-provider strategy improves reliability and cost control
- SSE streaming improves user trust and UX

### Slide 8 - Prompt and Governance Layer
- Dedicated prompts per stage (planner/writer/judge/refiner)
- Prompt locations are version-controllable in backend files
- Enables targeted tuning without changing entire system

### Slide 9 - Current Impact and Value
- Faster technical research cycles
- Higher confidence via evidence-grounded outputs
- Flexible deployment and provider choices
- Better user engagement with live progress feedback

### Slide 10 - Roadmap
- Citation validation and quality scoring
- Retrieval reranking and adaptive model routing
- Deeper observability, tests, and enterprise controls
- Product polish for wider adoption

Optional speaker note for closing:
- "This platform combines practical engineering reliability with AI flexibility, turning complex research from hours into minutes while preserving trust through evidence grounding."

---

## 13. Quick File Reference Index

- Architecture summary: `architecture.md`
- General project docs: `README.md`
- Backend startup: `backend/app/main.py`
- Deep report pipeline: `backend/app/pipeline.py`
- LLM routing/fallback: `backend/app/llm_gateway.py`
- Runtime settings API: `backend/app/routes/settings.py`
- Ingest endpoint: `backend/app/routes/ingest.py`
- Chat/report/flashcards endpoints: `backend/app/routes/chat.py`
- Frontend API proxy: `frontend/src/app/api/chat/route.ts`
- Frontend SSE client: `frontend/src/lib/sse-client.ts`
- Main chat input UI: `frontend/src/components/chat.tsx`

---

Document generated for this codebase state on 2026-03-05.
