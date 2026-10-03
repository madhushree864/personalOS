from .contracts import RouteWorkflow
from .policy import PolicyEngine
from .validator import RoutingValidator
from ..services import route_request


class SupervisorRoutingService:
    def __init__(self, validator=None, policy=None):
        self.validator = validator or RoutingValidator()
        self.policy = policy or PolicyEngine()

    def route(self, query: str, repo, user) -> dict:
        import uuid
        request_id = str(uuid.uuid4())
        validated = self.validator.validate(query, request_id)
        decision = self.policy.evaluate(validated.workflow, set(user.permissions or []),
                                         user=user, ownership_verified=bool(repo.owner_id),
                                         request_id=request_id)
        if not decision.allowed:
            raise PermissionError(decision.reason)
        result = route_request(validated.normalized_query, repo)
        typed = self.validator.validate_decision(decision.decision)
        # Preserve the legacy response contract while exposing deterministic policy metadata.
        result["policy"] = {"allowed": decision.allowed, "approval": decision.approval.value,
                            "reason": decision.reason, "request_id": request_id,
                            "risk_level": typed.risk_level.value,
                            "approval_type": typed.approval_type.value}
        result["request_id"] = request_id
        result["routing_decision"] = typed.model_dump(mode="json")
        return result
