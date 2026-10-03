from __future__ import annotations

from datetime import date as DateType
from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: str
    role: str
    permissions: list[str]


class LoginRequest(BaseModel):
    email: str
    password: str


class RenewalCreate(BaseModel):
    name: str
    category: str = "Custom"
    dueDate: DateType
    reminderDays: int = Field(default=7, ge=0)


class RenewalUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    dueDate: DateType | None = None
    reminderDays: int | None = Field(default=None, ge=0)
    status: str | None = None


class RenewalOut(BaseModel):
    id: str
    name: str
    category: str
    dueDate: date
    reminderDays: int
    status: str


class HealthCreate(BaseModel):
    date: DateType | None = None
    metric: str
    value: float
    unit: str = ""


class HealthOut(BaseModel):
    id: str
    date: DateType
    metric: str
    value: float
    unit: str


class RouteRequest(BaseModel):
    """Supervisor input contract; unknown fields are ignored for compatibility."""
    model_config = ConfigDict(extra="ignore")
    query: str = Field(default="", max_length=2000)


class InvestmentProposalRequest(BaseModel):
    symbol: str = Field(default="HDFCBANK", min_length=1, max_length=20)
    amount: float = Field(default=10000, gt=0)
    riskLevel: str = Field(default="Medium", min_length=1, max_length=30)


class InvestmentConfirmRequest(BaseModel):
    approved: bool
    mfa_verified: bool = False
    proposalId: str | None = None
    symbol: str | None = None
    amount: float | None = Field(default=None, gt=0)
    mfa_code: str | None = Field(default=None, min_length=6, max_length=6)

class InvestmentMFARequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)
