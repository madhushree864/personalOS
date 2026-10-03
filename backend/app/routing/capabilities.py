from dataclasses import dataclass
from .contracts import Capability, Intent, RiskLevel, ApprovalType


@dataclass(frozen=True)
class CapabilityDefinition:
    intent: Intent
    agent: str
    required: frozenset[Capability]
    risk: RiskLevel
    approval: ApprovalType
    execution: bool = False
    description: str = ""
    allowed_agent: str | None = None
    required_permission: str | None = None
    requires_mfa: bool = False
    read_only: bool = True
    ownership_required: bool = True

    @property
    def capabilities(self):
        return self.required


class CapabilityRegistry:
    def __init__(self, definitions: dict[Intent, CapabilityDefinition]):
        self._definitions = dict(definitions)

    def get(self, intent: Intent) -> CapabilityDefinition:
        return self._definitions[intent]

    def supports(self, intent: Intent, capability: Capability) -> bool:
        return capability in self.get(intent).required

    def workflows(self):
        return tuple(self._definitions)

    def definitions(self):
        return dict(self._definitions)

    @classmethod
    def default(cls):
        return default_capability_registry()


def default_capability_registry():
    return CapabilityRegistry({
        Intent.GENERAL: CapabilityDefinition(Intent.GENERAL, "Supervisor", frozenset(), RiskLevel.LOW, ApprovalType.NONE, description="Help and clarification", ownership_required=False),
        Intent.RENEWAL_QUERY: CapabilityDefinition(Intent.RENEWAL_QUERY, "renewal", frozenset({Capability.RENEWAL_READ}), RiskLevel.LOW, ApprovalType.NONE, description="Read owned renewals", allowed_agent="renewal", required_permission=Capability.RENEWAL_READ.value),
        Intent.RENEWAL_MANAGEMENT: CapabilityDefinition(Intent.RENEWAL_MANAGEMENT, "renewal", frozenset({Capability.RENEWAL_UPDATE}), RiskLevel.MEDIUM, ApprovalType.USER, execution=False, read_only=False, description="Manage owned renewals", allowed_agent="renewal", required_permission=Capability.RENEWAL_UPDATE.value),
        Intent.HEALTH_QUERY: CapabilityDefinition(Intent.HEALTH_QUERY, "health", frozenset({Capability.HEALTH_READ}), RiskLevel.MEDIUM, ApprovalType.NONE, description="Read owned health records", allowed_agent="health", required_permission=Capability.HEALTH_READ.value),
        Intent.HEALTH_ANALYSIS: CapabilityDefinition(Intent.HEALTH_ANALYSIS, "health", frozenset({Capability.HEALTH_READ}), RiskLevel.MEDIUM, ApprovalType.NONE, description="Analyze owned health records", allowed_agent="health", required_permission=Capability.HEALTH_READ.value),
        Intent.STOCK_ANALYSIS: CapabilityDefinition(Intent.STOCK_ANALYSIS, "stock_analysis", frozenset({Capability.STOCK_READ}), RiskLevel.MEDIUM, ApprovalType.NONE, description="Read-only portfolio analysis", allowed_agent="stock_analysis", required_permission=Capability.STOCK_READ.value),
        Intent.PORTFOLIO_ANALYSIS: CapabilityDefinition(Intent.PORTFOLIO_ANALYSIS, "stock_analysis", frozenset({Capability.STOCK_READ}), RiskLevel.MEDIUM, ApprovalType.NONE, description="Read-only portfolio analysis", allowed_agent="stock_analysis", required_permission=Capability.STOCK_READ.value),
        Intent.INVESTMENT_PROPOSAL: CapabilityDefinition(Intent.INVESTMENT_PROPOSAL, "investment", frozenset({Capability.INVESTMENT_PROPOSE}), RiskLevel.HIGH, ApprovalType.USER, execution=False, description="Proposal only", allowed_agent="investment", required_permission=Capability.INVESTMENT_PROPOSE.value),
        Intent.INVESTMENT_EXECUTION: CapabilityDefinition(Intent.INVESTMENT_EXECUTION, "investment", frozenset({Capability.INVESTMENT_EXECUTE}), RiskLevel.CRITICAL, ApprovalType.USER_AND_MFA, execution=True, read_only=False, description="Gated sandbox execution", allowed_agent="investment", required_permission=Capability.INVESTMENT_EXECUTE.value, requires_mfa=True),
        Intent.DOCUMENT_SEARCH: CapabilityDefinition(Intent.DOCUMENT_SEARCH, "document", frozenset({Capability.DOCUMENT_READ}), RiskLevel.LOW, ApprovalType.NONE, description="Search owned documents", allowed_agent="document", required_permission=Capability.DOCUMENT_READ.value),
    })
