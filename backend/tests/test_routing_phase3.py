import pytest

from app.routing.broker import MockBrokerGateway
from app.routing.capabilities import default_capability_registry
from app.routing.contracts import ApprovalStatus, Intent, RouteWorkflow
from app.routing.policy import PolicyEngine
from app.routing.validator import RoutingValidator


def test_validator_is_deterministic_and_prioritizes_investment():
    validator = RoutingValidator()
    assert validator.validate("  BUY   HDFCBANK ").workflow is RouteWorkflow.INVESTMENT
    assert validator.validate("sleep and exercise").workflow is RouteWorkflow.HEALTH
    assert validator.validate("").workflow is RouteWorkflow.GENERAL


def test_policy_requires_explicit_approval_for_investment():
    engine = PolicyEngine()
    caps = {"investment.propose"}
    pending = engine.evaluate(RouteWorkflow.INVESTMENT, caps)
    approved = engine.evaluate(RouteWorkflow.INVESTMENT, caps, approved=True)
    assert pending.approval is ApprovalStatus.REQUIRED
    assert approved.approval is ApprovalStatus.APPROVED


def test_registry_does_not_grant_execution_capability():
    definition = default_capability_registry().get(RouteWorkflow.INVESTMENT)
    assert not definition.execution


def test_mock_gateway_cannot_execute_without_both_guards():
    gateway = MockBrokerGateway()
    with pytest.raises(PermissionError):
        gateway.execute({"symbol": "AAPL"}, policy_allowed=True, approved=False)
    result = gateway.execute({"symbol": "AAPL"}, policy_allowed=True, approved=True)
    assert result.executed is True


def test_investment_execution_requires_capability_approval_and_mfa():
    engine = PolicyEngine()
    assert not engine.evaluate(Intent.INVESTMENT_EXECUTION, {"investment.propose"},
                               approved=True, mfa_verified=True).allowed
    assert not engine.evaluate(Intent.INVESTMENT_EXECUTION, {"investment.execute"},
                               approved=True, mfa_verified=False).allowed
    assert engine.evaluate(Intent.INVESTMENT_EXECUTION, {"investment.execute"},
                           approved=True, mfa_verified=True).allowed
