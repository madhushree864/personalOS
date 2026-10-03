from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MCPServerContext(BaseModel):
    """Context created by the policy-gated PersonalOS MCP client."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1, max_length=100)
    user_id: str = Field(min_length=1, max_length=100)
    agent: str = Field(min_length=1, max_length=100)
    capability: str = Field(min_length=1, max_length=100)
    policy_approved: Literal[True] = True
