from dataclasses import dataclass, field

from .chunking import chunk_text
from .contracts import DocumentCreate, DocumentRecord, RetrievalResult
from .ingestion import (
    DeterministicEmbeddingProvider,
    EmbeddingProvider,
    PlainTextExtractor,
    TextExtractor,
    VectorStore,
)
from .repository import DocumentRepository


@dataclass
class DocumentService:
    repository: DocumentRepository
    vector_store: VectorStore
    extractor: TextExtractor = field(default_factory=PlainTextExtractor)
    embedding_provider: EmbeddingProvider = field(default_factory=DeterministicEmbeddingProvider)
    chunk_size: int = 800
    overlap: int = 100

    def ingest(self, request: DocumentCreate, owner_id: str | None = None) -> DocumentRecord:
        repository_owner_id = self.repository.owner_id
        if owner_id is not None and owner_id != repository_owner_id:
            raise ValueError("owner_id does not match the repository owner")
        text = self.extractor.extract(request.content, request.content_type)
        document = self.repository.create(
            filename=request.filename,
            document_type=request.document_type.value,
            content_type=request.content_type,
            status="ingested",
            source=request.source,
            metadata_json=request.metadata,
        )
        chunks = chunk_text(
            text,
            document_id=document.id,
            owner_id=repository_owner_id,
            filename=document.filename,
            document_type=request.document_type,
            chunk_size=self.chunk_size,
            overlap=self.overlap,
        )
        for chunk in chunks:
            chunk.embedding = self.embedding_provider.embed(chunk.text)
        self.vector_store.upsert(chunks)
        return DocumentRecord(
            document_id=document.id,
            owner_id=document.owner_id,
            filename=document.filename,
            document_type=document.document_type,
            content_type=document.content_type,
            status=document.status,
            source=document.source,
            created_at=document.created_at,
            metadata=document.metadata_json,
        )

    def retrieve(self, query: str, owner_id: str, top_k: int = 5) -> list[RetrievalResult]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if top_k <= 0 or top_k > 100:
            raise ValueError("top_k must be between 1 and 100")
        return self.vector_store.search(
            self.embedding_provider.embed(query),
            owner_id=owner_id,
            top_k=top_k,
        )
