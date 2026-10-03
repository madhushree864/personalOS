from datetime import date
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .config import get_settings
from .db import Base, engine, get_db
from .models import HealthRecord, Renewal
from .repositories import Repository
from .schemas import *
from .seed import seed
from .auth import current_user, create_access_token, verify_password, require_permission, revoke_token
from .services import confirm_proposal, create_proposal, route_request, serialize_health, serialize_proposal, serialize_renewal
from .models import InvestmentApproval
from .approval import ApprovalState, transition, verify_mfa
from .routing.supervisor import SupervisorRoutingService
from .routing.broker import MockBrokerGateway
from .routing.audit import AuditEvent
from .routing.contracts import Intent

settings=get_settings(); app=FastAPI(title="PersonalOS API",version="3.0.0")
supervisor_service = SupervisorRoutingService()
broker_gateway = MockBrokerGateway()
app.add_middleware(CORSMiddleware,allow_origins=settings.origins or ["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
Base.metadata.create_all(engine)
if settings.seed_demo_data: seed()
@app.on_event("startup")
def startup(): Base.metadata.create_all(engine); seed() if settings.seed_demo_data else None
def repo(db,user): return Repository(db,user.id if user else None)
def audit(db,user,event,details=None): Repository(db,user.id if user else None).log(event,details)
def public_user(u): return {"id":u.id,"name":u.name,"email":u.email,"role":u.role,"permissions":u.permissions or []}
@app.get("/api/healthz")
def healthz(): return {"status":"ok","service":settings.app_name}
@app.post("/api/auth/login")
def login(payload:LoginRequest,db:Session=Depends(get_db)):
    u=Repository(db).user(payload.email)
    if not u or not verify_password(payload.password,u.password_hash): audit(db,None,"login-failed",{"email":payload.email}); raise HTTPException(401,"Invalid credentials")
    audit(db,u,"login",{"email":u.email,"success":True}); return {"token":create_access_token(u),"user":public_user(u)}
@app.get("/api/auth/me")
def me(user=Depends(current_user)): return {"user":public_user(user)}
@app.post("/api/auth/logout")
def logout(request: Request, db: Session = Depends(get_db), user=Depends(current_user)):
    revoke_token(request, db, user)
    audit(db, user, "logout")
    return {"success": True}
@app.get("/api/renewals")
def list_renewals(db=Depends(get_db),user=Depends(require_permission("renewal.read"))):
    audit(db,user,"renewals-read"); return {"renewals":[serialize_renewal(x) for x in repo(db,user).renewals()]}
@app.post("/api/renewals",status_code=201)
def create_renewal(p:RenewalCreate,db=Depends(get_db),user=Depends(require_permission("renewal.create"))):
    x=Renewal(owner_id=user.id,name=p.name,category=p.category,due_date=p.dueDate,reminder_days=p.reminderDays,status="upcoming"); db.add(x); db.commit(); db.refresh(x); audit(db,user,"renewal-created"); return {"item":serialize_renewal(x)}
@app.put("/api/renewals/{item_id}")
def update_renewal(item_id,p:RenewalUpdate,db=Depends(get_db),user=Depends(require_permission("renewal.update"))):
    x=db.get(Renewal,item_id)
    if not x or x.owner_id != user.id: raise HTTPException(404,"Renewal not found")
    for k,v in p.model_dump(exclude_unset=True).items(): setattr(x,{"dueDate":"due_date","reminderDays":"reminder_days"}.get(k,k),v)
    x.owner_id=user.id; db.commit(); return {"renewal":serialize_renewal(x)}
@app.delete("/api/renewals/{item_id}")
def delete_renewal(item_id,db=Depends(get_db),user=Depends(require_permission("renewal.delete"))):
    x=db.get(Renewal,item_id)
    if not x or x.owner_id != user.id: raise HTTPException(404,"Renewal not found")
    result=serialize_renewal(x); db.delete(x); db.commit(); audit(db,user,"renewal-deleted"); return {"deleted":result}
@app.get("/api/health")
def list_health(db=Depends(get_db),user=Depends(require_permission("health.read"))): return {"records":[serialize_health(x) for x in repo(db,user).health()]}
@app.post("/api/health",status_code=201)
def create_health(p:HealthCreate,db=Depends(get_db),user=Depends(require_permission("health.create"))):
    x=HealthRecord(owner_id=user.id,date=p.date or date.today(),metric=p.metric,value=p.value,unit=p.unit); db.add(x); db.commit(); db.refresh(x); return {"record":serialize_health(x)}
@app.post("/api/health/insights")
def health_insights(db=Depends(get_db),user=Depends(require_permission("health.read"))):
    records=[serialize_health(x) for x in repo(db,user).health()]; sleeps=[x["value"] for x in records if x["metric"]=="sleep"]; audit(db,user,"health-insight-generated")
    return {"sensitive":True,"rawData":records,"statisticalObservation":{"averageSleepHours":f"{sum(sleeps)/len(sleeps):.1f}" if sleeps else "0.0"},"aiInterpretation":{"summary":"The observed pattern is an observational summary only.","caution":"Do not treat these results as a diagnosis."}}
@app.get("/api/stock/summary")
def stock_summary(db=Depends(get_db),user=Depends(require_permission("stock.read"))):
    h=[{"symbol":x.symbol,"shares":x.shares,"price":x.price,"allocation":x.allocation} for x in repo(db,user).holdings()]; return {"portfolio":h,"totalValue":sum(x["shares"]*x["price"] for x in h),"risk":"Moderate"}
@app.post("/api/stock/analyze")
def stock_analyze(p:RouteRequest,db=Depends(get_db),user=Depends(require_permission("stock.analyze"))): return route_request(p.query or "portfolio",repo(db,user))
@app.post("/api/investment/propose")
def investment_propose(p:InvestmentProposalRequest,db=Depends(get_db),user=Depends(require_permission("investment.propose"))):
    x=create_proposal(repo(db,user),p.symbol,p.amount,p.riskLevel); audit(db,user,"investment-proposal"); return {"proposal":serialize_proposal(x)}

@app.post("/api/investment/{proposal_id}/mfa/verify")
def investment_mfa(proposal_id: str, p: InvestmentMFARequest, db=Depends(get_db),
                   user=Depends(require_permission("investment.confirm"))):
    r = repo(db, user); x = r.proposal(proposal_id); approval = r.approval(proposal_id)
    if not x or not approval:
        raise HTTPException(404, "Investment proposal not found")
    try:
        verify_mfa(approval, user_id=user.id, code=p.code)
    except HTTPException as exc:
        audit(db, user, "investment-mfa-failed",
              {"proposalId": proposal_id, "reason": exc.detail, "provider": "mock-dev"})
        raise
    db.commit()
    audit(db, user, "investment-mfa-verified", {"proposalId": proposal_id, "provider": "mock-dev"})
    return {"proposal": serialize_proposal(x, approval)}

@app.post("/api/investment/confirm")
def investment_confirm(p:InvestmentConfirmRequest,db=Depends(get_db),user=Depends(require_permission("investment.confirm"))):
    r=repo(db,user); x=r.proposal(p.proposalId) if p.proposalId else None
    if not x:
        if not p.symbol or p.amount is None: raise HTTPException(404,"Investment proposal not found")
        x=create_proposal(r,p.symbol,p.amount,"Medium")
    approval = r.approval(x.id)
    if not approval:
        approval = InvestmentApproval(proposal_id=x.id, owner_id=user.id, requested_by=user.id)
        db.add(approval); db.flush()
    if p.approved:
        if ApprovalState(approval.status) is ApprovalState.PENDING_USER:
            transition(approval, ApprovalState.PENDING_MFA, user_id=user.id)
        # mfa_code is the preferred explicit boundary; mfa_verified preserves
        # the development-only legacy API contract.
        if ApprovalState(approval.status) is ApprovalState.PENDING_MFA and not p.mfa_code and not p.mfa_verified:
            db.commit()
            audit(db, user, "investment-approval-awaiting-mfa",
                  {"proposalId": x.id, "state": approval.status})
            raise HTTPException(status_code=403, detail={
                "code": "investment_execution_denied",
                "reason": "MFA verification is required",
                "mfa_required": True})
        if ApprovalState(approval.status) is ApprovalState.PENDING_MFA:
            try:
                verify_mfa(approval, user_id=user.id, code=p.mfa_code,
                           legacy_assertion=p.mfa_verified)
            except HTTPException as exc:
                audit(db, user, "investment-mfa-failed",
                      {"proposalId": x.id, "reason": exc.detail, "provider": "mock-dev"})
                raise
        # Confirmation is a policy boundary. The gateway is called only after
        # the proposal has been explicitly approved and policy checks passed.
        decision = supervisor_service.policy.evaluate(
            Intent.INVESTMENT_EXECUTION, set(user.permissions or []), approved=True,
            mfa_verified=approval.mfa_verified_at is not None, user=user, ownership_verified=True,
            request_id=f"investment-confirmation:{x.id}")
        if not decision.allowed or approval.mfa_verified_at is None:
            audit(db, user, "investment-execution-denied", {
                "proposalId": x.id, "reason": decision.reason,
                "mfa_verified": approval.mfa_verified_at is not None})
            raise HTTPException(status_code=403, detail={
                "code": "investment_execution_denied",
                "reason": decision.reason,
                "mfa_required": True,
                "request_id": decision.decision.request_id if decision.decision else None,
            })
        broker_gateway.execute({"symbol": x.symbol, "amount": x.amount},
                              policy=decision.decision, approved=True,
                              mfa_verified=approval.mfa_verified_at is not None)
        transition(approval, ApprovalState.EXECUTED, user_id=user.id)
        db.commit()
    else:
        transition(approval, ApprovalState.REJECTED, user_id=user.id)
        db.commit()
    result = serialize_proposal(confirm_proposal(r,x,p.approved,user.name), approval)
    audit(db, user, "investment-confirmation", AuditEvent.create(
        "investment-confirmation", user.id,
        {"proposalId": x.id, "approved": p.approved}).details)
    if not p.approved: return {"status":"rejected","message":"Execution not approved by user."}
    return {"status":"sandbox_execute","broker":result["broker"],"message":"Mock broker request is ready for execution in sandbox mode after MFA and audit verification."}
@app.post("/api/supervisor/route")
def supervisor(p:RouteRequest,db=Depends(get_db),user=Depends(require_permission("supervisor.route"))):
    try:
        result=supervisor_service.route(p.query,repo(db,user),user)
    except ValueError as exc:
        audit(db, user, "supervisor-validation-failed",
              {"query": p.query, "reason": str(exc)})
        raise HTTPException(422, str(exc))
    except PermissionError as exc:
        audit(db, user, "supervisor-policy-denied",
              {"query": p.query, "reason": str(exc)})
        raise HTTPException(403, str(exc))
    audit(db,user,"supervisor-routed",{"query":p.query,"agent":result["agent"],
                                        "workflow": result.get("workflow"),
                                        "policy": result.get("policy")})
    return result
@app.get("/api/audit-log")
def audit_log(db=Depends(get_db),user=Depends(require_permission("audit.read"))):
    return {"entries":[{"id":x.id,"timestamp":x.timestamp.isoformat(),"event":x.event,"details":x.details} for x in repo(db,user).audit()]}
