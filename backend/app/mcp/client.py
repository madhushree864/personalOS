from .contracts import (
    MCPAuthorizationContext,
    MCPInvocationRequest,
    MCPInvocationResult,
)
from .errors import MCPAuthorizationError, MCPToolExecutionError
from .registry import MCPRegistry, default_mcp_registry


class MCPClient:
    """Invokes registered tools only after the existing Policy Engine approves."""

    def __init__(self, registry: MCPRegistry | None = None, transport=None):
        self.registry = registry or default_mcp_registry()
        self.transport = transport

    def invoke(
        self,
        request: MCPInvocationRequest,
        authorization: MCPAuthorizationContext,
    ) -> MCPInvocationResult:
        tool = self.registry.resolve(request.identity)
        decision = authorization.policy_decision
        if not decision.allowed or decision.decision is None:
            raise MCPAuthorizationError("an allowed Policy Engine decision is required")
        if not (
            decision.decision.authenticated
            and decision.decision.active_user
            and decision.decision.ownership_verified
        ):
            raise MCPAuthorizationError(
                "Policy Engine did not approve an authenticated, active, owned context"
            )
        if request.authenticated_user_id != authorization.user_id:
            raise MCPAuthorizationError("request identity does not match authorization context")
        if authorization.agent.value != decision.decision.agent.value:
            raise MCPAuthorizationError("authorization agent does not match the policy decision")
        if request.agent != authorization.agent or request.agent.value not in tool.allowed_agents:
            raise MCPAuthorizationError("agent is not authorized for this MCP tool")
        if request.capability is not tool.capability:
            raise MCPAuthorizationError("requested capability does not match the registered tool")
        if tool.capability not in decision.decision.required_capabilities:
            raise MCPAuthorizationError("Policy Engine did not approve this capability")
        if not decision.decision.policy_allowed:
            raise MCPAuthorizationError("Policy Engine decision is not approved")
        if not tool.read_only:
            raise MCPAuthorizationError("non-read-only tools are not allowed on this MCP boundary")
        try:
            if (
                self.transport is not None
                and request.identity.server_name == "personalos-safe-mock"
                and request.identity.tool_name in {"renewal.read", "health.read"}
            ):
                data = self.transport.invoke(request, authorization)
            else:
                tool_input = dict(request.input)
                tool_input["authenticated_user_id"] = authorization.user_id
                data = tool.handler(tool_input)
        except Exception as exc:
            if isinstance(exc, MCPToolExecutionError):
                raise
            raise MCPToolExecutionError("registered MCP tool failed") from exc
        return MCPInvocationResult(
            request_id=request.request_id,
            server_name=request.identity.server_name,
            tool_name=request.identity.tool_name,
            success=True,
            data=data,
        )
