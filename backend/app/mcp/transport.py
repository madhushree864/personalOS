import asyncio
import json

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from .contracts import (
    HealthReadResponse,
    MCPAuthorizationContext,
    MCPInvocationRequest,
    RenewalReadResponse,
)
from .errors import MCPToolExecutionError


class _TrustedMCPContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1, max_length=100)
    user_id: str = Field(min_length=1, max_length=100)
    agent: str = Field(min_length=1, max_length=100)
    capability: str = Field(min_length=1, max_length=100)
    policy_approved: Literal[True] = True


class RenewalMCPTransport:
    """Local MCP protocol transport for the renewal server only."""

    def __init__(self, adapter):
        self.server = MCPServer(
            name="personalos-renewal",
            version="0.1.0",
            instructions="Read-only owner-scoped renewal data.",
        )

        @self.server.tool(
            name="renewal.read",
            description="Read owner-scoped renewal information.",
        )
        def renewal_read(query: str, context: _TrustedMCPContext) -> dict:
            return adapter.read(query, context)

    def invoke(
        self,
        request: MCPInvocationRequest,
        authorization: MCPAuthorizationContext,
    ) -> dict:
        context = _TrustedMCPContext(
            request_id=request.request_id,
            user_id=authorization.user_id,
            agent=authorization.agent.value,
            capability=request.capability.value,
        )
        try:
            result = asyncio.run(
                self.server.call_tool(
                    request.identity.tool_name,
                    {"query": str(request.input.get("query", "")), "context": context},
                )
            )
            if result.is_error or not result.content:
                raise MCPToolExecutionError("renewal MCP server returned an error")
            payload = json.loads(result.content[0].text)
            return RenewalReadResponse.model_validate(payload).model_dump(mode="json")
        except MCPToolExecutionError:
            raise
        except Exception as exc:
            raise MCPToolExecutionError("renewal MCP transport failed") from exc


class HealthMCPTransport:
    """Local MCP protocol transport for the health server only."""

    def __init__(self, adapter):
        self.server = MCPServer(
            name="personalos-health",
            version="0.1.0",
            instructions="Read-only owner-scoped health data.",
        )

        @self.server.tool(
            name="health.read",
            description="Read owner-scoped health records.",
        )
        def health_read(metric: str, context: _TrustedMCPContext) -> dict:
            return adapter.read(metric, context)

    def invoke(
        self,
        request: MCPInvocationRequest,
        authorization: MCPAuthorizationContext,
    ) -> dict:
        context = _TrustedMCPContext(
            request_id=request.request_id,
            user_id=authorization.user_id,
            agent=authorization.agent.value,
            capability=request.capability.value,
        )
        try:
            result = asyncio.run(
                self.server.call_tool(
                    request.identity.tool_name,
                    {
                        "metric": str(request.input.get("metric", "")),
                        "context": context,
                    },
                )
            )
            if result.is_error or not result.content:
                raise MCPToolExecutionError("health MCP server returned an error")
            payload = json.loads(result.content[0].text)
            return HealthReadResponse.model_validate(payload).model_dump(mode="json")
        except MCPToolExecutionError:
            raise
        except Exception as exc:
            raise MCPToolExecutionError("health MCP transport failed") from exc
