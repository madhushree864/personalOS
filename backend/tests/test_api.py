import os
from datetime import datetime, timedelta, timezone

os.environ["DATABASE_URL"] = "sqlite:///./test_personalos.db"
os.environ["SEED_DEMO_DATA"] = "true"
os.environ["DEMO_PASSWORD"] = "test-demo-password"

from fastapi.testclient import TestClient
from jose import jwt
from app.auth import hash_password
from app.config import get_settings
from app.db import SessionLocal
from app.main import app
from app.models import AuditEntry, User

client = TestClient(app)


def login(email="demo@personalos.ai", password="test-demo-password"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()


def auth(token=None):
    return {"Authorization": f"Bearer {token or login()['token']}"}


def add_second_user():
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email="other@personalos.ai").first()
        if not user:
            user = User(id="user-002", name="Other User", email="other@personalos.ai",
                        password_hash=hash_password("other-password"), permissions=[
                            "renewal.read", "renewal.create", "renewal.update",
                            "renewal.delete", "audit.read", "supervisor.route"])
            db.add(user)
            db.commit()
    finally:
        db.close()


def test_login_and_compatible_endpoints():
    response = login()
    assert response["user"]["email"] == "demo@personalos.ai"
    assert "password" not in response["user"]
    assert "password_hash" not in response["user"]
    assert response["token"] != "******"
    assert client.get("/api/renewals", headers=auth(response["token"])).json()["renewals"]
    assert client.get("/api/stock/summary", headers=auth(response["token"])).json()["portfolio"]


def test_route_and_audit_are_persistent():
    token = login()["token"]
    result = client.post("/api/supervisor/route", headers=auth(token), json={"query": "buy HDFCBANK"})
    assert result.json()["requiresHumanApproval"] is True
    assert any(item["event"] == "supervisor-routed" for item in client.get("/api/audit-log", headers=auth(token)).json()["entries"])


def test_authentication_required():
    assert client.get("/api/renewals").status_code == 401


def test_investment_proposal_persists_and_validates():
    token = login()["token"]
    response = client.post("/api/investment/propose", headers=auth(token),
                           json={"symbol": "HDFCBANK", "amount": 10000, "riskLevel": "Medium"})
    assert response.status_code == 200
    proposal = response.json()["proposal"]
    assert proposal["id"]
    assert client.post("/api/investment/propose", headers=auth(token),
                       json={"symbol": "HDFCBANK", "amount": -1}).status_code == 422
    denied = client.post("/api/investment/confirm", headers=auth(token),
                         json={"proposalId": proposal["id"], "approved": True})
    assert denied.status_code == 403
    assert denied.json()["detail"]["mfa_required"] is True
    confirmed = client.post("/api/investment/confirm", headers=auth(token),
                            json={"proposalId": proposal["id"], "approved": True, "mfa_verified": True})
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "sandbox_execute"


def test_approval_state_and_mock_mfa_are_persistent():
    token = login()["token"]
    proposal = client.post("/api/investment/propose", headers=auth(token),
                           json={"symbol": "AAPL", "amount": 25}).json()["proposal"]
    waiting = client.post("/api/investment/confirm", headers=auth(token),
                          json={"proposalId": proposal["id"], "approved": True})
    assert waiting.status_code == 403
    assert waiting.json()["detail"]["mfa_required"] is True
    verified = client.post(f"/api/investment/{proposal['id']}/mfa/verify",
                           headers=auth(token), json={"code": "000000"})
    assert verified.status_code == 200
    assert verified.json()["proposal"]["approval"]["status"] == "approved"
    executed = client.post("/api/investment/confirm", headers=auth(token),
                           json={"proposalId": proposal["id"], "approved": True})
    assert executed.status_code == 200


def test_wrong_password_and_invalid_token_are_audited():
    assert client.post("/api/auth/login", json={"email": "demo@personalos.ai", "password": "wrong-password"}).status_code == 401
    assert client.get("/api/renewals", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401
    db = SessionLocal()
    try:
        events = [x.event for x in db.query(AuditEntry).order_by(AuditEntry.timestamp.desc()).limit(30)]
        assert "login-failed" in events
        assert "authentication-failed" in events
    finally:
        db.close()


def test_expired_jwt_is_rejected_and_audited():
    settings = get_settings()
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": "user-001", "jti": "expired-test-token", "iat": now - timedelta(minutes=2),
                        "exp": now - timedelta(minutes=1)}, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 401
    db = SessionLocal()
    try:
        assert db.query(AuditEntry).filter_by(event="authentication-failed").first()
    finally:
        db.close()


def test_logout_revokes_jwt():
    token = login()["token"]
    assert client.post("/api/auth/logout", headers=auth(token)).status_code == 200
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 401


def test_permission_denied_is_granular_and_audited():
    db = SessionLocal()
    try:
        if not db.query(User).filter_by(email="limited@personalos.ai").first():
            db.add(User(id="user-limited", name="Limited", email="limited@personalos.ai",
                        password_hash=hash_password("limited-password"), permissions=["renewal.read"]))
            db.commit()
    finally:
        db.close()
    token = login("limited@personalos.ai", "limited-password")["token"]
    assert client.get("/api/renewals", headers=auth(token)).status_code == 200
    assert client.post("/api/renewals", headers=auth(token), json={"name": "Denied", "dueDate": "2026-12-01"}).status_code == 403
    assert client.post("/api/investment/confirm", headers=auth(token), json={"approved": True, "symbol": "AAPL", "amount": 10}).status_code == 403
    assert client.post("/api/health", headers=auth(token), json={"metric": "sleep", "value": 7}).status_code == 403
    assert client.post("/api/health/insights", headers=auth(token)).status_code == 403
    assert client.get("/api/stock/summary", headers=auth(token)).status_code == 403
    assert client.post("/api/stock/analyze", headers=auth(token), json={"query": "portfolio"}).status_code == 403
    assert client.post("/api/investment/propose", headers=auth(token), json={"symbol": "AAPL", "amount": 10}).status_code == 403
    assert client.post("/api/supervisor/route", headers=auth(token), json={"query": "renewals"}).status_code == 403
    assert client.get("/api/audit-log", headers=auth(token)).status_code == 403
    db = SessionLocal()
    try:
        assert db.query(AuditEntry).filter_by(user_id="user-limited", event="permission-denied").first()
    finally:
        db.close()


def test_cross_user_ownership_isolated_for_reads_and_writes():
    add_second_user()
    other_token = login("other@personalos.ai", "other-password")["token"]
    created = client.post("/api/renewals", headers=auth(other_token), json={"name": "Other private renewal", "dueDate": "2026-12-01"})
    assert created.status_code == 201
    item_id = created.json()["item"]["id"]
    assert any(item["id"] == item_id for item in client.get("/api/renewals", headers=auth(other_token)).json()["renewals"])
    demo_token = login()["token"]
    assert all(item["id"] != item_id for item in client.get("/api/renewals", headers=auth(demo_token)).json()["renewals"])
    assert client.put(f"/api/renewals/{item_id}", headers=auth(demo_token), json={"name": "Hijacked"}).status_code == 404


def test_password_hash_is_stored_and_never_plaintext():
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email="demo@personalos.ai").one()
        assert user.password_hash != "test-demo-password"
        assert user.password_hash.startswith("$argon2") or user.password_hash.startswith("$2")
        assert not hasattr(user, "password")
    finally:
        db.close()
