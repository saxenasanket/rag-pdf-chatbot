# PDF RAG Chatbot - Interview Guide

A comprehensive technical guide to explain the entire system from start to finish, structured for technical interviews.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Complete Architecture](#complete-architecture)
3. [End-to-End User Flow](#end-to-end-user-flow)
4. [PDF Upload Flow](#pdf-upload-flow)
5. [Chat Query Flow](#chat-query-flow)
6. [Key Technical Decisions](#key-technical-decisions)
7. [Deployment on Render](#deployment-on-render)
8. [Common Interview Questions](#common-interview-questions)

---

## System Overview

### What Problem Does It Solve?

**Traditional Chatbots:** Ask ChatGPT a question → it uses its training data (which could be outdated) → might hallucinate

**RAG Chatbot:** Upload your PDFs → ask questions → AI searches YOUR documents → gives grounded answers with citations

**Key Insight:** By retrieving actual document content first, we ensure every answer is based on facts, not guesses.

### Core Capabilities

1. **Upload multiple PDFs** — Files are extracted, chunked, and indexed
2. **Search semantically** — Questions are matched to document content by meaning, not keywords
3. **Get grounded answers** — AI generates answers using only the retrieved content
4. **Get citations** — Every answer shows which document/page it came from

---

## Complete Architecture

### System Components

```
┌─────────────────────────────────────────────────────┐
│  Frontend (Browser)                                  │
│  - Single HTML/CSS/JS page (no build step)          │
│  - Drag-drop file upload                            │
│  - Chat interface with message history              │
│  - Stores chat history in browser (sessionStorage)  │
└──────────────────────┬────────────────────────────┘
                       │ HTTPS API
                       ▼
┌─────────────────────────────────────────────────────┐
│  FastAPI Backend (Python)                            │
│  ┌─────────────────────────────────────────────┐   │
│  │  HTTP Endpoints                              │   │
│  │  - POST /api/documents/ (upload)            │   │
│  │  - GET /api/documents/ (list files)         │   │
│  │  - DELETE /api/documents/{id} (remove)      │   │
│  │  - POST /api/chat/ (ask questions)          │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │  Core Modules                                │   │
│  │  - pdf_ingest: Extract & chunk PDFs         │   │
│  │  - embeddings: Convert text to vectors      │   │
│  │  - vectorstore: Store & search embeddings   │   │
│  │  - rag: Retrieve context & call Claude      │   │
│  │  - registry: Track uploaded documents       │   │
│  └─────────────────────────────────────────────┘   │
└──────────────────────┬───────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    ┌────────┐  ┌──────────┐  ┌──────────────┐
    │Registry│  │ Chroma   │  │ PDF Storage  │
    │ JSON   │  │ Vectors  │  │ (Local Disk) │
    │        │  │ Database │  │              │
    └────────┘  └──────────┘  └──────────────┘
        │            │              │
        └────────────┴──────────────┘
             ▼
        Render Persistent Disk
        (/app/data/)
        - Survives container restarts
        - Shared across all users
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Vanilla HTML/CSS/JavaScript | Lightweight, no build step |
| **Backend** | FastAPI (Python) | Fast async API framework |
| **PDF Processing** | pypdf | Extract text from PDFs |
| **Embeddings** | Voyage AI or sentence-transformers | Convert text to vectors |
| **Vector Store** | Chroma | Fast similarity search |
| **LLM** | Anthropic Claude | Generate grounded answers |
| **Hosting** | Render.com | Cloud deployment |
| **Storage** | Render persistent disk + local Chroma | Data persistence |

---

## End-to-End User Flow

### Complete Journey: Upload → Chat → Get Answer

```
╔════════════════════════════════════════════════════════════════╗
║  USER INTERACTION FLOW                                         ║
╚════════════════════════════════════════════════════════════════╝

t=0: User opens app at https://rag-pdf-chatbot.onrender.com
  ↓
Frontend loads index.html
  ├─ Loads chat history from sessionStorage (browser storage)
  ├─ Fetches list of previously uploaded PDFs from /api/documents/
  └─ Displays both chat and file list

t=5s: User selects 2 PDF files and clicks Upload
  ↓
Frontend creates FormData with both files
  └─ POST to /api/documents/
      ↓
Backend:
  ├─ Validate both files (check .pdf extension + %PDF magic bytes)
  ├─ Generate uuid for each: doc1_uuid, doc2_uuid
  ├─ Save to disk: /app/data/uploads/{uuid}.pdf
  ├─ Create registry entries: status="processing"
  └─ Return 202 Accepted immediately
      ↓
Background Task 1 (doc1): Extract & Embed
  ├─ Read /app/data/uploads/{doc1_uuid}.pdf
  ├─ Extract text page-by-page using pypdf
  ├─ Split into semantic chunks (~1000 chars, 20% overlap)
  ├─ Embed each chunk via Voyage AI API
  ├─ Store vectors + metadata in Chroma
  └─ Update registry: status="ready", pages=45, chunks=200

Background Task 2 (doc2): Extract & Embed (runs in parallel)
  └─ Same process for second PDF

t=10s: Frontend polls GET /api/documents/ every 2 seconds
  ├─ t=10s: status="processing" (both files)
  ├─ t=12s: status="processing" (both files)
  ├─ t=15s: doc1 status="ready" (45 pages, 200 chunks)
  ├─ t=18s: doc2 status="ready" (30 pages, 150 chunks)
  └─ UI updates to show both files ready

t=20s: User types question "What was Q3 revenue?"
  ↓
Frontend:
  ├─ Adds to chatHistory array
  ├─ Saves to sessionStorage (browser storage)
  └─ POST to /api/chat/
      ↓
Backend RAG Engine:
  │
  ├─ Step 1: Embed the question
  │   └─ Call Voyage AI: "What was Q3 revenue?" → vector [0.12, -0.45, ...]
  │
  ├─ Step 2: Search Chroma
  │   └─ Find top-5 chunks most similar to question vector
  │      Results:
  │      - Chunk from doc1, page 12 (similarity: 0.92)
  │      - Chunk from doc1, page 13 (similarity: 0.88)
  │      - Chunk from doc2, page 8 (similarity: 0.75)
  │      - Chunk from doc1, page 11 (similarity: 0.71)
  │      - Chunk from doc2, page 15 (similarity: 0.65)
  │
  ├─ Step 3: Build context
  │   └─ Format as:
  │      "[Source: file1.pdf, Page 12]
  │       Q3 revenue was $4.2M. Expenses were $2.1M.
  │       
  │       [Source: file1.pdf, Page 13]
  │       Net income: $2.1M..."
  │
  ├─ Step 4: Call Claude
  │   ├─ System Prompt: "Answer ONLY from provided context. Cite [filename, p.N]"
  │   ├─ User Message: "Context: [above]\n\nQuestion: What was Q3 revenue?"
  │   └─ History: [] (first turn, no prior messages)
  │
  └─ Step 5: Return response
      ├─ Answer: "Based on the documents, Q3 revenue was $4.2M [file1.pdf, p.12]"
      └─ Sources: [{source: "file1.pdf", page: 12, distance: 0.92}, ...]

Frontend receives response:
  ├─ Adds to chatHistory
  ├─ Saves to sessionStorage
  ├─ Displays answer bubble
  └─ Displays source chips below answer

t=25s: User sees:
  ┌─────────────────────────────────────────┐
  │ User: "What was Q3 revenue?"            │ (blue bubble)
  │                                          │
  │ Assistant: "Based on the documents,     │ (gray bubble)
  │ Q3 revenue was $4.2M [file1.pdf, p.12]" │
  │                                          │
  │ Sources:                                 │
  │ [file1.pdf — p.12] [file1.pdf — p.13]   │
  │ [file2.pdf — p.8]                        │
  └─────────────────────────────────────────┘
```

---

## PDF Upload Flow

### Deep Dive: What Happens When You Upload a PDF

```
USER UPLOADS: quarterly_report.pdf (5MB, 45 pages)
                       │
                       ▼
            ┌──────────────────────┐
            │  HTTP Upload Request  │
            │  - File: binary PDF   │
            │  - Size: 5MB          │
            └──────────────────────┘
                       │
                       ▼
         Frontend (app/static/index.html)
            ├─ Validate: ends with .pdf ✓
            ├─ Create FormData with file
            └─ POST /api/documents/
                       │
                       ▼
         Backend (app/api/documents.py)
            ├─ Receive uploaded file
            ├─ Read binary content
            ├─ Validate: starts with %PDF magic bytes ✓
            │
            ├─ Generate: doc_id = "abc123-def456-..."
            │
            ├─ Save PDF to disk:
            │   /app/data/uploads/abc123-def456-....pdf
            │
            ├─ Create registry entry:
            │   /app/data/documents.json:
            │   {
            │     "abc123-def456-...": {
            │       "filename": "quarterly_report.pdf",
            │       "status": "processing",
            │       "pages": 0,
            │       "chunks": 0,
            │       "created_at": "2026-09-28T10:40:09Z"
            │     }
            │   }
            │
            ├─ Return 202 Accepted
            │   {
            │     "doc_id": "abc123-def456-...",
            │     "filename": "quarterly_report.pdf",
            │     "status": "processing"
            │   }
            │
            └─ Queue background task:
               BackgroundTasks.add_task(process_pdf_ingestion, ...)
                       │
                       ▼
         Background Task (FastAPI BackgroundTasks)
         ┌────────────────────────────────────────┐
         │  process_pdf_ingestion()                │
         │  (runs async in same process)           │
         └────────────────────────────────────────┘
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
    ╔═══════════════╗   ╔═══════════════════╗
    │  Extract Text │   │  Embed Chunks     │
    ╚═══════════════╝   ╚═══════════════════╝
            │                     │
            ▼                     ▼
    ┌──────────────────┐  ┌──────────────────┐
    │  from pypdf      │  │  Call Voyage AI  │
    │  import PdfRead  │  │  (external API)  │
    │                  │  │                  │
    │  reader = Pdf... │  │  for each chunk: │
    │                  │  │  embed_chunk =   │
    │  for page in     │  │   client.embed(  │
    │   reader.pages:  │  │    text,         │
    │    page.extract  │  │    model=        │
    │    _text()       │  │     "voyage-3.5" │
    │                  │  │   )              │
    │  Page 1: "..."   │  │                  │
    │  Page 2: "..."   │  │  Returns:        │
    │  ...             │  │  [0.12, -0.45..] │
    │  Page 45: "..."  │  │  [0.23, 0.56...] │
    │                  │  │  ...             │
    └──────────────────┘  └──────────────────┘
            │                     │
            └──────────┬──────────┘
                       ▼
         ┌─────────────────────────────┐
         │  Chunk Page Text            │
         │  (within each page only)    │
         └─────────────────────────────┘
                       │
    ┌──────────────────┴──────────────────┐
    ▼                                      ▼
 Page 1:                               Page 2:
 Chunk 0: "Header text... [1000 chars]"  Chunk 0: "Sec 2 text... [1000 chars]"
 Chunk 1: "Body text... [1000 chars]"   Chunk 1: "Details... [950 chars]"
 
 (20% overlap within each chunk)
            │
            ▼
    ╔═════════════════════════════════╗
    │  Store in Chroma (Vector DB)    │
    ╚═════════════════════════════════╝
            │
    collection.add(
      ids=[
        "abc123_p1_c0",      # page 1, chunk 0
        "abc123_p1_c1",      # page 1, chunk 1
        "abc123_p2_c0",      # page 2, chunk 0
        ...
      ],
      embeddings=[
        [0.12, -0.45, ...],  # vector for page 1, chunk 0
        [0.23, 0.56, ...],   # vector for page 1, chunk 1
        [0.34, -0.67, ...],  # vector for page 2, chunk 0
        ...
      ],
      documents=[
        "Header text...",
        "Body text...",
        "Sec 2 text...",
        ...
      ],
      metadatas=[
        {
          "doc_id": "abc123...",
          "source": "quarterly_report.pdf",
          "page": 1,
          "chunk_index": 0,
          "char_count": 987
        },
        ...
      ]
    )
            │
            ▼
    Update registry:
    /app/data/documents.json:
    {
      "abc123-def456-...": {
        "filename": "quarterly_report.pdf",
        "status": "ready",
        "pages": 45,
        "chunks": 178,
        "created_at": "2026-09-28T10:40:09Z"
      }
    }
            │
            ▼
    Frontend polls /api/documents/
    Sees status="ready"
    Shows in UI: ✓ quarterly_report.pdf (45 pages, 178 chunks)
```

---

## Chat Query Flow

### Deep Dive: What Happens When You Ask a Question

```
USER TYPES: "What was Q3 revenue?"
                       │
                       ▼
         Frontend JavaScript
    ┌─────────────────────────────┐
    │ chatHistory = [             │
    │   {role:"user", content:"Q3"}│
    │ ]                           │
    │                             │
    │ sessionStorage.setItem(...)  │ ← Save to browser
    │ POST /api/chat/             │
    │   {                          │
    │     message: "What was...",  │
    │     history: []             │
    │   }                          │
    └─────────────────────────────┘
                       │
                       ▼
         Backend: app/api/chat.py
    ┌─────────────────────────────┐
    │ @router.post("/")           │
    │ async def chat(request):    │
    │   rag_engine = get_rag_...()│
    │   answer, sources =         │
    │     rag_engine.chat(        │
    │       message,              │
    │       history=[]            │
    │     )                        │
    │   return {answer, sources}  │
    └─────────────────────────────┘
                       │
                       ▼
    ╔═════════════════════════════════════════╗
    ║  RAG Engine (app/core/rag.py)           ║
    ║  Orchestrates entire retrieval process  ║
    ╚═════════════════════════════════════════╝
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    ╔════════════╗ ╔═════════════╗ ╔═══════════╗
    │  RETRIEVE  │ │ AUGMENT     │ │ GENERATE  │
    ╚════════════╝ ╚═════════════╝ ╚═══════════╝

    STEP 1: RETRIEVE
    ───────────────
    Question: "What was Q3 revenue?"
            │
            ▼
    Call embeddings.embed_query():
    (app/core/embeddings.py)
            │
            ├─ If EMBEDDING_PROVIDER=voyage:
            │  └─ Call Voyage AI API
            │     Request: {text: "What was Q3 revenue?", input_type: "query"}
            │     Response: [0.145, -0.234, 0.567, ..., -0.089]  (1024 dims)
            │
            └─ If EMBEDDING_PROVIDER=local:
               └─ Load sentence-transformers model
                  Prefix: "Represent this sentence for searching..."
                  Model.encode("Represent...Q3 revenue?")
                  Response: [0.234, -0.567, 0.123, ..., 0.456]  (384 dims)
            │
            ▼
    Question Vector: [0.145, -0.234, 0.567, ...]
            │
            ▼
    Query Chroma (app/core/vectorstore.py):
    collection.query(
      query_embeddings=[[0.145, -0.234, ...]],
      n_results=5,  # TOP_K from env
      include=["documents", "metadatas", "distances"]
    )
            │
            ▼
    Chroma does HNSW similarity search:
    For each stored chunk vector:
      similarity = dot_product(query_vec, chunk_vec)
      
    Results (top-5 by similarity):
    ┌─────────────────────────────────────────┐
    │ Chunk 1: similarity=0.92 (BEST MATCH!)   │
    │ - ID: abc123_p12_c2                      │
    │ - Text: "Q3 revenue was $4.2M. Expenses"│
    │ - Page: 12                              │
    │ - Source: quarterly_report.pdf          │
    │                                         │
    │ Chunk 2: similarity=0.88                │
    │ - ID: abc123_p13_c0                     │
    │ - Text: "...were $2.1M. Net income..."  │
    │ - Page: 13                              │
    │ - Source: quarterly_report.pdf          │
    │                                         │
    │ Chunk 3: similarity=0.75                │
    │ - ID: def456_p8_c1                      │
    │ - Text: "Q3 performance summary..."    │
    │ - Page: 8                               │
    │ - Source: another_report.pdf            │
    │                                         │
    │ Chunk 4: similarity=0.71                │
    │ - ID: abc123_p11_c3                     │
    │ - Text: "Revenue breakdown by category" │
    │ - Page: 11                              │
    │ - Source: quarterly_report.pdf          │
    │                                         │
    │ Chunk 5: similarity=0.65                │
    │ - ID: def456_p15_c0                     │
    │ - Text: "Financial summary for period"  │
    │ - Page: 15                              │
    │ - Source: another_report.pdf            │
    └─────────────────────────────────────────┘
            │
            ▼
    Extract metadata for citations:
    sources = [
      {source: "quarterly_report.pdf", page: 12, distance: 0.08},
      {source: "quarterly_report.pdf", page: 13, distance: 0.12},
      {source: "another_report.pdf", page: 8, distance: 0.25},
      ...
    ]

    STEP 2: AUGMENT
    ───────────────
    Build context from retrieved chunks:
            │
            ▼
    context = """
    [Source: quarterly_report.pdf, Page 12]
    Q3 revenue was $4.2M. Expenses were $2.1M.
    
    [Source: quarterly_report.pdf, Page 13]
    ...were $2.1M. Net income: $2.1M.
    
    [Source: another_report.pdf, Page 8]
    Q3 performance summary...
    
    [Source: quarterly_report.pdf, Page 11]
    Revenue breakdown by category...
    
    [Source: another_report.pdf, Page 15]
    Financial summary for period...
    """

    STEP 3: GENERATE
    ────────────────
    Build prompt for Claude:
            │
            ▼
    system_prompt = """
    You are a helpful assistant that answers questions based 
    EXCLUSIVELY on the provided context.
    
    IMPORTANT RULES:
    1. Answer ONLY using information from the context.
    2. If the answer is not in the context, say 'I don't have enough information'.
    3. Always cite your sources using [filename, p.N].
    4. Be concise and accurate.
    """
            │
            ▼
    user_message = """
    Context:
    [Source: quarterly_report.pdf, Page 12]
    Q3 revenue was $4.2M. Expenses were $2.1M.
    
    [Source: quarterly_report.pdf, Page 13]
    ...were $2.1M. Net income: $2.1M.
    ...
    
    Question: What was Q3 revenue?
    """
            │
            ▼
    Call Claude API:
    (app/core/rag.py)
    
    from anthropic import Anthropic
    
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
      model="claude-sonnet-5",
      max_tokens=1024,
      system=system_prompt,
      messages=[
        {role: "user", content: user_message}
      ]
    )
            │
            ▼
    Claude processes:
    1. Reads system prompt: "Answer ONLY from context"
    2. Reads provided context (5 chunks)
    3. Reads question: "What was Q3 revenue?"
    4. Finds answer in first chunk: "$4.2M"
    5. Generates response: "Q3 revenue was $4.2M [quarterly_report.pdf, p.12]"
            │
            ▼
    Response: 
    "Based on the provided documents, Q3 revenue was $4.2M 
    [quarterly_report.pdf, p.12]. Operating expenses totaled 
    $2.1M, resulting in a net income of $2.1M 
    [quarterly_report.pdf, p.13]."
```

---

## Key Technical Decisions

### 1. Why Chunking Within Pages Only?

**Decision:** Never split a chunk across page boundaries.

**Why:**
- Citations are page-accurate: `[file.pdf, p.12]` is always correct
- Avoids the need to track which page a cross-page chunk came from
- Simpler metadata model

**Example:**
```
✅ CORRECT:
  Page 12 → Chunks 0, 1, 2 (all map to p.12)
  Page 13 → Chunks 0, 1 (all map to p.13)

❌ WRONG:
  Chunk spans p.12 to p.13 → Which page do we cite?
```

### 2. Why ~1000 Character Chunks?

**Too small (100 chars):**
- Loses context, bad embeddings
- Millions of vectors, slow search

**Too large (5000+ chars):**
- Loses relevance precision
- Embedding signal diluted
- Includes unrelated content

**Sweet spot (1000 chars = ~150-220 tokens):**
- Topically coherent
- Good embedding signal
- Manageable chunk count
- Small enough to be precise, large enough to be meaningful

### 3. Why Voyage AI for Embeddings?

**Option A: Voyage AI (Chosen)**
- ✅ High quality (tuned for retrieval)
- ✅ `input_type="query"` vs `input_type="document"` — two separate models
- ✅ Anthropic's recommended partner
- ❌ ~$0.02 per 1M tokens (small cost)

**Option B: Local sentence-transformers**
- ✅ Free, fully offline
- ✅ No API calls
- ❌ Lower quality embeddings
- ❌ Slower (CPU) than API
- ❌ Single model (no query/doc distinction)

### 4. Why Chroma (Not Pinecone/Weaviate)?

**Chroma (Chosen)**
- ✅ Embedded locally, no external service
- ✅ Persists to disk automatically
- ✅ Good for single-user or small teams
- ❌ Doesn't scale to massive datasets

**Pinecone (Alternative)**
- ✅ Managed service, scales infinitely
- ❌ External dependency
- ❌ Costs money even at rest
- ❌ Network latency

### 5. Why sessionStorage for Chat (Not Database)?

**sessionStorage (Chosen)**
- ✅ No server needed
- ✅ Instant persistence
- ✅ Private to browser
- ✅ Survives refresh

**Database (Alternative)**
- ❌ Server overhead
- ❌ Every message → DB write
- ✅ Survives browser close
- ✅ Multi-device access

**For this app:** Single-user, local use → sessionStorage is perfect. Server doesn't need to store chat.

### 6. Why BackgroundTasks (Not Celery/Redis)?

**BackgroundTasks (Chosen)**
- ✅ Zero setup, built into FastAPI
- ✅ Good enough for single-process app
- ✅ Runs async in same Python process

**Celery/Redis (Alternative)**
- ✅ True distributed queue
- ✅ Survive process crashes
- ❌ Requires Redis server
- ❌ Overkill for this scale

---

## Deployment on Render

### How Data Persists on Render

```
┌─────────────────────────────────────────────────────┐
│  Render Container (Ephemeral)                       │
│                                                     │
│  /app/                    ← Code (rebuilt on deploy)
│  /usr/local/lib/python/   ← Packages (rebuilt)
│  /tmp/                    ← Temporary files (wiped)
│                                                     │
│  ← Lost on restart ❌                               │
└─────────────────────────────────────────────────────┘
         │
         │ Mounted at /app/data
         ▼
┌─────────────────────────────────────────────────────┐
│  Render Persistent Disk (1 GB)                      │
│                                                     │
│  /app/data/uploads/                                │
│    ├─ {uuid}.pdf    (PDFs you uploaded)            │
│    ├─ {uuid}.pdf                                   │
│    └─ {uuid}.pdf                                   │
│                                                     │
│  /app/data/chroma/                                 │
│    ├─ chroma-collections.db                        │
│    └─ 0_...f_embedding.parquet (all vectors)       │
│                                                     │
│  /app/data/documents.json                          │
│    └─ {doc_id: {filename, status, pages, chunks}}  │
│                                                     │
│  ← Survives restart ✅                              │
└─────────────────────────────────────────────────────┘
```

### Restart Scenarios

**Scenario 1: You push code to GitHub**
1. Render detects push
2. Builds new Docker image
3. Stops old container
4. Starts new container (code updated)
5. **Attaches same persistent disk**
6. App runs with old data ✅

**Scenario 2: Render auto-restarts (crash/daily)**
1. Container crashes
2. Docker stops
3. **Persistent disk detaches**
4. New container starts
5. **Same disk reattaches**
6. All PDFs and embeddings still there ✅

**Scenario 3: No persistent disk**
1. All PDFs lost ❌
2. All embeddings lost ❌
3. Empty registry ❌
4. User sees "No documents uploaded" ❌

---

## Common Interview Questions

### "Walk me through how you'd scale this system to 1000 concurrent users."

**Current bottleneck:** Local Chroma, single container.

**Scaling approach:**

1. **Vector store:** Migrate from Chroma → Pinecone/Weaviate
   - Eliminates local disk bottleneck
   - Serves requests in parallel
   - Cost: ~$1k/month

2. **FastAPI backend:** Run multiple replicas
   - Render auto-scales or add load balancer
   - No local state, so horizontal scaling is safe

3. **File storage:** Migrate uploads → S3/Cloud Storage
   - Render disk is now just a cache
   - Uploads don't consume local disk

4. **Database:** Add PostgreSQL for chat/user history
   - Instead of sessionStorage, persist conversations
   - Track usage, analytics

5. **Rate limiting & auth:**
   - Add API keys per user
   - Rate limit to prevent abuse

### "What if embeddings change between runs?"

**Problem:** Voyage AI releases a new embedding model. Existing vectors are in old space, new queries in new space. No match.

**Solution:**
1. Add version field to Chroma metadata: `{embedding_model: "voyage-3.5", ...}`
2. When model changes, flag old chunks as stale
3. Re-embed in background
4. Gradually replace old vectors

### "How do you handle PDFs that are mostly images?"

**Current:** pypdf skips image-only pages. User uploads 50-page scanned book, gets 0 chunks.

**Improvements:**
1. Add OCR (tesseract or Claude's vision) to text-only pages
2. Show in registry which pages were OCR'd vs. extracted
3. Fallback: "This page appears to be an image. OCR not available."

### "Can I run this completely offline?"

**Current:** Requires Voyage AI API and Anthropic API.

**Offline version:**
1. Switch to local embeddings: `EMBEDDING_PROVIDER=local`
2. Use local LLM: Ollama or llama.cpp instead of Claude API
3. No internet needed, everything runs on laptop
4. Trade-off: Lower quality answers, slower

### "What if a user asks about something not in their documents?"

**System prompt forces Claude to say:**
> "I don't have enough information to answer this question based on the provided documents."

**This prevents hallucination by design.** The system is constrained.

### "How do you prevent someone from asking about sensitive docs uploaded by another user?"

**Current:** Single-user app, not multi-tenant. No isolation needed.

**Multi-tenant version:**
1. Add authentication (OAuth/API keys)
2. Filter Chroma queries by user_id:
   ```python
   collection.query(
     ...,
     where={"user_id": current_user_id}  # Only my docs
   )
   ```
3. Separate schema or separate Chroma collection per user
4. Access control: Can't see other users' files in registry

### "Why not use a traditional SQL database instead of Chroma?"

**Traditional SQL:**
```sql
SELECT documents WHERE content LIKE '%revenue%'
```
❌ Keyword matching only, misses semantic meaning

**Vector DB (Chroma):**
```python
similar = collection.query(embedding([...]), n_results=5)
```
✅ Semantic meaning: "Q3 revenue", "third quarter income", "earnings" all match

**Key insight:** Semantic search > keyword search.

---

## Summary

This RAG chatbot demonstrates three core AI patterns:

1. **Retrieval:** Use vector similarity to find relevant document sections
2. **Augmentation:** Format retrieved context as prompt context
3. **Generation:** Have LLM generate answers based only on that context

**The magic:** By forcing the LLM to use only retrieved documents, we get grounded, cited answers that can be verified. It's the key to trustworthy AI.

**In interviews:** Be ready to discuss:
- Why each piece was chosen (Voyage, Chroma, sessionStorage)
- How you'd handle edge cases (image PDFs, scaling, offline mode)
- Tradeoffs (cost, complexity, accuracy)
- What's out of scope and why (auth, persistent chat, multi-user)
