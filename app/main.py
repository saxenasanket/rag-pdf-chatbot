from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import os

from app.api import documents, chat
from app.config import settings

app = FastAPI(
    title="PDF RAG Chatbot",
    description="Upload PDFs and chat with a RAG-powered assistant",
    version="1.0.0",
)

# Include API routers
app.include_router(documents.router)
app.include_router(chat.router)

# Serve static files (HTML, CSS, JS)
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Serve the main index.html"""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "PDF RAG Chatbot API"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    """Initialize directories and resources on startup"""
    settings.get_upload_path().mkdir(parents=True, exist_ok=True)
    settings.get_chroma_path().mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
