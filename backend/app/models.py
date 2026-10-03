from datetime import date, datetime
from uuid import uuid4
from sqlalchemy import JSON, Date, DateTime, Float, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def uid() -> str: return str(uuid4())

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    role: Mapped[str] = mapped_column(String(40), default="user")
    permissions: Mapped[list] = mapped_column(JSON, default=list)

class Renewal(Base):
    __tablename__ = "renewals"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    owner_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(80), default="Custom")
    due_date: Mapped[date] = mapped_column(Date)
    reminder_days: Mapped[int] = mapped_column(Integer, default=7)
    status: Mapped[str] = mapped_column(String(30), default="upcoming")

class HealthRecord(Base):
    __tablename__ = "health_records"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    owner_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    date: Mapped[date] = mapped_column(Date)
    metric: Mapped[str] = mapped_column(String(80))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(40), default="")

class Holding(Base):
    __tablename__ = "holdings"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    owner_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    symbol: Mapped[str] = mapped_column(String(20))
    shares: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    allocation: Mapped[float] = mapped_column(Float)

class AuditEntry(Base):
    __tablename__ = "audit_entries"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    user_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    event: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSON, default=dict)

class InvestmentProposal(Base):
    __tablename__ = "investment_proposals"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    owner_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="pending_user_confirmation")
    symbol: Mapped[str] = mapped_column(String(20))
    amount: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(30), default="Medium")
    broker: Mapped[dict] = mapped_column(JSON, default=dict)
    policy_checks: Mapped[list] = mapped_column(JSON, default=list)
    requires_human_approval: Mapped[bool] = mapped_column(default=True)
    approved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)

class InvestmentApproval(Base):
    """Durable approval state; execution must only happen from APPROVED."""
    __tablename__ = "investment_approvals"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    proposal_id: Mapped[str] = mapped_column(String(64), ForeignKey("investment_proposals.id"), unique=True, index=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending_user")
    requested_by: Mapped[str] = mapped_column(String(64))
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mfa_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ingested")
    source: Mapped[str] = mapped_column(String(120), nullable=False, default="upload")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
