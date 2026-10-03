from dataclasses import dataclass
from ..services import create_proposal, serialize_health, serialize_renewal


@dataclass
class RenewalService:
    repository: object

    def list(self) -> list[dict]:
        return [serialize_renewal(item) for item in self.repository.renewals()]


@dataclass
class HealthService:
    repository: object

    def list(self) -> list[dict]:
        return [serialize_health(item) for item in self.repository.health()]

    def average(self, metric: str) -> float:
        values = [item["value"] for item in self.list() if item["metric"] == metric]
        return sum(values) / len(values) if values else 0.0


@dataclass
class InvestmentService:
    repository: object

    def propose(self, symbol: str, amount: float, risk_level: str):
        return create_proposal(self.repository, symbol, amount, risk_level)
