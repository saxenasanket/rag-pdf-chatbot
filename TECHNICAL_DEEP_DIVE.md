# PDF RAG Chatbot — Complete Technical Deep Dive

A comprehensive guide to understanding how this Retrieval-Augmented Generation (RAG) system works, from PDF ingestion to chat responses.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture & Components](#architecture--components)
3. [Complete Data Flow](#complete-data-flow)
4. [PDF Processing Pipeline](#pdf-processing-pipeline)
5. [Text Extraction & Chunking](#text-extraction--chunking)
6. [Tokenization & Embeddings](#tokenization--embeddings)
7. [Vector Search & Retrieval](#vector-search--retrieval)
8. [RAG Query Pipeline](#rag-query-pipeline)
9. [Background Processes](#background-processes)
10. [Real Example Walkthrough](#real-example-walkthrough)

---

## System Overview

### What This System Does

A PDF RAG Chatbot allows users to:
1. **Upload PDFs** and have them automatically indexed for search
2. **Ask questions** in natural language
3. **Receive grounded answers** sourced directly from the uploaded documents
4. **Get citations** showing which documents/pages the answer came from

### Key Innovation: Grounded AI

Traditional ChatGPT might hallucinate or make up information. This system is **grounded**:
- Every answer is supported by actual document content
- If the answer isn't in the documents, the AI says so
- Sources are always cited with page numbers

### The RAG Paradigm

```
Traditional LLM:
Question → LLM → Answer (might be hallucinated)

RAG System:
Question → Retrieval (search docs) → Augmentation (build context) → Generation (LLM answer)
```

---

## Architecture & Components

### System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                         Frontend (Browser)                    │
│  - Document Upload Panel (drag & drop)                       │
│  - Document List (status, delete)                            │
│  - Chat Interface (messages, sources)                        │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTP REST API
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Python)                    │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  API Routes                                            │  │
│  │  - POST /api/documents (upload)                        │  │
│  │  - GET /api/documents (list)                           │  │
│  │  - DELETE /api/documents/{id} (remove)                 │  │
│  │  - POST /api/chat (send message)                       │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Core Processing Modules                               │  │
│  │  ├─ pdf_ingest.py (extraction + chunking)             │  │
│  │  ├─ embeddings.py (Voyage AI / local models)          │  │
│  │  ├─ vectorstore.py (Chroma vector DB)                 │  │
│  │  ├─ registry.py (document tracking)                   │  │
│  │  └─ rag.py (retrieval + Claude integration)           │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┬──────────────┐
         ▼             ▼             ▼              ▼
    ┌────────┐  ┌────────────┐  ┌───────┐    ┌──────────┐
    │Registry│  │PDF Storage │  │Vector │    │Embedding │
    │(JSON)  │  │(local disk)│  │Store  │    │Provider  │
    │        │  │            │  │(Chroma)    │(Voyage)  │
    └────────┘  └────────────┘  └───────┘    └──────────┘
    data/       data/uploads/   data/chroma/ API Call
    documents.json
```

### Component Responsibilities

| Component | Purpose | Type | Technology |
|-----------|---------|------|-----------|
| **Frontend** | User interaction | Web UI | Vanilla HTML/CSS/JS |
| **API Routes** | HTTP endpoints | Backend | FastAPI |
| **PDF Ingest** | Extract text, chunk | Processing | pypdf |
| **Embeddings** | Text → vectors | ML | Voyage AI / sentence-transformers |
| **Vector Store** | Store & search vectors | Database | Chroma (local) |
| **Registry** | Track documents | Metadata | JSON file |
| **RAG Engine** | Retrieve & generate | Orchestration | Anthropic Claude |

---

## Complete Data Flow

### Upload to Query Flow

```
USER UPLOADS PDF
    │
    ├─→ [API] POST /api/documents receives file
    │
    ├─→ [Validate] Check .pdf extension + %PDF magic bytes
    │
    ├─→ [Save] File → data/uploads/{uuid}.pdf
    │
    ├─→ [Registry] Create entry with status="processing"
    │
    ├─→ [Response] Return 202 (Accepted) to user immediately
    │
    └─→ [Background] BackgroundTasks.add_task(process_pdf_ingestion)

BACKGROUND INGESTION (runs in parallel)
    │
    ├─→ [Extract] PDF → Raw text (pypdf)
    │
    ├─→ [Split] Raw text → Pages (page_num, text)
    │
    ├─→ [Chunk] Each page → Semantic chunks (~1000 chars)
    │
    ├─→ [Embed] Each chunk → Vector (via Voyage/local model)
    │
    ├─→ [Store] Vectors + metadata → Chroma
    │
    └─→ [Registry] Update to status="ready", pages=X, chunks=Y

USER ASKS QUESTION
    │
    ├─→ [API] POST /api/chat receives {message, history}
    │
    ├─→ [Embed] Question → Vector (Voyage/local)
    │
    ├─→ [Search] Query Chroma: find top-5 similar chunks
    │    └─ Uses cosine similarity: dot product of vectors
    │
    ├─→ [Retrieve] Get chunks + metadata + distances
    │
    ├─→ [Build Context] Format chunks as:
    │    "[Source: file.pdf, Page 12]\nChunk text..."
    │
    ├─→ [Prompt] Send to Claude:
    │    System: "Answer only from context..."
    │    User: "Context:\n[chunks]\n\nQuestion: [question]"
    │
    ├─→ [Generate] Claude processes + generates answer
    │
    └─→ [Return] Answer + sources to frontend
```

---

## PDF Processing Pipeline

### Step 1: Text Extraction

**Input:** Binary PDF file (`Sanket_Saxena.pdf`)

**Process:**
```python
from pypdf import PdfReader

reader = PdfReader(pdf_path)
for page_num, page in enumerate(reader.pages, start=1):
    text = page.extract_text()  # Returns plain text from that page
    print(f"Page {page_num}: {text[:100]}...")
```

**Output:** Dictionary of pages with text

```python
{
    "pages": [
        {"page_num": 1, "text": "Sanket Saxena\nStaff Software Engineer\n...", "is_empty": False},
        {"page_num": 2, "text": "EXPERIENCE\nStaff Engineer at Asmi...", "is_empty": False},
        ...
    ]
}
```

**Why pypdf?**
- ✅ Pure Python (no system dependencies like Poppler)
- ✅ Fast and reliable for most PDFs
- ✅ Simple API
- ❌ Doesn't handle complex layouts, tables, or scanned PDFs well

---

### Step 2: Chunking Strategy

**Why chunking?** You can't store the entire PDF as one vector:
- Too large (one embedding per chunk, not per document)
- Loses granularity (similar questions might need only one chunk, not all)
- Impacts embedding quality (embeddings work best on ~100-300 word passages)

#### Chunking Algorithm

**Target:** ~1000 characters per chunk (~150-220 tokens), ~20% overlap

```python
def chunk_text(text, chunk_size=1000, overlap=200):
    """
    Split with semantic awareness: prioritize paragraph breaks > sentences > hard cut
    
    Example:
    --------
    Input text (resume):
        "Sanket Saxena
        TECHNICAL SKILLS
        Languages: Python, JavaScript...
        
        EXPERIENCE
        Staff Engineer at Asmi..."
    
    Output chunks:
        Chunk 0: "Sanket Saxena TECHNICAL SKILLS Languages: Python, JavaScript..."
        Chunk 1: "... Backend & Distributed Systems: FastAPI, Django, Node.js...
                EXPERIENCE Staff Engineer at Asmi..."
        ...
    """
```

**Chunking Priority:**
1. **Paragraph breaks (`\n\n`)** — Best! Preserves section semantics
2. **Sentence boundaries (`. `)** — Good! Natural cutoff
3. **Hard character cut** — Last resort! Might split sentences

**Example Resume Chunking:**

Original resume structure:
```
─────────────────────────────
Header: "Sanket Saxena"
─────────────────────────────
Sec 1: "TECHNICAL SKILLS"
  (Languages, Specialization, etc.)
─────────────────────────────
Sec 2: "RELEVANT EXPERIENCE"
  (Multiple jobs)
─────────────────────────────
Sec 3: "EDUCATION & ACHIEVEMENTS"
─────────────────────────────
```

After chunking (8 chunks):
```
Chunk 0: Header + start of Technical Skills
Chunk 1: Core of Technical Skills (~1000 chars)
Chunk 2: End of Technical Skills + start of Experience
Chunk 3: First job experience
Chunk 4: Second job experience
Chunk 5: Third job experience
Chunk 6: More experience
Chunk 7: Education section
```

**Why This Matters:** When user asks "how good is my python?", the system needs to retrieve **Chunk 1** (Technical Skills). If chunks are poorly aligned, this chunk might be missed.

**What We Fixed:** Lowered the threshold from 0.5 to 0.4 of chunk_size, so paragraph breaks are prioritized more, keeping sections together.

---

### Step 3: Metadata Association

Each chunk gets metadata:

```python
chunk = {
    "id": "abc123_p12_c2",  # Unique ID: doc_id_page_chunk_index
    "text": "Q3 revenue was $4.2M. Expenses were...",
    "metadata": {
        "doc_id": "abc123",
        "source": "quarterly_report.pdf",
        "page": 12,
        "chunk_index": 2,
        "char_count": 847
    }
}
```

**Why metadata?**
- **Source citation:** `[quarterly_report.pdf, p.12]`
- **Deduplication:** Never store same chunk twice
- **Filtering:** Search only within specific documents (future feature)
- **Analytics:** Track which pages are most relevant

---

## Tokenization & Embeddings

### What is Tokenization?

LLMs don't understand text directly. They convert text to **tokens** (atomic units).

**Tokens ≈ words, but not exactly:**

```
Input text: "Q3 revenue was $4.2M"

Tokens:     ["Q", "3", " revenue", " was", " $", "4", ".", "2", "M"]
Token IDs:  [1234, 5678, 9012, 3456, 7890, 2345, 6789, 0123, 4567]

Rule of thumb: 1 token ≈ 4 characters ≈ 0.75 words
```

**Token costs:**
- Voyage AI embeddings: **$0.02 per 1M input tokens**
- Claude generation: **$3 per 1M input tokens, $15 per 1M output tokens**

**Example:** Resume (1 page)
- Characters: ~5000
- Tokens: ~1250
- Embedding cost: ~$0.000025 (negligible!)

---

### What are Embeddings?

Embeddings are **dense vectors** that represent meaning.

**Text → Embedding Process:**

```
Input:  "The revenue was $4.2 million"
         (human-readable string)
         
         ↓ [Embedding Model]
         
Output: [0.234, -0.567, 0.890, ..., -0.123]  (1024 numbers for Voyage)
        └─ Each number encodes semantic meaning
           Numbers are learned, not handwritten
```

**Key Insight:** Similar meaning → similar vectors

```
"Q3 revenue was $4.2M"
    ↓ embed
[0.12, -0.34, 0.56, ..., 0.78]

"How much revenue in Q3?"
    ↓ embed
[0.11, -0.35, 0.57, ..., 0.79]
    
    These vectors are CLOSE (high cosine similarity)
    → System knows these are about the same topic
```

### Embedding Providers

#### Option 1: Voyage AI (Recommended)

**Model:** `voyage-3.5`  
**Dimensions:** 1024 (1024 numbers per vector)  
**Cost:** ~$0.02 per 1M tokens  
**Quality:** Very high (tuned for retrieval)  

```python
from voyageai import Client

client = Client(api_key=VOYAGE_KEY)

# At ingest time: "document" type
embeddings = client.embed(
    ["Q3 revenue was $4.2M"],
    model="voyage-3.5",
    input_type="document"  # ← Optimizes for chunk text
)
# Returns: [[0.234, -0.567, 0.890, ...]]

# At query time: "query" type
embeddings = client.embed(
    ["What was Q3 revenue?"],
    model="voyage-3.5",
    input_type="query"  # ← Optimizes for questions
)
# Returns: [[0.245, -0.570, 0.885, ...]]
```

**Why `input_type` matters:**
- Voyage trains two sub-models internally
- Documents and queries have different patterns
- Specifying type improves retrieval accuracy by ~5-10%

#### Option 2: Local Embeddings (Free)

**Model:** `BAAI/bge-small-en-v1.5`  
**Dimensions:** 384 (smaller, faster)  
**Cost:** Free (runs locally)  
**Quality:** Good (8/10 vs Voyage's 9.5/10)  

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-small-en-v1.5")

# For documents: embed as-is
embeddings = model.encode(["Q3 revenue was $4.2M"])
# Returns: [[0.456, 0.789, ...]] (384 numbers)

# For queries: prepend instruction
query = "Represent this sentence for searching relevant passages: What was Q3 revenue?"
embeddings = model.encode([query])
# Returns: [[0.467, 0.785, ...]]
```

**Tradeoff:**
- Voyage: Better accuracy, tiny cost ($0.0001 per query), requires API key
- Local: Free, offline, slightly lower accuracy, uses CPU

---

## Vector Search & Retrieval

### How Vector Similarity Search Works

**Goal:** Given a question vector, find the most similar chunk vectors.

**Metric: Cosine Similarity**

```
Cosine Similarity = (A · B) / (|A| × |B|)

Where:
  A · B = dot product (sum of element-wise products)
  |A|, |B| = magnitudes (vector lengths)

Range: -1 to +1
  +1 = identical direction (same topic)
  0 = perpendicular (unrelated)
  -1 = opposite direction (contradictory)
```

**Example:**

```
Question vector:     [0.1, -0.2, 0.3, ...]  (1024 dims)

Chunk 1 vector:      [0.09, -0.19, 0.31, ...]
Similarity:          0.987 (Very similar! ✅)

Chunk 2 vector:      [0.5, 0.1, -0.3, ...]
Similarity:          0.234 (Not similar ❌)

Chunk 3 vector:      [0.11, -0.21, 0.29, ...]
Similarity:          0.992 (Most similar! ✅✅)
```

### Chroma Vector Database

Chroma stores vectors and performs fast similarity search using HNSW (Hierarchical Navigable Small World).

```python
from chromadb import PersistentClient

client = PersistentClient(path="data/chroma")
collection = client.get_or_create_collection(
    name="pdf_chunks",
    metadata={"hnsw:space": "cosine"}  # ← Use cosine distance
)

# Add 200 vectors from a PDF
collection.add(
    ids=["doc123_p1_c0", "doc123_p1_c1", ..., "doc123_p45_c3"],
    embeddings=[[0.1, -0.2, ...], [0.3, 0.1, ...], ...],  # 200 vectors
    documents=["Chunk text 1", "Chunk text 2", ...],
    metadatas=[
        {"source": "resume.pdf", "page": 1, "chunk_index": 0},
        {"source": "resume.pdf", "page": 1, "chunk_index": 1},
        ...
    ]
)

# Query for top-5 similar chunks
results = collection.query(
    query_embeddings=[[0.12, -0.19, ...]],  # Question vector
    n_results=5,
    include=["documents", "metadatas", "distances"]
)

# Returns:
results = {
    "ids": [["doc123_p1_c0", "doc123_p1_c1", ...]],
    "documents": [["Chunk text 1", "Chunk text 2", ...]],
    "metadatas": [[{source: "resume.pdf", page: 1}, ...]],
    "distances": [[0.013, 0.089, ...]]  # Lower = more similar
}
```

**Complexity:** O(log n) with HNSW, extremely fast even with millions of vectors.

---

## RAG Query Pipeline

### Complete Query Flow

```
User Question: "How good is my Python?"
        │
        ▼
    [Embed]
    Question → Voyage AI → Vector [0.234, -0.567, ...]
        │
        ▼
    [Retrieve]
    Chroma.query(vector, n_results=5)
    → Top-5 similar chunks returned
        │
        ├─ Chunk: "Languages: Python (Intermediate)" (distance: 0.05)
        ├─ Chunk: "Python expertise in..." (distance: 0.12)
        ├─ Chunk: "System design using..." (distance: 0.34)
        ├─ Chunk: "Frontend: React, Next.js" (distance: 0.67)
        └─ Chunk: "Cloud: GCP, AWS, K8s" (distance: 0.78)
        │
        ▼
    [Build Context]
    Format for Claude:
    
    Context:
    [Source: resume.pdf, Page 1]
    Languages: Python (Intermediate), JavaScript, TypeScript...
    
    [Source: resume.pdf, Page 1]
    Python expertise in distributed systems...
    
    [Source: resume.pdf, Page 2]
    System design using...
        │
        ▼
    [Prompt Claude]
    System Message:
    "You are a helpful assistant. Answer ONLY from the provided context.
     If the answer is not in the context, say 'I don't know'.
     Cite sources as [filename, p.N]."
    
    User Message:
    "Context:
    [Source: resume.pdf, Page 1]
    Languages: Python (Intermediate), JavaScript, TypeScript...
    
    Question: How good is my Python?"
        │
        ▼
    [Generate]
    Claude processes the prompt:
    - Reads system message
    - Reads context chunks
    - Processes question
    - Generates answer grounded in context
        │
        ▼
    [Response]
    "Based on your resume, you have Intermediate Python skills 
     [resume.pdf, p.1]. You've used Python in distributed systems, 
     backend development, and ML infrastructure projects."
        │
        ▼
    Return to Frontend:
    {
      "answer": "...",
      "sources": [
        {"source": "resume.pdf", "page": 1, "distance": 0.05},
        {"source": "resume.pdf", "page": 1, "distance": 0.12},
        ...
      ]
    }
```

### System Prompt (The Magic)

The system prompt is crucial — it instructs Claude to stay grounded:

```
You are a helpful assistant that answers questions based exclusively 
on the provided context.

IMPORTANT RULES:
1. Answer ONLY using information from the provided context.
2. If the answer is not in the context, say "I don't have enough 
   information to answer this question based on the provided documents."
3. Always cite your sources using the format [filename, p.N].
4. Be concise and accurate.
5. If multiple sources support the answer, cite all relevant sources.
```

**Without this prompt:**
- Claude might use its training data
- Answers could be hallucinated (not in documents)
- No citations

**With this prompt:**
- Claude only uses provided context
- Refuses to answer if context is missing
- Always cites sources

---

## Background Processes

### BackgroundTasks for Async Ingestion

When you upload a PDF, we don't want the user to wait 10-30 seconds. Instead:

```python
from fastapi import BackgroundTasks

@app.post("/api/documents")
async def upload_documents(files: List[UploadFile], background_tasks: BackgroundTasks):
    # Immediate response
    for file in files:
        doc_id = uuid.uuid4()
        
        # Save file
        with open(f"data/uploads/{doc_id}.pdf", "wb") as f:
            f.write(await file.read())
        
        # Create registry entry
        registry.create(doc_id, file.filename)
        
        # Queue background task
        background_tasks.add_task(
            process_pdf_ingestion,
            f"data/uploads/{doc_id}.pdf",
            doc_id,
            file.filename
        )
        
        responses.append({
            "doc_id": doc_id,
            "status": "processing"
        })
    
    # Return immediately (user doesn't wait)
    return responses
```

**Timeline:**
```
t=0ms:   User clicks Upload
t=50ms:  File saved, response returned (user sees "processing...")
t=50ms-500ms: FastAPI background task starts (async)
t=500ms-15000ms: Extraction + Embedding happening in background
t=15000ms: Registry updated to "ready"
t=15010ms: Frontend polls, sees "ready", shows chunk count
```

---

## Real Example Walkthrough

### Scenario: Upload Resume & Ask Question

#### Phase 1: Upload (t=0 to t=50ms)

**User action:** Drag `Sanket_Saxena.pdf` onto upload area, click "Upload"

**Frontend code:**
```javascript
const formData = new FormData();
formData.append('files', pdfFile);

const response = await fetch('/api/documents', {
    method: 'POST',
    body: formData
});

const data = await response.json();
// data = [{doc_id: "abc123", status: "processing", filename: "Sanket_Saxena.pdf"}]
```

**Backend code:**
```python
@router.post("/")
async def upload_documents(files: List[UploadFile], background_tasks: BackgroundTasks):
    responses = []
    
    for file in files:  # file = UploadFile(filename="Sanket_Saxena.pdf")
        content = await file.read()  # Read binary PDF
        
        # Validate
        if not content.startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="Invalid PDF")
        
        # Save
        doc_id = str(uuid.uuid4())  # "3f9e2b6c-..."
        pdf_path = Path("data/uploads") / f"{doc_id}.pdf"
        with open(pdf_path, "wb") as f:
            f.write(content)
        
        # Register
        registry = get_registry()
        registry.create(doc_id, "Sanket_Saxena.pdf")
        # documents.json now contains:
        # {"3f9e2b6c-...": {status: "processing", filename: "Sanket_Saxena.pdf"}}
        
        # Queue background job
        background_tasks.add_task(
            process_pdf_ingestion,
            pdf_path,
            doc_id,
            "Sanket_Saxena.pdf"
        )
        
        responses.append(...)
    
    return responses  # User gets response in ~50ms
```

**Frontend now shows:** "Sanket_Saxena.pdf: processing..."

#### Phase 2: Background Ingestion (t=50ms to t=5000ms)

**Extraction:**
```python
def process_pdf_ingestion(pdf_path, doc_id, filename):
    # Extract text
    result = ingest_pdf(pdf_path, doc_id, filename)
    
    # ingest_pdf does:
    # 1. PDF → Pages (pypdf)
    #    Page 1: "Sanket Saxena\nStaff Software Engineer..."
    #    Page 2: "EXPERIENCE\nStaff Engineer at Asmi..."
    #
    # 2. Pages → Chunks (semantic chunking)
    #    Chunk 0: "Sanket Saxena\nStaff Software Engineer..."
    #    Chunk 1: "TECHNICAL SKILLS\nLanguages: Python (Intermediate)..."
    #    Chunk 2: "Agentic AI: Multi-Agent Orchestration..."
    #    ... (8 total chunks)
    #
    # Returns:
    # {
    #   "pages": 1,
    #   "chunks": [
    #     {"id": "3f9e2b6c_p1_c0", "text": "...", "metadata": {...}},
    #     {"id": "3f9e2b6c_p1_c1", "text": "...", "metadata": {...}},
    #     ...
    #   ]
    # }
```

**Embedding:**
```python
    chunk_texts = [chunk["text"] for chunk in chunks]
    # ["Sanket Saxena\nStaff...", "TECHNICAL SKILLS...", ...]
    
    embeddings = embed_documents(chunk_texts)
    # Calls Voyage AI (or local model)
    # Returns 8 vectors, each 1024-dimensional:
    # [[0.123, -0.456, ...], [0.234, 0.567, ...], ...]
```

**Storage:**
```python
    vectorstore.add(
        ids=["3f9e2b6c_p1_c0", "3f9e2b6c_p1_c1", ...],
        embeddings=[[0.123, -0.456, ...], [0.234, 0.567, ...], ...],
        documents=["Sanket Saxena\n...", "TECHNICAL SKILLS...", ...],
        metadatas=[
            {"source": "Sanket_Saxena.pdf", "page": 1, "chunk_index": 0},
            {"source": "Sanket_Saxena.pdf", "page": 1, "chunk_index": 1},
            ...
        ]
    )
    # Stored in Chroma: data/chroma/
```

**Registry Update:**
```python
    registry.update_status(
        doc_id="3f9e2b6c-...",
        status="ready",
        pages=1,
        chunks=8
    )
    # documents.json now shows:
    # {"3f9e2b6c-...": {status: "ready", pages: 1, chunks: 8}}
```

**Frontend polls `/api/documents/` every 2 seconds:**
```
t=1s:    GET → {status: "processing"} (no change)
t=3s:    GET → {status: "processing"} (still embedding)
t=5s:    GET → {status: "ready", pages: 1, chunks: 8} ✅
         Display changes to green "Ready (1 pages, 8 chunks)"
```

#### Phase 3: User Asks Question (t=5000ms to t=8000ms)

**User types:** "how good is my python" and presses Send

**Frontend:**
```javascript
const response = await fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        message: "how good is my python",
        history: []  // First message, no history
    })
});

const data = await response.json();
// data = {
//   answer: "Based on your resume, you have Intermediate Python skills...",
//   sources: [
//     {source: "Sanket_Saxena.pdf", page: 1, distance: 0.05},
//     ...
//   ]
// }
```

**Backend:**
```python
@router.post("/")
async def chat(request: ChatRequest):
    # request.message = "how good is my python"
    # request.history = []
    
    rag_engine = get_rag_engine()
    answer, sources = rag_engine.chat(
        question="how good is my python",
        history=[]
    )
    
    return ChatResponse(answer=answer, sources=sources)
```

**RAG Engine - Retrieve:**
```python
def chat(self, question, history):
    # Step 1: Embed question
    query_embedding = embed_query("how good is my python")
    # Calls Voyage AI or local model
    # Returns: [0.145, -0.234, 0.678, ..., -0.089]  (1024 numbers)
    
    # Step 2: Search Chroma
    results = vectorstore.query(query_embedding, n_results=5)
    
    # Chroma compares question vector to all 8 chunk vectors:
    # Chunk 0 similarity: 0.45 (not very similar)
    # Chunk 1 similarity: 0.92 (VERY SIMILAR!) ✅
    # Chunk 2 similarity: 0.34
    # Chunk 3 similarity: 0.28
    # Chunk 4 similarity: 0.18
    # Chunk 5 similarity: 0.15
    # Chunk 6 similarity: 0.12
    # Chunk 7 similarity: 0.08
    #
    # Returns top-5: [Chunk 1, Chunk 0, Chunk 2, Chunk 3, Chunk 4]
    
    # Returns:
    # {
    #   "ids": [["3f9e2b6c_p1_c1", "3f9e2b6c_p1_c0", ...]],
    #   "documents": [["TECHNICAL SKILLS\nLanguages: Python (Intermediate)...", ...]],
    #   "metadatas": [[{"source": "Sanket_Saxena.pdf", "page": 1}, ...]],
    #   "distances": [[0.08, 0.55, 0.66, 0.72, 0.82]]
    # }
```

**Build Context:**
```python
    context = """
    [Source: Sanket_Saxena.pdf, Page 1]
    TECHNICAL SKILLS
    Languages: JavaScript, TypeScript, Python (Intermediate), C++
    
    [Source: Sanket_Saxena.pdf, Page 1]
    Specialization: AI Systems Engineering, Distributed Systems...
    
    [Source: Sanket_Saxena.pdf, Page 1]
    Agentic AI: Multi-Agent Orchestration, Tool Calling...
    
    [Source: Sanket_Saxena.pdf, Page 1]
    LLM & ML Infrastructure: Provider-Agnostic Model Routing...
    
    [Source: Sanket_Saxena.pdf, Page 1]
    Backend & Distributed Systems: FastAPI, Django, Node.js...
    """
    
    sources = [
        Source(source="Sanket_Saxena.pdf", page=1, distance=0.08),
        Source(source="Sanket_Saxena.pdf", page=1, distance=0.55),
        ...
    ]
```

**Call Claude:**
```python
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        system="""You are a helpful assistant...
                 Answer ONLY from provided context...
                 Cite sources as [filename, p.N]...""",
        messages=[
            {
                "role": "user",
                "content": f"""Context:
                {context}
                
                Question: how good is my python"""
            }
        ]
    )
    
    # Claude's reasoning:
    # - Reads system prompt: "Answer only from context"
    # - Reads context: Sees "Python (Intermediate)"
    # - Generates answer grounded in context
    
    answer = response.content[0].text
    # "Based on your resume, you have Intermediate Python skills 
    #  [Sanket_Saxena.pdf, p.1]. Your expertise includes..."
```

**Return Response:**
```python
    return ChatResponse(
        answer=answer,
        sources=sources
    )
```

**Frontend displays:**
```
User bubble:       "how good is my python"
Assistant bubble:  "Based on your resume, you have Intermediate 
                   Python skills [Sanket_Saxena.pdf, p.1]..."
Sources:           "Sanket_Saxena.pdf — Page 1" (5 chips)
```

---

## Key Insights & Optimizations

### Why This Works Better Than Raw ChatGPT

| Aspect | ChatGPT | RAG System |
|--------|---------|-----------|
| **Hallucination** | Can make up facts | Grounded in documents |
| **Citations** | None | Filename + page number |
| **Knowledge cutoff** | Training data (2024) | Your live documents |
| **Privacy** | Data sent to OpenAI | Stays on your computer |
| **Accuracy** | General knowledge | Domain-specific expert |

### Chunking Matters

**Bad chunking:**
```
Chunk 0: "Sanket Saxena\nStaff Software Engineer\nTECHNICAL SKILLS\nLanguages:"
Chunk 1: "Python (Intermediate) JavaScript, TypeScript, C++\nAgentic AI: Multi-Agent"
Chunk 2: "Orchestration, Tool Calling..."
```
→ When searching for "Python", might miss Chunk 1 because it's fragmented

**Good chunking:**
```
Chunk 0: "Sanket Saxena\nStaff Software Engineer..."
Chunk 1: "TECHNICAL SKILLS\nLanguages: Python (Intermediate) JavaScript, TypeScript..."
Chunk 2: "Agentic AI: Multi-Agent Orchestration, Tool Calling..."
```
→ Chunk 1 is semantically complete, easy to retrieve and cite

### Embedding Quality Matters

**Poor embeddings:**
- Question: "How good is your Python?"
- Embedding: Generic, doesn't capture "proficiency level"
- Search result: Returns resume structure instead of skills section

**Good embeddings (Voyage):**
- Question: "How good is your Python?"
- Embedding: Specifically designed for retrieval, captures "proficiency assessment"
- Search result: Returns "Python (Intermediate)" section

### Cost Analysis

For typical use (100 PDFs, 1000 chat queries):

| Component | Cost |
|-----------|------|
| Voyage embeddings (ingest) | ~$0.01 |
| Voyage embeddings (queries) | ~$0.01 |
| Claude generation | ~$0.10-1.00 |
| **Total** | ~$0.12-1.02 |

**Very cheap!** Negligible if Claude is the bottleneck.

---

## Summary

This RAG system:
1. **Extracts** text from PDFs intelligently
2. **Chunks** semantically to preserve meaning
3. **Embeds** chunks into high-dimensional vectors
4. **Stores** vectors in a local database for fast search
5. **Retrieves** relevant chunks using similarity search
6. **Augments** prompts with retrieved context
7. **Generates** grounded answers via Claude

The magic is in the **Retrieval** step — by finding the most relevant document sections before querying the LLM, we ensure answers are factual, cited, and can be verified by looking at the source documents.

---

## Glossary

- **Token:** Atomic unit of text (~4 chars, ~0.75 words)
- **Embedding:** Dense vector representing semantic meaning (~1024 numbers)
- **Chunk:** Semantic unit of text (~1000 chars, fits into embedding)
- **Vector similarity:** Measure of how related two embeddings are (cosine similarity)
- **Cosine similarity:** Angle-based similarity (-1 to +1, higher = more similar)
- **HNSW:** Hierarchical Navigable Small World — fast vector search algorithm
- **RAG:** Retrieval-Augmented Generation — retrieve docs, then generate with context
- **Grounded:** Answer supported by actual document content, with citations
- **Hallucination:** LLM making up facts not in training data or provided context
