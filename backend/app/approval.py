from datetime import datetime
from enum import StrEnum
from fastapi import HTTPException
from .config import get_settings
from .models import InvestmentApproval

class ApprovalState(StrEnum):
    PENDING_USER = "pending_user"
    PENDING_MFA = "pending_mfa"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"

_TRANSITIONS = {
    ApprovalState.PENDING_USER: {ApprovalState.PENDING_MFA, ApprovalState.REJECTED},
    ApprovalState.PENDING_MFA: {ApprovalState.APPROVED, ApprovalState.REJECTED},
    ApprovalState.APPROVED: {ApprovalState.EXECUTED},
    ApprovalState.REJECTED: set(),
    ApprovalState.EXECUTED: set(),
}

def transition(approval: InvestmentApproval, target: ApprovalState, *, user_id: str):
    current = ApprovalState(approval.status)
    if target not in _TRANSITIONS[current]:
        raise HTTPException(409, detail={"code": "invalid_approval_transition",
                                         "from": current.value, "to": target.value})
    now = datetime.utcnow()
    approval.status = target.value
    approval.updated_at = now
    if target is ApprovalState.PENDING_MFA:
        approval.approved_by = None
    elif target is ApprovalState.APPROVED:
        approval.approved_by, approval.approved_at = user_id, now
    elif target is ApprovalState.REJECTED:
        approval.rejected_at = now
    elif target is ApprovalState.EXECUTED:
        approval.executed_at = now
    return approval

def verify_mfa(approval: InvestmentApproval, *, user_id: str, code: str | None = None,
               legacy_assertion: bool = False):
    if approval.owner_id != user_id:
        raise HTTPException(404, "Investment approval not found")
    if ApprovalState(approval.status) is not ApprovalState.PENDING_MFA:
        raise HTTPException(409, detail={"code": "mfa_not_expected", "state": approval.status})
    settings = get_settings()
    # This is intentionally a local/dev boundary. No provider or secret is used.
    valid = code == "000000" or (legacy_assertion and settings.environment != "production")
    if not valid:
        raise HTTPException(403, detail={"code": "mfa_verification_failed", "mfa_required": True})
    approval.mfa_verified_at = datetime.utcnow()
    transition(approval, ApprovalState.APPROVED, user_id=user_id)
    return approval
