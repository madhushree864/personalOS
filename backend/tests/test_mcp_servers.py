import asyncio
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_personalos.db")
os.environ.setdefault("DEMO_PASSWORD", "test-demo-password")

sys.path.insert(0, str(Path(__file__).parents[2]))

from app.mcp.client import MCPClient
from app.mcp.contracts import MCPAuthorizationContext, MCPInvocationRequest, MCPToolIdentity
from app.mcp.errors import MCPToolNotFoundError
from app.mcp.registry import default_mcp_registry
from app.routing.contracts import AgentName, Capability, Intent
from app.routing.policy import PolicyEngine
from mcp_servers.document.server import server as document_server
from mcp_servers.health.server import server as health_server
from mcp_servers.market.server import server as market_server
from mcp_servers.renewal.server import server as renewal_server


def tool_names(server):
    return {tool.name for tool in asyncio.run(server.list_tools())}


@pytest.mark.parametrize(
    "server,tool_name",
    [
        (renewal_server, "renewal.read"),
        (health_server, "health.read"),
        (market_server, "market.read"),
        (document_server, "document.search"),
    ],
)
def test_safe_servers_expose_expected_read_only_tool(server, tool_name):
    names = tool_names(server)
    assert tool_name in names
    assert "investment.execute" not in names


def test_safe_servers_are_instantiable_without_external_services():
    assert renewal_server is not None
    assert health_server is not None
    assert market_server is not None
    assert document_server is not None


def test_registry_capability_mapping_matches_server_tools():
    registry = default_mcp_registry()
    expected = {
        "renewal.read": Capability.RENEWAL_READ,
        "health.read": Capability.HEALTH_READ,
        "market.read": Capability.STOCK_READ,
    }
    for tool in registry.tools():
        assert tool.identity.tool_name in expected
        assert tool.capability is expected[tool.identity.tool_name]
        assert tool.read_only is True


def test_document_server_does_not_expose_investment_execution():
    assert "investment.execute" not in tool_names(document_server)
    assert "investment.execute" not in {
        tool.identity.tool_name for tool in default_mcp_registry().tools()
    }


def test_policy_gated_client_remains_required_for_server_capability():
    client = MCPClient(default_mcp_registry())
    decision = PolicyEngine().evaluate(
        Intent.DOCUMENT_SEARCH,
        {"document.read"},
        user=type("User", (), {"is_active": True})(),
        ownership_verified=True,
        request_id="phase7-test",
    )
    context = MCPAuthorizationContext(
        user_id="user-001",
        agent=AgentName.DOCUMENT,
        policy_decision=decision,
    )
    request = MCPInvocationRequest(
        request_id="phase7-test",
        identity=MCPToolIdentity(
            server_name="personalos-safe-mock",
            tool_name="document.search",
        ),
        capability=Capability.DOCUMENT_READ,
        authenticated_user_id="user-001",
        agent=AgentName.DOCUMENT,
    )
    with pytest.raises(MCPToolNotFoundError):
        client.invoke(request, context)


def test_existing_policy_engine_read_only_market_behavior_is_unchanged():
    decision = PolicyEngine().evaluate(
        Intent.STOCK_ANALYSIS,
        {"stock.read"},
        user=type("User", (), {"is_active": True})(),
        ownership_verified=True,
    )
    assert decision.allowed is True
    assert decision.decision.capability is Capability.STOCK_READ
    assert decision.decision.execution_authorized is False
