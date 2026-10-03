from collections.abc import Callable
from typing import Any

from .contracts import MCPServerIdentity, MCPToolIdentity, MCPToolRegistration
from .errors import MCPToolNotFoundError
from ..routing.contracts import AgentName, Capability


class MCPRegistry:
    """Deterministic registry; registration is the only discovery mechanism."""

    def __init__(self):
        self._servers: dict[str, MCPServerIdentity] = {}
        self._tools: dict[tuple[str, str], MCPToolRegistration] = {}

    def register_server(self, server: MCPServerIdentity) -> None:
        self._servers[server.name] = server

    def register_tool(
        self,
        identity: MCPToolIdentity,
        capability: Capability,
        allowed_agents: set[str] | frozenset[str],
        handler: Callable[[dict[str, Any]], dict[str, Any]],
        *,
        read_only: bool = True,
    ) -> None:
        if identity.server_name not in self._servers:
            raise ValueError(f"server is not registered: {identity.server_name}")
        if not allowed_agents:
            raise ValueError("a tool must have at least one allowed agent")
        self._tools[(identity.server_name, identity.tool_name)] = MCPToolRegistration(
            identity=identity,
            capability=capability,
            allowed_agents=frozenset(allowed_agents),
            handler=handler,
            read_only=read_only,
        )

    def resolve(self, identity: MCPToolIdentity) -> MCPToolRegistration:
        tool = self._tools.get((identity.server_name, identity.tool_name))
        if tool is None:
            raise MCPToolNotFoundError(
                f"unregistered MCP tool: {identity.server_name}/{identity.tool_name}"
            )
        return tool

    def tools(self) -> tuple[MCPToolRegistration, ...]:
        return tuple(self._tools.values())


def _renewal_read(payload: dict[str, Any]) -> dict[str, Any]:
    return {"kind": "renewal.read", "query": payload.get("query", "")}


def _health_read(payload: dict[str, Any]) -> dict[str, Any]:
    return {"kind": "health.read", "metric": payload.get("metric")}


def _market_read(payload: dict[str, Any]) -> dict[str, Any]:
    return {"kind": "market.read", "symbol": payload.get("symbol")}


def default_mcp_registry() -> MCPRegistry:
    registry = MCPRegistry()
    registry.register_server(MCPServerIdentity(name="personalos-safe-mock"))
    registry.register_tool(
        MCPToolIdentity(server_name="personalos-safe-mock", tool_name="renewal.read"),
        Capability.RENEWAL_READ,
        {AgentName.RENEWAL_SHORT.value},
        _renewal_read,
    )
    registry.register_tool(
        MCPToolIdentity(server_name="personalos-safe-mock", tool_name="health.read"),
        Capability.HEALTH_READ,
        {AgentName.HEALTH_SHORT.value},
        _health_read,
    )
    registry.register_tool(
        MCPToolIdentity(server_name="personalos-safe-mock", tool_name="market.read"),
        Capability.STOCK_READ,
        {AgentName.STOCK_ANALYSIS_SHORT.value},
        _market_read,
    )
    return registry


def register_document_search_tool(
    registry: MCPRegistry,
    handler: Callable[[dict[str, Any]], dict[str, Any]],
) -> None:
    """Register a read-only document retrieval handler supplied by the app."""
    registry.register_tool(
        MCPToolIdentity(server_name="personalos-safe-mock", tool_name="document.search"),
        Capability.DOCUMENT_READ,
        {AgentName.DOCUMENT.value},
        handler,
    )
