import pytest
from datetime import datetime, timezone

from ai_soc.alerts.models import NormalizedAlert, ThreatIntelResult
from ai_soc.detection.risk_engine import RiskEngine


def test_baseline_low_risk():
    engine = RiskEngine()
    alert = NormalizedAlert(
        source="wazuh",
        event_type="generic",
        title="Normal system check",
        description="Routine log message",
        source_ip="192.168.1.50"
    )
    risk = engine.assess_risk(alert)
    assert risk.score <= 30
    assert risk.severity == "LOW"


def test_privileged_account_targeted():
    engine = RiskEngine()
    alert = NormalizedAlert(
        source="wazuh",
        event_type="auth_failure",
        title="Failed login",
        description="Password failed",
        source_ip="198.51.100.10",
        target_user="root",
        is_privileged_user=True
    )
    risk = engine.assess_risk(alert)
    # Privileged account adds 20
    assert risk.score >= 20
    assert any(f.name == "Privileged Account Targeted" for f in risk.contributing_factors)


def test_malicious_reputation_points():
    engine = RiskEngine()
    alert = NormalizedAlert(
        source="wazuh",
        event_type="auth_failure",
        title="SSH connection",
        description="Connection attempt",
        source_ip="198.51.100.42"
    )
    intel = ThreatIntelResult(
        indicator="198.51.100.42",
        abuse_confidence_score=95,
        is_malicious=True,
        total_reports=100
    )
    risk = engine.assess_risk(alert, threat_intel=intel)
    # Known malicious IP adds 30
    assert risk.score >= 30
    assert any(f.name == "Known Malicious IP Reputation" for f in risk.contributing_factors)


def test_repeated_failed_logins_and_escalation():
    engine = RiskEngine()
    ip = "198.51.100.99"
    intel = ThreatIntelResult(
        indicator=ip,
        abuse_confidence_score=90,
        is_malicious=True
    )

    # 1st attempt
    alert1 = NormalizedAlert(
        source="wazuh",
        event_type="auth_failure",
        title="SSH Failed",
        description="Attempt 1",
        source_ip=ip,
        target_user="root",
        is_privileged_user=True
    )
    risk1 = engine.assess_risk(alert1, intel)

    # 2nd attempt
    alert2 = NormalizedAlert(
        source="wazuh",
        event_type="auth_failure",
        title="SSH Failed",
        description="Attempt 2",
        source_ip=ip,
        target_user="root",
        is_privileged_user=True
    )
    risk2 = engine.assess_risk(alert2, intel)

    # 3rd attempt: triggers repeated failed logins (+20) + repeated behavior (+15) + privileged (+20) + reputation (+30) = 85 (CRITICAL)
    alert3 = NormalizedAlert(
        source="wazuh",
        event_type="auth_failure",
        title="SSH Failed",
        description="Attempt 3",
        source_ip=ip,
        target_user="root",
        is_privileged_user=True
    )
    risk3 = engine.assess_risk(alert3, intel)

    assert risk3.score >= 80
    assert risk3.severity == "CRITICAL"
    factor_names = [f.name for f in risk3.contributing_factors]
    assert "Repeated Failed Login Attempts" in factor_names
    assert "Privileged Account Targeted" in factor_names
    assert "Known Malicious IP Reputation" in factor_names


def test_success_after_failure_critical():
    engine = RiskEngine()
    ip = "198.51.100.88"

    # Send 3 failures
    for _ in range(3):
        engine.assess_risk(NormalizedAlert(
            source="syslog",
            event_type="auth_failure",
            title="SSH Failed",
            description="Failed login",
            source_ip=ip,
            target_user="admin",
            is_privileged_user=True
        ))

    # Now send successful login
    success_alert = NormalizedAlert(
        source="syslog",
        event_type="auth_success",
        title="SSH Accepted",
        description="Accepted login",
        source_ip=ip,
        target_user="admin",
        is_privileged_user=True
    )
    risk = engine.assess_risk(success_alert)

    # Should contain Successful Login After Repeated Failures (+30)
    assert any(f.name == "Successful Login After Repeated Failures" for f in risk.contributing_factors)
