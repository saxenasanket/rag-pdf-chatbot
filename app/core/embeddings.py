from abc import ABC, abstractmethod
from typing import List
from app.config import settings


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        pass


class VoyageEmbeddings(EmbeddingProvider):
    def __init__(self):
        try:
            import voyageai
        except ImportError:
            raise ImportError(
                "voyageai not installed. Install with: pip install voyageai"
            )
        self.client = voyageai.Client(api_key=settings.voyage_api_key)
        self.model = "voyage-3.5"

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embed(
            texts, model=self.model, input_type="document"
        )
        return response.embeddings

    def embed_query(self, text: str) -> List[float]:
        response = self.client.embed(
            [text], model=self.model, input_type="query"
        )
        return response.embeddings[0]


class LocalEmbeddings(EmbeddingProvider):
    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. Install with: "
                "pip install sentence-transformers torch"
            )
        self.model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        self.query_prefix = "Represent this sentence for searching relevant passages: "

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, convert_to_numpy=False)
        return [e.tolist() for e in embeddings]

    def embed_query(self, text: str) -> List[float]:
        prefixed_text = self.query_prefix + text
        embedding = self.model.encode(prefixed_text, convert_to_numpy=False)
        return embedding.tolist()


def get_embedding_provider() -> EmbeddingProvider:
    if settings.embedding_provider.lower() == "voyage":
        return VoyageEmbeddings()
    elif settings.embedding_provider.lower() == "local":
        return LocalEmbeddings()
    else:
        raise ValueError(
            f"Unknown embedding provider: {settings.embedding_provider}. "
            "Use 'voyage' or 'local'."
        )


# Singleton instance
_provider = None


def embed_documents(texts: List[str]) -> List[List[float]]:
    global _provider
    if _provider is None:
        _provider = get_embedding_provider()
    return _provider.embed_documents(texts)


def embed_query(text: str) -> List[float]:
    global _provider
    if _provider is None:
        _provider = get_embedding_provider()
    return _provider.embed_query(text)
