from enum import Enum
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field


class AgentName(str, Enum):
    RENEWAL_SHORT = "renewal"
    HEALTH_SHORT = "health"
    STOCK_ANALYSIS_SHORT = "stock_analysis"
    INVESTMENT_SHORT = "investment"
    DOCUMENT = "document"
    SUPERVISOR = "Supervisor"
    RENEWAL = "Renewal Agent"
    HEALTH = "Health Agent"
    STOCK_ANALYSIS = "Stock Analysis Agent"
    INVESTMENT = "Investment Agent"


class Intent(str, Enum):
    RENEWAL_QUERY = "renewal_query"
    RENEWAL_MANAGEMENT = "renewal_management"
    HEALTH_QUERY = "health_query"
    HEALTH_ANALYSIS = "health_analysis"
    STOCK_ANALYSIS = "stock_analysis"
    PORTFOLIO_ANALYSIS = "portfolio_analysis"
    INVESTMENT_PROPOSAL = "investment_proposal"
    INVESTMENT_EXECUTION = "investment_execution"
    DOCUMENT_SEARCH = "document_search"
    GENERAL = "general"
    RENEWAL = "renewal_query"
    HEALTH = "health_query"
    INVESTMENT = "investment_proposal"


RouteWorkflow = Intent


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalType(str, Enum):
    NONE = "none"
    USER = "user"
    MFA = "mfa"
    USER_AND_MFA = "user_and_mfa"


class Capability(str, Enum):
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ANALYZE = "analyze"
    CONFIRM = "confirm"
    EXECUTE = "execute"
    DOCUMENT = "document"
    RENEWAL_CREATE = "renewal.create"
    RENEWAL_UPDATE = "renewal.update"
    RENEWAL_DELETE = "renewal.delete"
    RENEWAL_READ = "renewal.read"
    HEALTH_READ = "health.read"
    STOCK_READ = "stock.read"
    INVESTMENT_PROPOSE = "investment.propose"
    INVESTMENT_EXECUTE = "investment.execute"
    INVESTMENT_CONFIRM = "investment.confirm"
    DOCUMENT_READ = "document.read"
    AUDIT_READ = "audit.read"


class ApprovalStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    REQUIRED = "required"
    APPROVED = "approved"
    DENIED = "denied"


class RouteRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    query: str = Field(default="", max_length=2000)
    request_id: str = Field(default_factory=lambda: str(uuid4()))


class RoutingDecision(BaseModel):
    """Canonical, serializable decision exchanged by validator and policy."""
    model_config = ConfigDict(extra="forbid")
    request_id: str
    agent: AgentName
    intent: Intent
    target_agent: AgentName | None = None
    requested_action: str = "read"
    required_capabilities: list[Capability] = Field(default_factory=list)
    required_data_domains: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    confidence: float = Field(default=1.0, ge=0, le=1)
    reasoning_summary: str = ""
    constraints: list[str] = Field(default_factory=list)
    capability: Capability | None = None
    risk_level: RiskLevel = RiskLevel.LOW
    approval_type: ApprovalType = ApprovalType.NONE
    approval_status: ApprovalStatus = ApprovalStatus.NOT_REQUIRED
    requires_human_approval: bool = False
    policy_allowed: bool = False
    authenticated: bool = False
    active_user: bool = False
    ownership_verified: bool = False
    execution_authorized: bool = False
    reason: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class RouteResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    agent: str
    workflow: Intent
    requiresHumanApproval: bool
    response: str
    data: dict[str, Any] = Field(default_factory=dict)


RoutingIntent = Intent
RoutingRequest = RouteRequest
RoutingResponse = RouteResponse
