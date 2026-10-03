from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from .config import get_settings
from .db import get_db
from .models import User, RevokedToken
from .repositories import Repository
from .services import TOKEN

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

def hash_password(password: str) -> str: return pwd_context.hash(password)
def verify_password(password: str, hashed: str) -> bool:
    try: return pwd_context.verify(password, hashed)
    except (ValueError, TypeError): return False
def create_access_token(user: User) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": user.id, "jti": __import__("uuid").uuid4().hex, "iat": now, "exp": now + timedelta(minutes=settings.access_token_minutes)}, settings.jwt_secret, algorithm=settings.jwt_algorithm)
def current_user(request: Request, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    # Preserve the original demo client's placeholder token only in development.
    # The legacy demo token remains available only for local development so
    # existing seeded clients continue to work while production requires JWT.
    if get_settings().environment != "production" and token in {"******", TOKEN}:
        user = Repository(db).user("demo@personalos.ai")
        if user: return user
    try:
        data = jwt.decode(token, get_settings().jwt_secret, algorithms=[get_settings().jwt_algorithm])
        user_id = data.get("sub")
        if not user_id: raise JWTError()
    except JWTError:
        Repository(db).log("authentication-failed", {"path": request.url.path})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token", headers={"WWW-Authenticate":"Bearer"})
    if data.get("jti") and db.get(RevokedToken, data["jti"]):
        raise HTTPException(status_code=401, detail="Token revoked", headers={"WWW-Authenticate":"Bearer"})
    user = db.get(User, user_id)
    if not user or not user.is_active: raise HTTPException(401, "Authentication required")
    return user
def require_permission(permission: str):
    aliases = {"renewal.create": {"renewal.create", "renewal:write"}, "renewal.update": {"renewal.update", "renewal:write"},
               "renewal.delete": {"renewal.delete", "renewal:write"}, "health.create": {"health.create", "health:read"},
               "stock.analyze": {"stock.analyze", "stock:read"},
               "investment.propose": {"investment.propose", "investment:review"},
               "investment.confirm": {"investment.confirm", "investment:confirm", "investment.execute"}}
    def dependency(request: Request, db: Session = Depends(get_db), user=Depends(current_user)):
        if not (set(user.permissions or []) & aliases.get(permission, {permission})):
            Repository(db, user.id).log("permission-denied", {"path": request.url.path, "permission": permission})
            raise HTTPException(403, "Permission denied")
        return user
    return dependency

def revoke_token(request: Request, db: Session, user: User):
    token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    try:
        claims = jwt.decode(token, get_settings().jwt_secret, algorithms=[get_settings().jwt_algorithm], options={"verify_exp": False})
        if claims.get("jti") and claims.get("exp"):
            db.add(RevokedToken(jti=claims["jti"], user_id=user.id,
                                 expires_at=datetime.fromtimestamp(claims["exp"], timezone.utc).replace(tzinfo=None)))
            db.commit()
    except JWTError:
        pass

def require_role(*roles: str):
    """FastAPI dependency for endpoints restricted to one or more roles."""
    allowed = set(roles)
    def dependency(user=Depends(current_user)):
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail="Role not permitted")
        return user
    return dependency
