from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentType(StrEnum):
    IDENTITY = "identity"
    RENEWAL = "renewal"
    INSURANCE = "insurance"
    MEDICAL = "medical"
    FINANCIAL = "financial"
    CERTIFICATE = "certificate"
    GENERAL = "general"


class DocumentStatus(StrEnum):
    INGESTED = "ingested"
    FAILED = "failed"


class DocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1, max_length=255)
    document_type: DocumentType = DocumentType.GENERAL
    content_type: str = Field(min_length=1, max_length=120)
    source: str = Field(default="upload", min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=2_000_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    owner_id: str
    filename: str
    document_type: DocumentType
    content_type: str
    status: DocumentStatus
    source: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    owner_id: str
    document_type: DocumentType
    filename: str
    chunk_id: str
    text: str = Field(min_length=1)
    embedding: list[float] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    filename: str
    chunk_id: str
    document_type: DocumentType
    text: str
    score: float | None = None


class StoredVector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk: DocumentChunk

