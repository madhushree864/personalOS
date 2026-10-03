import hashlib
import re

from .contracts import DocumentChunk, DocumentType


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def chunk_text(
    text: str,
    *,
    document_id: str,
    owner_id: str,
    filename: str,
    document_type: DocumentType,
    chunk_size: int = 800,
    overlap: int = 100,
) -> list[DocumentChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")
    cleaned = clean_text(text)
    if not cleaned:
        return []
    chunks: list[DocumentChunk] = []
    start = 0
    index = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        value = cleaned[start:end]
        chunk_id = hashlib.sha256(
            f"{document_id}:{index}:{value}".encode("utf-8")
        ).hexdigest()[:24]
        chunks.append(DocumentChunk(
            document_id=document_id,
            owner_id=owner_id,
            document_type=document_type,
            filename=filename,
            chunk_id=chunk_id,
            text=value,
            metadata={"chunk_index": index},
        ))
        if end == len(cleaned):
            break
        start = end - overlap
        index += 1
    return chunks
