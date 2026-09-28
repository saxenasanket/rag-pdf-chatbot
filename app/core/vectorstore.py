import chromadb
from typing import List
from app.config import settings


class VectorStore:
    def __init__(self):
        self.chroma_dir = settings.get_chroma_path()
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.chroma_dir))
        self.collection = self.client.get_or_create_collection(
            name="pdf_chunks",
            metadata={"hnsw:space": "cosine"},
        )

    def add(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[dict],
    ) -> None:
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def query(
        self, query_embedding: List[float], n_results: int = 5
    ) -> dict:
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        return results

    def delete(self, doc_id: str) -> None:
        self.collection.delete(where={"doc_id": doc_id})

    def get_collection_stats(self) -> dict:
        return self.collection.count()


# Singleton instance
_vectorstore = None


def get_vectorstore() -> VectorStore:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = VectorStore()
    return _vectorstore
