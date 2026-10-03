from datetime import date
from .models import HealthRecord, Renewal
from .models import InvestmentApproval, InvestmentProposal
from .repositories import Repository

TOKEN = "personalos-demo-token"
BROKER = {"status": "sandbox", "canExecute": False, "lastApprovedBy": None,
          "supported": ["AAPL", "MSFT", "NIFTY50", "RELIANCE", "HDFCBANK"]}


def serialize_renewal(item):
    return {"id": item.id, "name": item.name, "category": item.category,
            "dueDate": item.due_date.isoformat(), "reminderDays": item.reminder_days, "status": item.status}


def serialize_health(item):
    return {"id": item.id, "date": item.date.isoformat(), "metric": item.metric,
            "value": item.value, "unit": item.unit}


def serialize_proposal(item, approval=None):
    return {"id": item.id, "status": item.status, "symbol": item.symbol, "amount": item.amount,
            "riskLevel": item.risk_level, "broker": item.broker, "policyChecks": item.policy_checks,
            "requiresHumanApproval": item.requires_human_approval,
            "approval": {"status": approval.status, "mfaVerified": approval.mfa_verified_at is not None}
            if approval else None}


def create_proposal(repo, symbol, amount, risk_level):
    proposal = InvestmentProposal(owner_id=repo.owner_id, symbol=symbol, amount=amount, risk_level=risk_level, broker=dict(BROKER),
                                  policy_checks=["Sandbox mode enabled", "User review required", "Explicit approval before execution"])
    repo.db.add(proposal)
    repo.db.commit()
    repo.db.refresh(proposal)
    approval = InvestmentApproval(proposal_id=proposal.id, owner_id=repo.owner_id, requested_by=repo.owner_id)
    repo.db.add(approval)
    repo.db.commit()
    return proposal


def confirm_proposal(repo, proposal, approved, user_name):
    if not approved:
        proposal.status = "rejected"
        repo.db.commit()
        return proposal
    proposal.status = "sandbox_execute"
    proposal.approved_by = user_name
    proposal.broker = dict(BROKER, canExecute=True, lastApprovedBy=user_name)
    repo.db.commit()
    repo.db.refresh(proposal)
    return proposal


def route_request(query, repo: Repository):
    text = (query or "").lower()
    renewals = [serialize_renewal(x) for x in repo.renewals()]
    health = [serialize_health(x) for x in repo.health()]
    holdings = [{"symbol": x.symbol, "shares": x.shares, "price": x.price, "allocation": x.allocation} for x in repo.holdings()]
    if any(word in text for word in ("renew", "insurance", "subscription", "membership", "certificate", "expiry", "reminder")):
        return {"agent": "Renewal Agent", "workflow": "renewal", "requiresHumanApproval": False,
                "response": f"I found {len(renewals)} items that may need attention.", "data": {"renewals": renewals}}
    if any(word in text for word in ("health", "heart", "sleep", "steps", "medical", "exercise", "workout")):
        sleeps = [x["value"] for x in health if x["metric"] == "sleep"]
        steps = [x["value"] for x in health if x["metric"] == "steps"]
        return {"agent": "Health Agent", "workflow": "health", "requiresHumanApproval": False,
                "response": "Health data reviewed with privacy safeguards. Raw values are separated from the interpretation layer.",
                "data": {"rawData": health, "statisticalObservation": {"averageSleepHours": f"{sum(sleeps)/len(sleeps):.1f}" if sleeps else "0.0",
                "averageSteps": f"{sum(steps)/len(steps):.0f}" if steps else "0",
                "trend": "Sleep quality is stable and step count is trending above the weekly baseline."},
                "aiInterpretation": {"summary": "This is not a medical diagnosis and should be reviewed with a clinician.", "safetyNote": "AI interpretation is advisory only."}}}
        
    if any(word in text for word in ("buy", "sell", "trade", "invest", "money", "transfer", "withdraw")):
        return {"agent": "Investment Agent", "workflow": "investment", "requiresHumanApproval": True,
                "response": "Investment requests require a policy review and explicit user confirmation before any broker action can be simulated.",
                "data": {"proposal": {"action": "Buy ₹10,000 of HDFCBANK", "riskLevel": "Medium", "policyChecks": ["KYC status verified", "Exposure within sandbox limit", "User approval required"], "broker": BROKER}}}
    if any(word in text for word in ("stock", "portfolio", "company", "equity", "risk", "market", "analysis", "compare")):
        total = sum(x["shares"] * x["price"] for x in holdings)
        return {"agent": "Stock Analysis Agent", "workflow": "stock-analysis", "requiresHumanApproval": False,
                "response": "Portfolio analysis generated without execution rights. This workflow is read-only and does not authorize any buy or sell action.",
                "data": {"holdings": holdings, "totalValue": total, "risk": "Moderate", "summary": "The portfolio is diversified across technology and index exposure, with moderate concentration risk."}}
    return {"agent": "Supervisor", "workflow": "general", "requiresHumanApproval": False,
            "response": "I can help with renewals, health insights, stock analysis, or high-risk investment requests. Please tell me what you want to do.", "data": {}}
