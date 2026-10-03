import hashlib
import math
from collections.abc import Iterable
from typing import Protocol

from .contracts import DocumentChunk, RetrievalResult


class TextExtractor(Protocol):
    def extract(self, content: str, content_type: str) -> str: ...


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]: ...


class VectorStore(Protocol):
    def upsert(self, chunks: Iterable[DocumentChunk]) -> None: ...

    def search(
        self, embedding: list[float], *, owner_id: str, top_k: int
    ) -> list[RetrievalResult]: ...


class PlainTextExtractor:
    def extract(self, content: str, content_type: str) -> str:
        if not content_type.startswith("text/") and content_type != "application/octet-stream":
            raise ValueError("only plain text content is supported by the default extractor")
        return content


class DeterministicEmbeddingProvider:
    """Small local embedding substitute with no network or API dependency."""

    def __init__(self, dimensions: int = 32):
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        values = [0.0] * self.dimensions
        for index, byte in enumerate(hashlib.sha256(text.encode("utf-8")).digest()):
            values[index % self.dimensions] += (byte / 255.0) - 0.5
        magnitude = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / magnitude for value in values]


class InMemoryVectorStore:
    def __init__(self, embedding_provider: EmbeddingProvider):
        self.embedding_provider = embedding_provider
        self._chunks: dict[str, DocumentChunk] = {}

    def upsert(self, chunks: Iterable[DocumentChunk]) -> None:
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk

    def search(self, embedding: list[float], *, owner_id: str, top_k: int) -> list[RetrievalResult]:
        if top_k <= 0:
            return []
        matches = []
        for chunk in self._chunks.values():
            if chunk.owner_id != owner_id:
                continue
            score = sum(left * right for left, right in zip(
                embedding, self.embedding_provider.embed(chunk.text)
            ))
            matches.append(RetrievalResult(
                document_id=chunk.document_id,
                filename=chunk.filename,
                chunk_id=chunk.chunk_id,
                document_type=chunk.document_type,
                text=chunk.text,
                score=score,
            ))
        return sorted(matches, key=lambda item: item.score or 0.0, reverse=True)[:top_k]


class QdrantVectorStore:
    """Optional adapter boundary; importing qdrant is deferred until construction."""

    def __init__(self, collection_name: str, url: str, embedding_provider: EmbeddingProvider):
        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:
            raise RuntimeError("qdrant-client is required only to use QdrantVectorStore") from exc
        self.client = QdrantClient(url=url)
        self.collection_name = collection_name
        self.embedding_provider = embedding_provider

    def upsert(self, chunks: Iterable[DocumentChunk]) -> None:
        raise NotImplementedError("Qdrant writes will be added with the production adapter")

    def search(self, embedding: list[float], *, owner_id: str, top_k: int) -> list[RetrievalResult]:
        raise NotImplementedError("Qdrant search will be added with the production adapter")
