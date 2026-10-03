from dataclasses import dataclass
from typing import Any
from .contracts import RoutingDecision, ApprovalStatus, ApprovalType


@dataclass(frozen=True)
class BrokerResult:
    status: str
    executed: bool
    reference: str | None = None


class BrokerGateway:
    def execute(self, order: dict[str, Any], *, policy: RoutingDecision | None = None,
                approved: bool = False, mfa_verified: bool = False,
                policy_allowed: bool | None = None) -> BrokerResult:
        if policy is not None:
            if not policy.policy_allowed or not policy.ownership_verified:
                raise PermissionError("broker execution requires an allowed policy and ownership")
            if policy.approval_type is ApprovalType.USER_AND_MFA and (not approved or not mfa_verified):
                raise PermissionError("broker execution requires explicit approval and MFA")
            if policy.approval_status is not ApprovalStatus.APPROVED:
                raise PermissionError("broker execution requires an approved policy decision")
        elif policy_allowed is not True or not approved:
            raise PermissionError("broker execution requires an allowed policy decision and explicit approval")
        return BrokerResult("sandbox_executed", True, "mock-" + str(order.get("symbol", "order")))


class MockBrokerGateway(BrokerGateway):
    """Safe broker boundary: no network calls and no real-money capability."""
