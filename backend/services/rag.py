"""RAG layer — per master-spec §15.

Prefers ChromaDB + multilingual sentence-transformers (same embedding model
Anti-FraudX uses, which also covers Russian). Falls back to a plain
keyword-overlap search over the same documents if those heavy dependencies
aren't installed yet, so the rest of the system keeps working without them.
"""
import json
from pathlib import Path
from typing import Optional

from backend.core.config import settings


def _knowledge_dir() -> Path:
    return settings.resolved_asset(settings.knowledge_dir)


def _iter_documents():
    kdir = _knowledge_dir()

    for item in json.loads((kdir / "manipulations.json").read_text(encoding="utf-8")):
        hints = "; ".join(item.get("phrasing_hints", []))
        text = f"{item['name']}: {item['defensive_definition']} Подсказки по тону: {hints}"
        yield f"manip::{item['id']}", text, {"category": item.get("category", "")}

    for item in json.loads((kdir / "red_flags.json").read_text(encoding="utf-8")):
        text = f"{item['code']}: {item['description']}"
        yield f"redflag::{item['code']}", text, {"category": item.get("category", "")}

    for item in json.loads((kdir / "educational_material.json").read_text(encoding="utf-8")):
        yield f"edu::{item['id']}", item["text"], {"category": "educational"}

    for persona in ("sveta", "sergey"):
        for item in json.loads((kdir / "personas" / persona / "timeline.json").read_text(encoding="utf-8")):
            yield f"timeline::{persona}::{item['id']}", item["description"], {"category": "biography", "persona": persona}


class RagService:
    def __init__(self):
        self._docs = list(_iter_documents())
        self._backend = "keyword"
        if settings.rag_enabled:
            try:
                self._init_chroma()
                self._backend = "chroma"
            except Exception:
                self._backend = "keyword"

    def _init_chroma(self) -> None:
        import chromadb
        from sentence_transformers import SentenceTransformer

        persist_dir = str(settings.resolved(settings.rag_persist_dir))
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._embedder = SentenceTransformer(settings.embedding_model)
        self._collection = self._client.get_or_create_collection("sveta_knowledge")
        if self._collection.count() == 0:
            ids = [d[0] for d in self._docs]
            texts = [d[1] for d in self._docs]
            metadatas = [d[2] for d in self._docs]
            embeddings = self._embedder.encode(texts).tolist()
            self._collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)

    def retrieve(self, query: str, n_results: int = 3, category: Optional[str] = None) -> list[str]:
        if self._backend == "chroma":
            return self._chroma_retrieve(query, n_results)
        return self._keyword_retrieve(query, n_results, category)

    def _chroma_retrieve(self, query: str, n_results: int) -> list[str]:
        embedding = self._embedder.encode(query).tolist()
        results = self._collection.query(query_embeddings=[embedding], n_results=n_results)
        docs = results.get("documents") or [[]]
        return docs[0]

    def _keyword_retrieve(self, query: str, n_results: int, category: Optional[str]) -> list[str]:
        q_words = set(query.lower().split())
        scored = []
        for _id, text, meta in self._docs:
            if category and meta.get("category") not in (category, ""):
                continue
            overlap = len(q_words & set(text.lower().split()))
            if overlap:
                scored.append((overlap, text))
        scored.sort(key=lambda x: -x[0])
        return [text for _, text in scored[:n_results]]

    @property
    def backend(self) -> str:
        return self._backend


_rag_service: Optional[RagService] = None


def get_rag_service() -> RagService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RagService()
    return _rag_service
