import math
import unicodedata
from collections import Counter
from dataclasses import dataclass

from app.retrieval.schemas import KnowledgeChunk, RetrievalContext, RetrievalHit


def tokenize(text: str) -> list[str]:
    """Keep Unicode letters, digits and combining marks, including Indic vowel signs."""
    words, current = [], []
    for character in unicodedata.normalize("NFKC", text).casefold():
        if unicodedata.category(character)[0] in {"L", "N", "M"}:
            current.append(character)
        elif current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    return words


@dataclass(frozen=True)
class IndexedChunk:
    chunk: KnowledgeChunk
    terms: Counter
    length: int


class BM25Retriever:
    """Small in-memory BM25 index with positive IDF and length normalization.

    Uses log(1 + (N - df + 0.5) / (df + 0.5)). No embeddings, network or model
    calls. Store filtering precedes scoring and corpus statistics.
    """

    def __init__(
        self, chunks: list[KnowledgeChunk], top_k: int = 3, k1: float = 1.2, b: float = 0.75
    ):
        if not 1 <= top_k <= 10 or not math.isfinite(k1) or k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("Invalid BM25 parameters")
        self.top_k, self.k1, self.b = top_k, k1, b
        self.index = []
        for chunk in chunks:
            terms = tokenize(f"{chunk.title} {chunk.text}")
            if terms:
                self.index.append(IndexedChunk(chunk, Counter(terms), len(terms)))

    async def retrieve(
        self, query: str, store_id: str, top_k: int | None = None
    ) -> RetrievalContext:
        limit = self.top_k if top_k is None else top_k
        if not 1 <= limit <= 10:
            raise ValueError("top_k must be between 1 and 10")
        eligible = [
            entry
            for entry in self.index
            if not entry.chunk.store_ids or store_id in entry.chunk.store_ids
        ]
        if not eligible:
            return RetrievalContext(provider="bm25", status="empty")
        query_terms = set(tokenize(query))
        count = len(eligible)
        average_length = sum(entry.length for entry in eligible) / count
        frequencies = Counter(
            term for entry in eligible for term in query_terms if term in entry.terms
        )
        ranked = []
        for entry in eligible:
            score = 0.0
            normalization = self.k1 * (1 - self.b + self.b * entry.length / average_length)
            for term in sorted(query_terms):
                frequency = entry.terms[term]
                if not frequency:
                    continue
                df = frequencies[term]
                idf = math.log1p((count - df + 0.5) / (df + 0.5))
                score += idf * frequency * (self.k1 + 1) / (frequency + normalization)
            if score > 0:
                ranked.append(RetrievalHit(**entry.chunk.model_dump(), score=score))
        ranked.sort(key=lambda hit: (-hit.score, hit.chunk_id))
        return RetrievalContext(
            provider="bm25", status="matched" if ranked else "no_matches", hits=ranked[:limit]
        )
