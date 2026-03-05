
# Deep Research Engine Architecture & Flow

The application has been unified so both the frontend UI and the backend AI logic run together seamlessly via a single command. 

## 1. High-Level Process in a Bank (or Enterprise RAG) 🏦
When a user (like an analyst at a bank) asks a complex question ("What are our Q3 risk exposures compared to Basel III requirements?"):
1. **User asks question in UI** & uploads a source document (e.g., PDF report).
2. **Ingestion & Embedding**: The Python backend reads the PDF, chunks the text, and turns it into dense vector embeddings using `sentence-transformers`.
3. **Retrieval**: When the user clicks "Deep Report", the backend uses **Hybrid Search** (BM25 keyword match + vector similarity match with Reciprocal Rank Fusion) to find the exact chunks of the document related to "Basel III risk exposure".
4. **Synthesis**: The LangGraph orchestration pipeline takes the retrieved chunks, passes them to the LLM (OpenRouter/Groq), and generates a tightly cited Markdown report.
5. **Streaming**: The report is streamed back to the Next.js UI using Server-Sent Events (SSE).

---

## 2. Directory & Role Map 🗺️

Here are the folders actually working and how they connect:

### 🟢 Active & Critical Folders

* **`package.json`** (Root)
  * The orchestrator. Contains the `npm run dev` script that uses `concurrently` to boot both Next.js and FastAPI together.
* **`frontend/`** (The UI Shell)
  * **`src/app/page.tsx`**: The main user interface.
  * **`src/components/chat.tsx`**: The chat UI component where users upload PDFs/URLs and see the streaming thoughts and answers.
  * **`src/app/api/chat/route.ts`**: The unified proxy. It catches `/api/chat`, `/api/ingest`, etc., and transparently forwards them to the Python backend on port 8000.
  * **`next.config.js`**: Contains the rewrite rules mapping frontend `/api/` to backend `http://localhost:8000/api/`.
* **`backend/`** (The Brains - FastAPI + LangGraph)
  * **`app/main.py`**: The entrypoint for the FastAPI server.
  * **`app/routes/`**: Defines the endpoints for `/ingest`, `/chat`, `/report` which the frontend talks to.
  * **`app/pipeline.py`**: The LangGraph state machine that coordinates searching, reading, writing, and judging.
  * **`app/tools/`**:
    * `embedder.py`: Handles vectorizing text locally (No Pinecone needed!).
    * `indexer.py`: Handles hybrid search (combining BM25 and our new vectors).
    * `scraper.py`: Extracts text from URLs.
    * `pdf_tool.py`: Extracts text from PDFs.
  * **`app/database.py`**: Uses `sqlite3` to store extracted document text and vector data cleanly.

### 🔴 Deleted / Unused Folders
* **`frontend/src/app/api/answer/`** ❌ (Removed)
* **`frontend/src/app/api/report/`** ❌ (Removed)
* **`frontend/src/app/api/flashcards/`** ❌ (Removed)
* *Why?* Previously, the frontend tried to handle LLM calls on its own and circumvented the backend entirely, leading to timeout errors and lost data. They have been deleted so all logic flows cleanly to the robust Python backend.

---

## 3. How to Run It 🏃

You no longer need two CMD terminals. The system has been optimized to start entirely from **one command**.

1. Open **one** terminal at the root of the project (`c:\Users\vamsi\OneDrive\Desktop\deep_research_agent`).
2. Type:
   ```bash
   npm run dev
   ```
3. **What happens**: The `concurrently` package will split the terminal output. You will see both `[FRONTEND]` (Next.js starting on port 3000) and `[BACKEND]` (Python FastAPI starting on port 8000) logging simultaneously.

*(If you ever wanted to run them manually separately for deep debugging, you still can by typing `npm run frontend` in one CMD and `npm run backend` in another).*

---

## 4. Checklist of Goals Reached from `instructions.md` ✅

* ☑️ **Search / Harvesting:** System successfully parses PDFs (via PyMuPDF) and URLs (via BeautifulSoup/Scraper).
* ☑️ **Storage & Embeddings:** Vectors are generated via `sentence-transformers` and stored in SQLite (no complex external DBs required for local dev).
* ☑️ **Hybrid Retrieval:** Search uses a combination of BM25 and Vector Cosine Similarity (RRF) to retrieve highly accurate context.
* ☑️ **Single Command Startup:** Successfully implemented `npm run dev` to boot both services.
* ☑️ **Bug Fixes:** 
  * Fixed the PDF/URL ingestion completely bypassing the backend.
  * Fixed the `/api/api/` routing bug in the python backend.
  * Fixed the LLM timeouts in the frontend by deleting the rogue frontend LLM routes and forcing data through the python proxy.
* ☑️ **The "Reasoning Loop" (LangGraph Pipeline):** Exists natively in `backend/app/pipeline.py` processing retrieved chunks through the `OpenRouter` models.
