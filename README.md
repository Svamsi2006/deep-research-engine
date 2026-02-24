# Engineering Oracle

Multi-Agent RAG Research & Benchmark Engine powered by LangGraph, OpenRouter free-tier models, and Next.js 15.

## Architecture

```
Query → [Discovery] → [Harvest] → [Clean] → [Reasoning] → [Evaluation] → [Synthesis]
              ↑                                                    |
              └──────────── Supervisor (score < 0.8) ──────────────┘
```

### Nodes

1. **Discovery** — DuckDuckGo search (Tavily fallback if <3 quality results)
2. **Harvest** — Parallel scraping + GitHub repo cloning + PDF download
3. **Clean** — PyMuPDF4LLM for PDFs, chunking for docs, README extraction for repos
4. **Reasoning** — MiMo V2 Flash analyzes FLOPs, latency, code patterns
5. **Evaluation** — ChromaDB cosine similarity scoring; re-routes if <0.8
6. **Synthesis** — Llama 3.3 70B generates structured Markdown report

### Stack

- **Orchestration**: LangGraph (Supervisor + Evaluator pattern)
- **Search**: DuckDuckGo + Tavily API
- **Extraction**: Scrapy-Playwright + GitPython
- **PDF Parsing**: PyMuPDF4LLM
- **LLMs**: OpenRouter free models (Llama 3.3 70B, MiMo V2 Flash, Gemini 2.0 Flash)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2 + ChromaDB
- **Backend**: FastAPI + SSE streaming
- **Frontend**: Next.js 15, Tailwind, Shadcn/UI, Vercel AI SDK

## Quick Start

```bash
# 1. Copy env
cp .env.example .env
# Fill in your OPENROUTER_API_KEY and TAVILY_API_KEY

# 2. Docker (recommended)
docker-compose up --build

# 3. Manual
cd backend && pip install -e . && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## License

MIT
