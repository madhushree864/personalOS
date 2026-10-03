"""Deterministic document ingestion and retrieval foundation."""

from .contracts import (
    DocumentChunk,
    DocumentCreate,
    DocumentRecord,
    DocumentType,
    RetrievalResult,
)
from .service import DocumentService

__all__ = [
    "DocumentChunk",
    "DocumentCreate",
    "DocumentRecord",
    "DocumentService",
    "DocumentType",
    "RetrievalResult",
]
