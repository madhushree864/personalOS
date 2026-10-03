import os
from dataclasses import replace
from datetime import date

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_personalos.db")
os.environ.setdefault("DEMO_PASSWORD", "test-demo-password")

from app.db import SessionLocal
from app.mcp.adapters.health import HealthMCPAdapter
from app.mcp.client import MCPClient
from app.mcp.contracts import (
    MCPAuthorizationContext,
    MCPInvocationRequest,
    MCPToolIdentity,
)
from app.mcp.errors import MCPAuthorizationError, MCPToolExecutionError
from app.mcp.registry import default_mcp_registry
from app.mcp.transport import HealthMCPTransport
from app.models import HealthRecord
from app.repositories import Repository
from app.routing.contracts import AgentName, Capability, Intent
from app.routing.policy import PolicyEngine
from app.routing.supervisor import SupervisorRoutingService


def authorization(
    *,
    user_id="health-owner",
    active=True,
    authenticated=True,
    ownership=True,
    agent=AgentName.HEALTH_SHORT,
    capabilities=None,
):
    decision = PolicyEngine().evaluate(
        Intent.HEALTH_QUERY,
        capabilities or {"health.read"},
        user=type("User", (), {"is_active": active})(),
        authenticated=authenticated,
        active=active,
        ownership_verified=ownership,
        request_id="health-mcp-test",
    )
    return MCPAuthorizationContext(
        user_id=user_id,
        agent=agent,
        policy_decision=decision,
    )


def request(
    *,
    user_id="health-owner",
    agent=AgentName.HEALTH_SHORT,
    capability=Capability.HEALTH_READ,
    input_data=None,
):
    return MCPInvocationRequest(
        request_id="health-request",
        identity=MCPToolIdentity(
            server_name="personalos-safe-mock",
            tool_name="health.read",
        ),
        capability=capability,
        authenticated_user_id=user_id,
        agent=agent,
        input=input_data or {"metric": ""},
    )


def client_for(owner_id):
    db = SessionLocal()
    db.add(
        HealthRecord(
            owner_id=owner_id,
            date=date(2026, 1, 1),
            metric="sleep",
            value=7.5,
            unit="hours",
        )
    )
    db.add(
        HealthRecord(
            owner_id=owner_id,
            date=date(2026, 1, 2),
            metric="steps",
            value=8000,
            unit="count",
        )
    )
    db.commit()
    repository = Repository(db, owner_id)
    adapter = HealthMCPAdapter(repository)
    return MCPClient(default_mcp_registry(), HealthMCPTransport(adapter)), db


def denied_authorization():
    context = authorization()
    return context.model_copy(
        update={"policy_decision": replace(context.policy_decision, allowed=False)}
    )


def test_authorized_health_read_returns_owner_domain_data():
    client, db = client_for("health-owner")
    try:
        result = client.invoke(request(), authorization())
        assert result.success
        assert {item["metric"] for item in result.data["records"]} == {"sleep", "steps"}
    finally:
        db.close()


def test_cross_user_health_access_is_prevented():
    client, db = client_for("health-owner")
    try:
        with pytest.raises(MCPToolExecutionError):
            client.invoke(
                request(user_id="other-user"),
                authorization(user_id="other-user"),
            )
    finally:
        db.close()


def test_user_supplied_user_id_cannot_override_trusted_context():
    client, db = client_for("health-owner")
    try:
        result = client.invoke(
            request(input_data={"metric": "", "user_id": "other-user"}),
            authorization(),
        )
        assert result.data["records"]
        assert all(item["metric"] in {"sleep", "steps"} for item in result.data["records"])
    finally:
        db.close()


@pytest.mark.parametrize(
    "context",
    [
        authorization(authenticated=False),
        authorization(active=False),
        authorization(ownership=False),
        authorization(agent=AgentName.RENEWAL_SHORT),
        denied_authorization(),
    ],
)
def test_health_mcp_rejects_unauthorized_contexts(context):
    client, db = client_for("health-owner")
    try:
        with pytest.raises(MCPAuthorizationError):
            client.invoke(request(agent=context.agent), context)
    finally:
        db.close()


def test_health_mcp_rejects_wrong_capability():
    client, db = client_for("health-owner")
    try:
        with pytest.raises(MCPAuthorizationError):
            client.invoke(
                request(capability=Capability.RENEWAL_READ),
                authorization(),
            )
    finally:
        db.close()


def test_supervisor_routes_health_query_through_mcp():
    _, db = client_for("health-owner")
    try:
        user = type(
            "User",
            (),
            {"id": "health-owner", "is_active": True, "permissions": ["health.read"]},
        )()
        result = SupervisorRoutingService().route(
            "Show my health records",
            Repository(db, "health-owner"),
            user,
        )
        assert result["data"]["rawData"]
        assert result["routing_decision"]["capability"] == "health.read"
    finally:
        db.close()


def test_only_health_read_is_domain_integrated_and_investment_is_absent():
    registry = default_mcp_registry()
    assert {tool.identity.tool_name for tool in registry.tools()} == {
        "renewal.read",
        "health.read",
        "market.read",
    }
    assert all(tool.read_only for tool in registry.tools())
