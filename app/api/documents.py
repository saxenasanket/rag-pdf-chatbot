from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from pathlib import Path
import uuid
from typing import List

from app.config import settings
from app.models.schemas import (
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentListItem,
)
from app.core.registry import get_registry
from app.core.pdf_ingest import ingest_pdf
from app.core.embeddings import embed_documents
from app.core.vectorstore import get_vectorstore

router = APIRouter(prefix="/api/documents", tags=["documents"])


def validate_pdf(file_content: bytes) -> bool:
    """Check if file starts with PDF magic bytes."""
    return file_content.startswith(b"%PDF")


def process_pdf_ingestion(
    pdf_path: Path,
    doc_id: str,
    filename: str,
) -> None:
    """Background task: extract, embed, and store PDF chunks."""
    registry = get_registry()
    vectorstore = get_vectorstore()

    try:
        # Extract and chunk
        result = ingest_pdf(pdf_path, doc_id, filename)

        if not result["success"]:
            registry.update_status(
                doc_id,
                status="error",
                error=result.get("error", "Unknown error"),
            )
            return

        chunks = result["chunks"]

        if not chunks:
            registry.update_status(
                doc_id,
                status="error",
                error="No extractable text found in PDF",
            )
            return

        # Embed all chunks
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings = embed_documents(chunk_texts)

        # Store in vectorstore
        vectorstore.add(
            ids=[chunk["id"] for chunk in chunks],
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=[chunk["metadata"] for chunk in chunks],
        )

        # Update registry with success
        registry.update_status(
            doc_id,
            status="ready",
            pages=result["pages"],
            chunks=len(chunks),
        )

    except Exception as e:
        registry.update_status(
            doc_id,
            status="error",
            error=str(e),
        )


@router.post("/", response_model=List[DocumentUploadResponse])
async def upload_documents(
    files: list[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
):
    """
    Upload one or more PDF files for ingestion.
    Returns immediately with processing status; ingestion happens in background.
    """
    upload_dir = settings.get_upload_path()
    upload_dir.mkdir(parents=True, exist_ok=True)

    responses = []

    for file in files:
        # Validate filename
        if not file.filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        # Check file extension
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files allowed")

        # Read and validate PDF magic bytes
        content = await file.read()
        if not validate_pdf(content):
            raise HTTPException(status_code=400, detail=f"{file.filename} is not a valid PDF")

        # Generate document ID and save file
        doc_id = str(uuid.uuid4())
        pdf_path = upload_dir / f"{doc_id}.pdf"

        with open(pdf_path, "wb") as f:
            f.write(content)

        # Create registry entry
        registry = get_registry()
        registry.create(doc_id, file.filename)

        # Queue background ingestion task
        background_tasks.add_task(
            process_pdf_ingestion,
            pdf_path,
            doc_id,
            file.filename,
        )

        responses.append(
            DocumentUploadResponse(
                doc_id=doc_id,
                filename=file.filename,
                status="processing",
            )
        )

    return responses


@router.get("/", response_model=DocumentListResponse)
async def list_documents():
    """
    List all uploaded documents with their status and statistics.
    """
    registry = get_registry()
    documents = registry.list_all()

    items = [
        DocumentListItem(
            doc_id=doc["doc_id"],
            filename=doc["filename"],
            status=doc["status"],
            pages=doc.get("pages", 0),
            chunks=doc.get("chunks", 0),
            error=doc.get("error"),
        )
        for doc in documents
    ]

    return DocumentListResponse(documents=items)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """
    Delete a document: remove file, registry entry, and Chroma chunks.
    """
    registry = get_registry()
    doc = registry.get(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove from Chroma
    vectorstore = get_vectorstore()
    vectorstore.delete(doc_id)

    # Remove from filesystem
    upload_dir = settings.get_upload_path()
    pdf_path = upload_dir / f"{doc_id}.pdf"
    if pdf_path.exists():
        pdf_path.unlink()

    # Remove from registry
    registry.delete(doc_id)

    return {"status": "deleted", "doc_id": doc_id}


@router.post("/clean")
async def clean_all():
    """
    Delete ALL documents: remove all files, registry, and Chroma data.
    """
    registry = get_registry()
    vectorstore = get_vectorstore()
    upload_dir = settings.get_upload_path()

    # Get all documents
    documents = registry.list_all()

    # Delete each document
    for doc in documents:
        doc_id = doc["doc_id"]

        # Remove from Chroma
        vectorstore.delete(doc_id)

        # Remove from filesystem
        pdf_path = upload_dir / f"{doc_id}.pdf"
        if pdf_path.exists():
            pdf_path.unlink()

        # Remove from registry
        registry.delete(doc_id)

    return {"status": "cleaned", "message": "All documents deleted"}
