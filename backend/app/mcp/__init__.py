"""MCP integration boundary for explicitly registered, policy-approved tools."""

from .client import MCPClient
from .contracts import (
    MCPAuthorizationContext,
    MCPInvocationRequest,
    MCPInvocationResult,
    MCPServerIdentity,
    MCPToolIdentity,
    MCPToolRegistration,
)
from .registry import MCPRegistry, default_mcp_registry

__all__ = [
    "MCPAuthorizationContext",
    "MCPClient",
    "MCPInvocationRequest",
    "MCPInvocationResult",
    "MCPRegistry",
    "MCPServerIdentity",
    "MCPToolIdentity",
    "MCPToolRegistration",
    "default_mcp_registry",
]
