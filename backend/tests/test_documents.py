import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_personalos.db")
os.environ.setdefault("DEMO_PASSWORD", "test-demo-password")

from app.db import Base, SessionLocal, engine
from app.documents.chunking import chunk_text
from app.documents.contracts import DocumentCreate, DocumentType
from app.documents.ingestion import (
    DeterministicEmbeddingProvider,
    InMemoryVectorStore,
)
from app.documents.repository import DocumentRepository
from app.documents.service import DocumentService
from app.mcp.client import MCPClient
from app.mcp.contracts import MCPAuthorizationContext, MCPInvocationRequest, MCPToolIdentity
from app.mcp.errors import MCPAuthorizationError
from app.mcp.registry import default_mcp_registry, register_document_search_tool
from app.routing.contracts import AgentName, Capability, Intent
from app.routing.policy import PolicyEngine


Base.metadata.create_all(engine)


def service_for(owner_id):
    provider = DeterministicEmbeddingProvider(dimensions=16)
    return DocumentService(
        DocumentRepository(SessionLocal(), owner_id),
        InMemoryVectorStore(provider),
        embedding_provider=provider,
        chunk_size=24,
        overlap=4,
    )


def test_chunking_is_deterministic_and_preserves_ownership_metadata():
    kwargs = {
        "document_id": "doc-1",
        "owner_id": "user-1",
        "filename": "policy.txt",
        "document_type": DocumentType.INSURANCE,
        "chunk_size": 10,
        "overlap": 2,
    }
    first = chunk_text("abcdefghij klmnopqrst uvwxyz", **kwargs)
    second = chunk_text("abcdefghij klmnopqrst uvwxyz", **kwargs)
    assert [item.chunk_id for item in first] == [item.chunk_id for item in second]
    assert all(item.owner_id == "user-1" for item in first)
    assert all(item.document_id == "doc-1" for item in first)


def test_ingestion_persists_document_and_retrieves_owned_top_k():
    owner = "document-test-owner"
    service = service_for(owner)
    record = service.ingest(
        DocumentCreate(
            filename="renewal.txt",
            document_type=DocumentType.RENEWAL,
            content_type="text/plain",
            content="Renewal date is in June. Keep the renewal certificate available.",
            metadata={"source_ref": "synthetic"},
        ),
        owner,
    )
    assert record.owner_id == owner
    assert record.document_type is DocumentType.RENEWAL
    results = service.retrieve("renewal certificate", owner, top_k=1)
    assert len(results) == 1
    assert results[0].document_id == record.document_id
    assert results[0].filename == "renewal.txt"
    assert results[0].document_type is DocumentType.RENEWAL
    assert results[0].chunk_id
    assert results[0].score is not None
    service.repository.repository.db.close()


def test_ingestion_rejects_owner_mismatch_before_persistence():
    service = service_for("owner-a")
    existing_count = len(service.repository.list_owned())
    with pytest.raises(ValueError, match="repository owner"):
        service.ingest(
            DocumentCreate(
                filename="private.txt",
                content_type="text/plain",
                content="private content",
            ),
            "owner-b",
        )
    assert len(service.repository.list_owned()) == existing_count
    service.repository.repository.db.close()


def test_vector_retrieval_filters_cross_user_chunks():
    provider = DeterministicEmbeddingProvider(dimensions=16)
    store = InMemoryVectorStore(provider)
    owner_service = DocumentService(
        DocumentRepository(SessionLocal(), "owner-a"),
        store,
        embedding_provider=provider,
    )
    other_service = DocumentService(
        DocumentRepository(SessionLocal(), "owner-b"),
        store,
        embedding_provider=provider,
    )
    owner_service.ingest(
        DocumentCreate(filename="a.txt", content_type="text/plain", content="private alpha"),
        "owner-a",
    )
    other_service.ingest(
        DocumentCreate(filename="b.txt", content_type="text/plain", content="private beta"),
        "owner-b",
    )
    results = owner_service.retrieve("private", "owner-a", top_k=10)
    assert results
    assert all(result.filename == "a.txt" for result in results)
    owner_service.repository.repository.db.close()
    other_service.repository.repository.db.close()


def test_document_mcp_tool_requires_document_policy_and_agent():
    registry = default_mcp_registry()
    register_document_search_tool(registry, lambda payload: {
        "owner_id": payload["authenticated_user_id"],
        "results": [],
    })
    decision = PolicyEngine().evaluate(
        Intent.DOCUMENT_SEARCH,
        {"document.read"},
        user=type("User", (), {"is_active": True})(),
        ownership_verified=True,
        request_id="document-mcp-test",
    )
    context = MCPAuthorizationContext(
        user_id="owner-a",
        agent=AgentName.DOCUMENT,
        policy_decision=decision,
    )
    request = MCPInvocationRequest(
        request_id="document-request",
        identity=MCPToolIdentity(
            server_name="personalos-safe-mock",
            tool_name="document.search",
        ),
        capability=Capability.DOCUMENT_READ,
        authenticated_user_id="owner-a",
        agent=AgentName.DOCUMENT,
        input={"query": "certificate"},
    )
    result = MCPClient(registry).invoke(request, context)
    assert result.success
    assert result.data["owner_id"] == "owner-a"


def test_document_mcp_rejects_wrong_agent_or_capability():
    registry = default_mcp_registry()
    register_document_search_tool(registry, lambda payload: {})
    decision = PolicyEngine().evaluate(
        Intent.DOCUMENT_SEARCH,
        {"document.read"},
        user=type("User", (), {"is_active": True})(),
        ownership_verified=True,
    )
    context = MCPAuthorizationContext(
        user_id="owner-a",
        agent=AgentName.DOCUMENT,
        policy_decision=decision,
    )
    request = MCPInvocationRequest(
        request_id="document-request",
        identity=MCPToolIdentity(
            server_name="personalos-safe-mock",
            tool_name="document.search",
        ),
        capability=Capability.STOCK_READ,
        authenticated_user_id="owner-a",
        agent=AgentName.DOCUMENT,
    )
    import pytest
    with pytest.raises(MCPAuthorizationError):
        MCPClient(registry).invoke(request, context)
