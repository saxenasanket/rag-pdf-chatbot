# PDF RAG Chatbot

A local, single-user system to upload PDFs and chat with an AI assistant that answers questions using Retrieval-Augmented Generation (RAG) grounded in your documents.

## Features

- 📄 **Multi-PDF Upload**: Upload multiple PDFs at once with real-time processing status
- 💬 **RAG-Powered Chat**: Ask questions and get answers sourced directly from your documents
- 📍 **Source Citations**: Every answer shows which document and page it came from
- 🚀 **Fast & Local**: No external dependencies beyond API keys; works offline with local embeddings
- 🎨 **Beautiful UI**: Single-page vanilla JavaScript frontend with drag-and-drop upload

## Architecture

```
┌─────────────────────────────────┐
│   Single-Page Frontend (HTML)    │
│  - Documents upload panel        │
│  - Chat interface                │
└────────────────┬────────────────┘
                 │
                 ▼
         ┌──────────────────┐
         │   FastAPI App    │
         │  - /api/documents│
         │  - /api/chat     │
         └────────┬─────────┘
                  │
        ┌─────────┼─────────┬─────────┐
        ▼         ▼         ▼         ▼
    Registry  PDF Ingest Vector DB  Embeddings
    (JSON)    (pypdf)    (Chroma)   (Voyage/Local)
       │         │         │            │
       └─────────┴─────────┴────────────┘
              data/
            (on disk)
```

## Setup

### 1. Prerequisites

- Python 3.10+
- Anthropic API key (from https://console.anthropic.com)
- Voyage API key (optional; for better embeddings; get from https://dash.voyageai.com)

### 2. Clone/Initialize

```bash
cd /Users/sanketsaxena/Documents/rag-pdf
```

### 3. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
VOYAGE_API_KEY=pa-your-actual-key-here
EMBEDDING_PROVIDER=voyage
CLAUDE_MODEL=claude-sonnet-5
CHROMA_DIR=data/chroma
UPLOAD_DIR=data/uploads
TOP_K=5
```

**Environment Variables:**
- `ANTHROPIC_API_KEY` *(required)*: Your Claude API key
- `VOYAGE_API_KEY`: Your Voyage AI embeddings key (required if `EMBEDDING_PROVIDER=voyage`)
- `EMBEDDING_PROVIDER`: `voyage` (recommended, higher quality) or `local` (free, offline)
- `CLAUDE_MODEL`: `claude-opus-5` (best quality, higher cost) or `claude-sonnet-5` (good quality, cheaper)
- `TOP_K`: Number of context chunks to retrieve (default: 5, range: 1-8)

### 6. Run

```bash
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/ in your browser.

## Usage

### Upload PDFs

1. Click "Click to select PDFs or drag & drop" or drag files into the panel
2. Click "Upload"
3. Status shows "processing..." while PDFs are being extracted and embedded
4. When done, shows "ready" with page/chunk counts

### Ask Questions

1. Type a question in the chat input (e.g., "What was Q3 revenue?")
2. Press Enter or click "Send"
3. The chatbot retrieves relevant sections and generates an answer
4. Sources are shown as chips below the answer (e.g., "report.pdf — Page 12")

### Tips

- Ask specific questions for best results (e.g., "Q3 revenue" vs. "tell me about Q3")
- The AI will say "I don't have enough information" if the answer isn't in your documents
- Chat history is saved in your browser (lost when you restart the server)

## Embedding Providers

### Voyage AI (Recommended)

- **Quality**: Highest (tuned for retrieval)
- **Cost**: ~$0.10 per million tokens (very cheap)
- **Setup**: Get key from https://dash.voyageai.com, set `EMBEDDING_PROVIDER=voyage`

### Local Embeddings (Free, Offline)

- **Quality**: Good (slightly lower than Voyage)
- **Cost**: Free, zero API calls
- **Setup**: 
  ```bash
  pip install sentence-transformers torch
  ```
  Set `EMBEDDING_PROVIDER=local` in `.env`
- **Note**: First run downloads a ~140MB model (takes ~30 seconds)

**Important**: Switching embedding providers requires wiping `data/chroma/` and re-uploading PDFs (vectors have different dimensions).

## API Endpoints

### Documents

```bash
# Upload PDFs
curl -F files=@report.pdf -F files=@notes.pdf http://localhost:8000/api/documents

# List documents
curl http://localhost:8000/api/documents

# Delete document
curl -X DELETE http://localhost:8000/api/documents/{doc_id}
```

### Chat

```bash
# Send a message
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What was Q3 revenue?",
    "history": []
  }'
```

## Project Structure

```
rag-pdf/
├── app/
│   ├── main.py                     # FastAPI app setup
│   ├── config.py                   # Environment configuration
│   ├── models/schemas.py           # Pydantic request/response models
│   ├── core/
│   │   ├── embeddings.py           # Text-to-vector conversion (Voyage/local)
│   │   ├── vectorstore.py          # Chroma vector database wrapper
│   │   ├── pdf_ingest.py           # PDF extraction + chunking
│   │   ├── registry.py             # Document metadata tracking (JSON)
│   │   └── rag.py                  # Retrieval + Claude integration
│   ├── api/
│   │   ├── documents.py            # Upload, list, delete routes
│   │   └── chat.py                 # Chat endpoint
│   └── static/
│       └── index.html              # Single-page frontend (HTML+CSS+JS)
├── data/
│   ├── uploads/                    # Uploaded PDF files (gitignored)
│   ├── chroma/                     # Vector database persistence (gitignored)
│   └── documents.json              # Document registry (auto-created, gitignored)
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## How RAG Works

1. **Ingest** 📥
   - PDF → Extract text (pypdf)
   - Text → Split into chunks (~1000 chars each)
   - Chunks → Convert to vectors (Voyage/local embeddings)
   - Vectors → Store in Chroma with metadata (source, page, etc.)

2. **Retrieve** 🔍
   - User question → Convert to vector
   - Chroma → Find top-5 most similar chunks
   - Return chunks + metadata

3. **Generate** 💡
   - Context = retrieved chunks (formatted as: "[Source: file.pdf, Page 12] chunk text")
   - Prompt = system message + context + user question
   - Call Claude → Get grounded answer with citations

## Performance

- **Upload time**: ~1-2 seconds per PDF page (depending on PDF complexity and embedding provider)
- **Chat response time**: ~2-5 seconds (embeddings + retrieval + Claude generation)
- **Vector store**: Handles ~millions of chunks efficiently

## Limitations & Out of Scope

- ❌ Multi-user: No authentication or per-user isolation
- ❌ Streaming: Responses are returned all at once, not token-by-token
- ❌ OCR: Scanned PDFs with only images are skipped (text extraction only)
- ❌ Tables: Complex table extraction not optimized (use pdfplumber if needed)
- ❌ PDF viewer: No in-app PDF reader (use external viewer for deep-linking)
- ❌ Persistent chat: Chat history is lost when server restarts
- ❌ Re-ranking: No semantic re-ranking after initial vector search

## Troubleshooting

### "ModuleNotFoundError: No module named 'voyageai'"

Install the voyageai package:
```bash
pip install voyageai
```

### "ANTHROPIC_API_KEY is required"

Set your API key in `.env`:
```env
ANTHROPIC_API_KEY=sk-ant-...
```

### PDF extraction looks garbled

Try switching to pdfplumber for better layout handling:
1. `pip install pdfplumber`
2. Edit `app/core/pdf_ingest.py`, change `extract_text_from_pdf()` to use `pdfplumber`
   (No other code changes needed — the chunking interface stays the same)

### Embeddings dimension mismatch error

You switched embedding providers. Clear the vector database:
```bash
rm -rf data/chroma/
```
Then re-upload your PDFs.

## Development

### Run with hot-reload

```bash
uvicorn app.main:app --reload --port 8000
```

### Run tests (future)

```bash
pytest tests/
```

### Check code quality (future)

```bash
black app/
flake8 app/
mypy app/
```

## License

MIT

## Support

For issues or questions, check:
1. That API keys are set in `.env` (not in code)
2. That PDFs are valid and readable
3. That you have enough API quota (Anthropic, Voyage)
4. Server logs for detailed error messages
