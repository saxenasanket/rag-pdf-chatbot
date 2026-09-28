import json
from pathlib import Path
from datetime import datetime
from typing import List
from app.config import settings


class DocumentRegistry:
    def __init__(self):
        self.registry_path = Path(settings.upload_dir) / "documents.json"
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        if self.registry_path.exists():
            with open(self.registry_path, "r") as f:
                self.documents = json.load(f)
        else:
            self.documents = {}

    def _save(self):
        with open(self.registry_path, "w") as f:
            json.dump(self.documents, f, indent=2)

    def create(self, doc_id: str, filename: str) -> None:
        """Create a new document entry in processing status."""
        self.documents[doc_id] = {
            "doc_id": doc_id,
            "filename": filename,
            "status": "processing",
            "pages": 0,
            "chunks": 0,
            "created_at": datetime.utcnow().isoformat(),
            "error": None,
        }
        self._save()

    def update_status(
        self,
        doc_id: str,
        status: str,
        pages: int = 0,
        chunks: int = 0,
        error: str = None,
    ) -> None:
        """Update document status and stats."""
        if doc_id in self.documents:
            self.documents[doc_id]["status"] = status
            self.documents[doc_id]["pages"] = pages
            self.documents[doc_id]["chunks"] = chunks
            if error:
                self.documents[doc_id]["error"] = error
            self._save()

    def delete(self, doc_id: str) -> None:
        """Remove a document from registry."""
        if doc_id in self.documents:
            del self.documents[doc_id]
            self._save()

    def get(self, doc_id: str) -> dict:
        """Get a document entry."""
        return self.documents.get(doc_id, {})

    def list_all(self) -> List[dict]:
        """List all documents."""
        return list(self.documents.values())


# Singleton instance
_registry = None


def get_registry() -> DocumentRegistry:
    global _registry
    if _registry is None:
        _registry = DocumentRegistry()
    return _registry
