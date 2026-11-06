from functools import lru_cache
from typing import Protocol

from app.core.config import get_settings
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.corpus import chunk_documents, load_documents
from app.retrieval.schemas import RetrievalContext


class Retriever(Protocol):
    async def retrieve(
        self, query: str, store_id: str, top_k: int | None = None
    ) -> RetrievalContext: ...


class DisabledRetriever:
    async def retrieve(
        self, query: str, store_id: str, top_k: int | None = None
    ) -> RetrievalContext:
        return RetrievalContext()


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    settings = get_settings()
    if settings.rag_provider == "disabled":
        return DisabledRetriever()
    documents = load_documents(settings.rag_corpus_path)
    chunks = chunk_documents(documents, settings.rag_chunk_words, settings.rag_overlap_words)
    return BM25Retriever(chunks, settings.rag_top_k, settings.rag_k1, settings.rag_b)
