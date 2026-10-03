from dataclasses import dataclass
from .contracts import ApprovalStatus, ApprovalType, Capability, Intent, RiskLevel, RoutingDecision, AgentName
from .capabilities import CapabilityRegistry, default_capability_registry


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    approval: ApprovalStatus
    reason: str
    capability: Capability | None = None
    decision: RoutingDecision | None = None


class PolicyEngine:
    """Deterministic policy boundary. No role/admin bypass is applied."""
    def __init__(self, registry: CapabilityRegistry | None = None):
        self.registry = registry or default_capability_registry()

    def evaluate(self, workflow: Intent, user_capabilities: set[str] | None = None,
                 approved: bool = False, *, user=None, ownership_verified: bool = True,
                 authenticated: bool | None = None, active: bool | None = None,
                 mfa_verified: bool = False, request_id: str = "policy-request") -> PolicyDecision:
        caps = user_capabilities or set()
        definition = self.registry.get(Intent(workflow))
        required = sorted(definition.required, key=lambda c: c.value)[0] if definition.required else None
        # The capability-only form remains available for pure policy unit tests;
        # request paths always provide the authenticated principal explicitly.
        is_authenticated = (bool(user_capabilities) if user is None else True) if authenticated is None else authenticated
        is_active = (True if user is None else getattr(user, "is_active", False)) if active is None else active
        if not is_authenticated:
            return self._deny(request_id, definition, required, "authenticated user is required", is_authenticated, is_active, ownership_verified)
        if not is_active:
            return self._deny(request_id, definition, required, "user is inactive", is_authenticated, is_active, ownership_verified)
        if not ownership_verified:
            return self._deny(request_id, definition, required, "resource ownership is not verified", is_authenticated, is_active, ownership_verified)
        if required and required.value not in caps:
            return self._deny(request_id, definition, required, "required capability is missing", is_authenticated, is_active, ownership_verified)
        if definition.execution and (not approved or not mfa_verified):
            return self._deny(request_id, definition, required, "investment execution requires explicit approval and MFA", is_authenticated, is_active, ownership_verified)
        approval = ApprovalStatus.NOT_REQUIRED if definition.approval is ApprovalType.NONE else (ApprovalStatus.APPROVED if approved else ApprovalStatus.REQUIRED)
        # Routing/proposal is permitted, while execution remains blocked until
        # the required approval factors are present.
        allowed = True
        reason = "policy permitted; explicit approval and MFA are required before execution" if approval is ApprovalStatus.REQUIRED else "policy permitted"
        decision = RoutingDecision(request_id=request_id, agent=AgentName(definition.agent), target_agent=AgentName(definition.agent), intent=definition.intent,
            capability=required, risk_level=definition.risk, approval_type=definition.approval,
            approval_status=approval, requires_human_approval=approval is ApprovalStatus.REQUIRED, policy_allowed=True,
            authenticated=is_authenticated, active_user=is_active, ownership_verified=ownership_verified,
            execution_authorized=definition.execution, required_capabilities=list(definition.required),
            required_data_domains=[definition.intent.value], requires_approval=definition.approval is not ApprovalType.NONE,
            requested_action="execute" if definition.execution else "read", reasoning_summary=reason,
            constraints=["ownership_required"] if definition.ownership_required else [])
        return PolicyDecision(allowed, approval, reason, required, decision)

    def _deny(self, request_id, definition, required, reason, authenticated, active, owned):
        decision = RoutingDecision(request_id=request_id, agent=AgentName(definition.agent), target_agent=AgentName(definition.agent), intent=definition.intent,
            capability=required, risk_level=definition.risk, approval_type=definition.approval,
            approval_status=ApprovalStatus.DENIED, requires_human_approval=False, policy_allowed=False,
            authenticated=authenticated, active_user=active, ownership_verified=owned, reason=reason,
            required_capabilities=list(definition.required), required_data_domains=[definition.intent.value],
            requires_approval=definition.approval is not ApprovalType.NONE,
            requested_action="execute" if definition.execution else "read", reasoning_summary=reason)
        return PolicyDecision(False, ApprovalStatus.DENIED, reason, required, decision)
