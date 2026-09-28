from anthropic import Anthropic
from typing import List, Tuple
from app.config import settings
from app.core.embeddings import embed_query
from app.core.vectorstore import get_vectorstore
from app.models.schemas import Source


SYSTEM_PROMPT = """You are a helpful assistant that answers questions based exclusively on the provided context.

IMPORTANT RULES:
1. Answer ONLY using information from the provided context.
2. If the answer is not in the context, say "I don't have enough information to answer this question based on the provided documents."
3. Always cite your sources using the format [filename, p.N] for specific pages.
4. Be concise and accurate.
5. If multiple sources support the answer, cite all relevant sources."""


class RAGEngine:
    def __init__(self):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.vectorstore = get_vectorstore()
        self.model = settings.claude_model
        self.top_k = settings.top_k

    def retrieve_context(self, question: str) -> Tuple[str, List[Source]]:
        """Retrieve relevant context chunks and return formatted context + sources."""
        query_embedding = embed_query(question)
        results = self.vectorstore.query(query_embedding, n_results=self.top_k)

        sources = []
        context_parts = []

        if results["ids"] and len(results["ids"]) > 0:
            for i, (doc_id, metadata, distance) in enumerate(
                zip(
                    results["ids"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                )
            ):
                chunk_text = results["documents"][0][i]
                source = Source(
                    source=metadata.get("source", "unknown"),
                    page=metadata.get("page", 0),
                    chunk_index=metadata.get("chunk_index", 0),
                    distance=float(distance),
                    snippet=chunk_text[:200] + "..."
                    if len(chunk_text) > 200
                    else chunk_text,
                )
                sources.append(source)

                context_parts.append(
                    f"[Source: {metadata.get('source', 'unknown')}, Page {metadata.get('page', '?')}]\n{chunk_text}"
                )

        context = "\n\n".join(context_parts)
        return context, sources

    def chat(
        self, question: str, history: List[dict] = None
    ) -> Tuple[str, List[Source]]:
        """Answer a question using RAG."""
        if history is None:
            history = []

        context, sources = self.retrieve_context(question)

        if not context:
            return (
                "I don't have any documents to search. Please upload some PDFs first.",
                [],
            )

        full_message = f"Context:\n{context}\n\nQuestion: {question}"

        messages = history + [{"role": "user", "content": full_message}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

        answer = response.content[0].text

        return answer, sources


# Singleton instance
_rag_engine = None


def get_rag_engine() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
