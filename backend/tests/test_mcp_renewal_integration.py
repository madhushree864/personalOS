import os
from datetime import date, timedelta
from dataclasses import replace

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_personalos.db")
os.environ.setdefault("DEMO_PASSWORD", "test-demo-password")

from app.db import SessionLocal
from app.mcp.adapters.renewal import RenewalMCPAdapter
from app.mcp.client import MCPClient
from app.mcp.contracts import (
    MCPAuthorizationContext,
    MCPInvocationRequest,
    MCPToolIdentity,
)
from app.mcp.errors import MCPAuthorizationError, MCPToolExecutionError
from app.mcp.registry import default_mcp_registry
from app.mcp.transport import RenewalMCPTransport
from app.models import Renewal
from app.repositories import Repository
from app.routing.contracts import AgentName, Capability, Intent
from app.routing.policy import PolicyEngine
from app.routing.supervisor import SupervisorRoutingService


def authorization(
    *,
    user_id="renewal-owner",
    active=True,
    authenticated=True,
    ownership=True,
    agent=AgentName.RENEWAL_SHORT,
    capabilities=None,
    approved=True,
):
    decision = PolicyEngine().evaluate(
        Intent.RENEWAL_QUERY,
        capabilities or {"renewal.read"},
        user=type("User", (), {"is_active": active})(),
        authenticated=authenticated,
        active=active,
        ownership_verified=ownership,
        approved=approved,
        request_id="renewal-mcp-test",
    )
    return MCPAuthorizationContext(
        user_id=user_id,
        agent=agent,
        policy_decision=decision,
    )


def request(*, user_id="renewal-owner", agent=AgentName.RENEWAL_SHORT, capability=Capability.RENEWAL_READ):
    return MCPInvocationRequest(
        request_id="renewal-request",
        identity=MCPToolIdentity(
            server_name="personalos-safe-mock",
            tool_name="renewal.read",
        ),
        capability=capability,
        authenticated_user_id=user_id,
        agent=agent,
        input={"query": "renewals"},
    )


def client_for(owner_id):
    db = SessionLocal()
    db.add(
        Renewal(
            owner_id=owner_id,
            name=f"{owner_id} renewal",
            category="Insurance",
            due_date=date.today() + timedelta(days=30),
            reminder_days=7,
            status="upcoming",
        )
    )
    db.commit()
    repository = Repository(db, owner_id)
    adapter = RenewalMCPAdapter(repository)
    return MCPClient(default_mcp_registry(), RenewalMCPTransport(adapter)), db


def unapproved_authorization():
    context = authorization()
    return context.model_copy(
        update={"policy_decision": replace(context.policy_decision, allowed=False)}
    )


def test_authorized_renewal_read_returns_owner_domain_data():
    client, db = client_for("renewal-owner")
    try:
        result = client.invoke(request(), authorization())
        assert result.success
        assert result.data["renewals"][0]["name"] == "renewal-owner renewal"
    finally:
        db.close()


def test_supervisor_routes_renewal_query_through_mcp_transport():
    client, db = client_for("renewal-owner")
    try:
        user = type(
            "User",
            (),
            {"id": "renewal-owner", "is_active": True, "permissions": ["renewal.read"]},
        )()
        result = SupervisorRoutingService().route(
            "What needs renewal?",
            Repository(db, "renewal-owner"),
            user,
        )
        assert result["data"]["renewals"][0]["name"] == "renewal-owner renewal"
        assert result["routing_decision"]["capability"] == "renewal.read"
    finally:
        db.close()


def test_cross_user_renewal_access_is_owner_scoped():
    client, db = client_for("renewal-owner")
    try:
        with pytest.raises(MCPToolExecutionError):
            client.invoke(
                request(user_id="other-user"),
                authorization(user_id="other-user"),
            )
    finally:
        db.close()


@pytest.mark.parametrize(
    "context",
    [
        authorization(authenticated=False),
        authorization(active=False),
        authorization(ownership=False),
        unapproved_authorization(),
        authorization(agent=AgentName.HEALTH_SHORT),
    ],
)
def test_renewal_mcp_rejects_unauthorized_contexts(context):
    client, db = client_for("renewal-owner")
    try:
        with pytest.raises(MCPAuthorizationError):
            client.invoke(request(agent=context.agent), context)
    finally:
        db.close()


def test_renewal_mcp_rejects_wrong_capability():
    client, db = client_for("renewal-owner")
    try:
        with pytest.raises(MCPAuthorizationError):
            client.invoke(
                request(capability=Capability.HEALTH_READ),
                authorization(),
            )
    finally:
        db.close()


def test_renewal_integration_does_not_expose_investment_execution():
    registry = default_mcp_registry()
    assert {tool.identity.tool_name for tool in registry.tools()} == {
        "renewal.read",
        "health.read",
        "market.read",
    }
    assert all(tool.read_only for tool in registry.tools())
