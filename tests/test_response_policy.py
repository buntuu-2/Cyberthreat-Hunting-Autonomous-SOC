import pytest
from ai_soc.alerts.models import NormalizedAlert, RiskAssessment, RiskFactor
from ai_soc.response.policy import ResponsePolicyEngine
from ai_soc.response.firewall import FirewallManager


def test_allowlist_protection():
    policy = ResponsePolicyEngine()
    alert = NormalizedAlert(
        source="wazuh",
        event_type="auth_failure",
        title="Failed login",
        description="Localhost test",
        source_ip="127.0.0.1"
    )
    risk = RiskAssessment(score=95, severity="CRITICAL")

    is_permitted, action, reason = policy.evaluate(alert, risk)
    assert is_permitted is False
    assert action == "ALLOWLIST_BYPASS"
    assert "protected allowlist" in reason


def test_severity_threshold_gate():
    policy = ResponsePolicyEngine()
    alert = NormalizedAlert(
        source="wazuh",
        event_type="auth_failure",
        title="Failed login",
        description="Low severity test",
        source_ip="198.51.100.22"
    )
    low_risk = RiskAssessment(score=25, severity="LOW")
    is_permitted, action, reason = policy.evaluate(alert, low_risk)
    assert is_permitted is False
    assert action == "NO_ACTION"

    high_risk = RiskAssessment(score=75, severity="HIGH")
    is_permitted_high, action_high, _ = policy.evaluate(alert, high_risk)
    assert is_permitted_high is True
    assert action_high == "UFW_BLOCK"


def test_firewall_block_and_unblock():
    mgr = FirewallManager()
    ip = "198.51.100.77"

    action = mgr.block_ip(ip, reason="Test block", risk_score=85, ttl_seconds=60)
    assert action.action_type == "UFW_BLOCK"
    assert action.status == "SUCCESS"
    assert ip in [b.target_ip for b in mgr.get_active_blocks()]

    unblock_action = mgr.unblock_ip(ip)
    assert unblock_action.action_type == "UFW_UNBLOCK"
    assert unblock_action.status == "SUCCESS"
    assert ip not in [b.target_ip for b in mgr.get_active_blocks()]
