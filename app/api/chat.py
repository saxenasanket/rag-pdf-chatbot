from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse, Source
from app.core.rag import get_rag_engine

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message and get an answer grounded in the uploaded PDFs.
    Optionally include conversation history for context.

    Request:
    {
        "message": "What was Q3 revenue?",
        "history": [
            {"role": "user", "content": "Tell me about Q3..."},
            {"role": "assistant", "content": "Q3 was a strong quarter..."}
        ]
    }

    Response:
    {
        "answer": "Q3 revenue was $4.2M [report.pdf, p.12]...",
        "sources": [
            {
                "source": "report.pdf",
                "page": 12,
                "chunk_index": 2,
                "distance": 0.12,
                "snippet": "Q3 revenue was $4.2M..."
            }
        ]
    }
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    rag_engine = get_rag_engine()

    try:
        answer, sources = rag_engine.chat(
            question=request.message,
            history=request.history,
        )

        return ChatResponse(
            answer=answer,
            sources=sources,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
