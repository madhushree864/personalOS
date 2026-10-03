from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

from ..routing.contracts import AgentName, Capability
from ..routing.policy import PolicyDecision


class MCPServerIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    version: str = Field(default="0.1.0", min_length=1, max_length=30)


class MCPToolIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    server_name: str = Field(min_length=1, max_length=100)
    tool_name: str = Field(min_length=1, max_length=100)


class MCPToolRegistration(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    identity: MCPToolIdentity
    capability: Capability
    allowed_agents: frozenset[str] = Field(min_length=1)
    read_only: bool = True
    handler: Callable[[dict[str, Any]], dict[str, Any]]


class MCPInvocationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1, max_length=100)
    identity: MCPToolIdentity
    capability: Capability
    authenticated_user_id: str = Field(min_length=1, max_length=100)
    agent: AgentName
    input: dict[str, Any] = Field(default_factory=dict)


class MCPAuthorizationContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    user_id: str = Field(min_length=1, max_length=100)
    agent: AgentName
    policy_decision: PolicyDecision


class MCPInvocationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    server_name: str
    tool_name: str
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
