import os
from dataclasses import replace

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_personalos.db")
os.environ.setdefault("DEMO_PASSWORD", "test-demo-password")

import pytest

from app.mcp.client import MCPClient
from app.mcp.contracts import (
    MCPAuthorizationContext,
    MCPInvocationRequest,
    MCPToolIdentity,
)
from app.mcp.errors import (
    MCPAuthorizationError,
    MCPToolNotFoundError,
)
from app.mcp.registry import default_mcp_registry
from app.routing.contracts import AgentName, Capability, Intent
from app.routing.policy import PolicyEngine


def authorization(intent, capabilities, *, user_id="user-001", agent=None):
    decision = PolicyEngine().evaluate(
        intent,
        capabilities,
        user=type("User", (), {"is_active": True})(),
        ownership_verified=True,
        request_id="mcp-test",
    )
    return MCPAuthorizationContext(
        user_id=user_id,
        agent=agent or AgentName.STOCK_ANALYSIS_SHORT,
        policy_decision=decision,
    )


def request(tool_name, capability=Capability.STOCK_READ, *, agent=AgentName.STOCK_ANALYSIS_SHORT):
    return MCPInvocationRequest(
        request_id="request-1",
        identity=MCPToolIdentity(server_name="personalos-safe-mock", tool_name=tool_name),
        capability=capability,
        authenticated_user_id="user-001",
        agent=agent,
        input={"symbol": "AAPL"},
    )


def test_registered_tool_can_be_resolved_and_invoked():
    client = MCPClient(default_mcp_registry())
    result = client.invoke(
        request("market.read"),
        authorization(Intent.STOCK_ANALYSIS, {"stock.read"}),
    )
    assert result.success is True
    assert result.data["kind"] == "market.read"


def test_unregistered_tool_is_rejected():
    with pytest.raises(MCPToolNotFoundError):
        default_mcp_registry().resolve(
            MCPToolIdentity(server_name="personalos-safe-mock", tool_name="investment.execute")
        )


def test_unauthorized_capability_is_rejected():
    client = MCPClient()
    with pytest.raises(MCPAuthorizationError, match="Policy Engine"):
        client.invoke(
            request("market.read", Capability.STOCK_READ),
            authorization(Intent.STOCK_ANALYSIS, {"renewal.read"}),
        )


def test_stock_analysis_cannot_invoke_investment_execution():
    client = MCPClient()
    with pytest.raises(MCPToolNotFoundError):
        client.registry.resolve(
            MCPToolIdentity(server_name="personalos-safe-mock", tool_name="investment.execute")
        )


def test_mcp_client_cannot_bypass_policy_engine():
    client = MCPClient()
    context = authorization(Intent.STOCK_ANALYSIS, {"stock.read"})
    context = context.model_copy(
        update={"policy_decision": replace(context.policy_decision, allowed=False)}
    )
    with pytest.raises(MCPAuthorizationError):
        client.invoke(request("market.read"), context)


def test_malformed_request_is_rejected():
    with pytest.raises(ValueError):
        MCPInvocationRequest(
            request_id="",
            identity=MCPToolIdentity(server_name="personalos-safe-mock", tool_name="market.read"),
            capability=Capability.STOCK_READ,
            authenticated_user_id="user-001",
            agent=AgentName.STOCK_ANALYSIS_SHORT,
        )
