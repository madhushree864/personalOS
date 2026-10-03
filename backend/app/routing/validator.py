from dataclasses import dataclass
from .contracts import AgentName, Intent, RoutingDecision


@dataclass(frozen=True)
class ValidationResult:
    workflow: Intent
    normalized_query: str
    request_id: str = ""


class RoutingValidator:
    def validate(self, query: str, request_id: str = "") -> ValidationResult:
        normalized = " ".join((query or "").strip().lower().split())
        if len(normalized) > 2000:
            raise ValueError("query exceeds 2000 characters")
        if any(token in normalized for token in ("document", "file", "pdf", "search document")):
            workflow = Intent.DOCUMENT_SEARCH
        elif any(token in normalized for token in ("renew", "insurance", "subscription", "membership", "certificate", "expiry", "reminder")):
            workflow = Intent.RENEWAL_QUERY
        elif any(token in normalized for token in ("health", "heart", "sleep", "steps", "medical", "exercise", "workout")):
            workflow = Intent.HEALTH_QUERY
        elif any(token in normalized for token in ("buy", "sell", "trade", "invest", "money", "transfer", "withdraw")):
            workflow = Intent.INVESTMENT_PROPOSAL
        elif any(token in normalized for token in ("portfolio",)):
            workflow = Intent.PORTFOLIO_ANALYSIS
        elif any(token in normalized for token in ("stock", "company", "equity", "risk", "market", "analysis", "compare")):
            workflow = Intent.STOCK_ANALYSIS
        else:
            workflow = Intent.GENERAL
        return ValidationResult(workflow, normalized, request_id)

    def validate_decision(self, decision: RoutingDecision) -> RoutingDecision:
        expected = {
            Intent.GENERAL: AgentName.SUPERVISOR,
            Intent.RENEWAL_QUERY: AgentName.RENEWAL_SHORT,
            Intent.RENEWAL_MANAGEMENT: AgentName.RENEWAL_SHORT,
            Intent.HEALTH_QUERY: AgentName.HEALTH_SHORT,
            Intent.HEALTH_ANALYSIS: AgentName.HEALTH_SHORT,
            Intent.STOCK_ANALYSIS: AgentName.STOCK_ANALYSIS,
            Intent.PORTFOLIO_ANALYSIS: AgentName.STOCK_ANALYSIS_SHORT,
            Intent.INVESTMENT_PROPOSAL: AgentName.INVESTMENT_SHORT,
            Intent.INVESTMENT_EXECUTION: AgentName.INVESTMENT_SHORT,
            Intent.DOCUMENT_SEARCH: AgentName.DOCUMENT,
        }[decision.intent]
        if decision.agent is not expected:
            raise ValueError("agent does not match intent")
        if decision.requires_human_approval != (decision.approval_status is not None and decision.approval_status.value == "required"):
            raise ValueError("approval flag does not match approval status")
        if decision.execution_authorized and (not decision.policy_allowed or not decision.ownership_verified):
            raise ValueError("execution cannot bypass policy or ownership")
        return decision
