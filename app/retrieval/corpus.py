from pathlib import Path

from pydantic import TypeAdapter

from app.core.errors import IntegrationNotConfigured
from app.retrieval.schemas import KnowledgeChunk, KnowledgeDocument


def load_documents(path: Path) -> list[KnowledgeDocument]:
    try:
        documents = TypeAdapter(list[KnowledgeDocument]).validate_json(
            path.read_text(encoding="utf-8-sig")
        )
        if len({document.id for document in documents}) != len(documents):
            raise ValueError("Duplicate document IDs")
        return documents
    except (OSError, ValueError) as exc:
        raise IntegrationNotConfigured("Knowledge corpus is missing or invalid.") from exc


def chunk_documents(
    documents: list[KnowledgeDocument], chunk_words: int = 160, overlap_words: int = 30
) -> list[KnowledgeChunk]:
    if chunk_words < 1 or not 0 <= overlap_words < chunk_words:
        raise ValueError("Chunk size must be positive and overlap smaller than the chunk.")
    chunks = []
    for document in documents:
        words = document.text.split()
        for number, start in enumerate(range(0, len(words), chunk_words - overlap_words)):
            chunks.append(
                KnowledgeChunk(
                    chunk_id=f"{document.id}:{number:04d}",
                    document_id=document.id,
                    title=document.title,
                    source=document.source,
                    text=" ".join(words[start : start + chunk_words]),
                    store_ids=document.store_ids,
                    is_mock=document.is_mock,
                )
            )
            if start + chunk_words >= len(words):
                break
    return chunks
