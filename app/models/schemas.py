from pydantic import BaseModel
from typing import Optional, List


class DocumentUploadResponse(BaseModel):
    doc_id: str
    filename: str
    status: str


class DocumentListItem(BaseModel):
    doc_id: str
    filename: str
    status: str
    pages: int = 0
    chunks: int = 0
    error: Optional[str] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentListItem]


class Source(BaseModel):
    source: str
    page: int
    chunk_index: int
    distance: float
    snippet: str


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []


class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
