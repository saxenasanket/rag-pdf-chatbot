import re
from pathlib import Path
from typing import List
from pypdf import PdfReader


def extract_text_from_pdf(pdf_path: Path) -> dict:
    """Extract text from PDF, page by page.
    Returns: {"pages": [{page_num, text, is_empty}]}
    """
    reader = PdfReader(pdf_path)
    pages = []

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        is_empty = len(text) < 50

        pages.append(
            {
                "page_num": page_num,
                "text": text,
                "is_empty": is_empty,
            }
        )

    return {"pages": pages}


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks.
    Tries to split on paragraph breaks (double newlines), then sentences, then hard cut.
    Prioritizes semantic boundaries (sections) over character limits.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    current_pos = 0

    while current_pos < len(text):
        chunk_end = current_pos + chunk_size

        if chunk_end >= len(text):
            chunk = text[current_pos:].strip()
            if chunk:
                chunks.append(chunk)
            break

        # Priority 1: Try to find a paragraph break (double newline) — best for semantic sections
        paragraph_pos = text.rfind("\n\n", current_pos, chunk_end)
        if paragraph_pos > current_pos + chunk_size * 0.4:  # Lowered threshold from 0.5
            chunk_end = paragraph_pos
        else:
            # Priority 2: Try sentence boundary (". ")
            sentence_pos = text.rfind(". ", current_pos, chunk_end)
            if sentence_pos > current_pos + chunk_size * 0.4:
                chunk_end = sentence_pos + 2
            else:
                # Priority 3: Try any period
                period_pos = text.rfind(".", current_pos, chunk_end)
                if period_pos > current_pos + chunk_size * 0.4:
                    chunk_end = period_pos + 1

        chunk = text[current_pos:chunk_end].strip()
        if chunk:
            chunks.append(chunk)
        current_pos = chunk_end - overlap

    return [c for c in chunks if len(c) > 50]  # Filter out tiny chunks


def ingest_pdf(
    pdf_path: Path,
    doc_id: str,
    filename: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> dict:
    """Ingest a PDF, extract text, and create chunks with metadata.

    Returns: {
        "success": bool,
        "doc_id": str,
        "filename": str,
        "pages": int,
        "chunks": list of {id, text, metadata},
        "error": str (if not success)
    }
    """
    try:
        extraction = extract_text_from_pdf(pdf_path)
        pages = extraction["pages"]

        all_chunks = []
        total_non_empty_pages = 0

        for page_data in pages:
            if page_data["is_empty"]:
                continue

            total_non_empty_pages += 1
            page_text = page_data["text"]
            page_num = page_data["page_num"]

            page_chunks = chunk_text(page_text, chunk_size, overlap)

            for chunk_idx, chunk_text_content in enumerate(page_chunks):
                chunk_id = f"{doc_id}_p{page_num}_c{chunk_idx}"
                metadata = {
                    "doc_id": doc_id,
                    "source": filename,
                    "page": page_num,
                    "chunk_index": chunk_idx,
                    "char_count": len(chunk_text_content),
                }
                all_chunks.append(
                    {
                        "id": chunk_id,
                        "text": chunk_text_content,
                        "metadata": metadata,
                    }
                )

        return {
            "success": True,
            "doc_id": doc_id,
            "filename": filename,
            "pages": total_non_empty_pages,
            "chunks": all_chunks,
        }

    except Exception as e:
        return {
            "success": False,
            "doc_id": doc_id,
            "filename": filename,
            "error": str(e),
        }
