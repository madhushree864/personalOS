"""Application-facing domain boundaries.

These small services keep persistence and transport concerns out of routing
and make each domain independently replaceable.
"""
from .services import serialize_health, serialize_renewal


class RenewalDomainService:
    def list(self, repository):
        return [serialize_renewal(item) for item in repository.renewals()]


class HealthDomainService:
    def list(self, repository):
        return [serialize_health(item) for item in repository.health()]


class InvestmentDomainService:
    def propose(self, repository, symbol, amount, risk_level):
        from .services import create_proposal
        return create_proposal(repository, symbol, amount, risk_level)
