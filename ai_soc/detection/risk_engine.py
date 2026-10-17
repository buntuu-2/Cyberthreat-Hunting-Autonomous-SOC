from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

from ai_soc.alerts.models import NormalizedAlert, ThreatIntelResult, RiskAssessment, RiskFactor
from ai_soc.config.settings import get_settings


class RiskEngine:
    """
    Deterministic, transparent, auditable risk scoring engine.
    Implements the exact scoring model specified in Section 9 of the Project Roadmap.
    """

    def __init__(self, window_minutes: int = 15):
        self.settings = get_settings()
        self.window_minutes = window_minutes
        
        # State tracking: IP -> list of timestamps of failed logins
        self._failed_logins: Dict[str, List[datetime]] = defaultdict(list)
        # State tracking: IP -> list of timestamps of all alerts
        self._ip_alert_history: Dict[str, List[datetime]] = defaultdict(list)
        # State tracking: IP -> set of targeted users
        self._ip_targeted_users: Dict[str, set] = defaultdict(set)

    def _cleanup_old_records(self, now: datetime):
        """Remove state older than window_minutes."""
        cutoff = now - timedelta(minutes=self.window_minutes)
        for ip in list(self._failed_logins.keys()):
            self._failed_logins[ip] = [t for t in self._failed_logins[ip] if t > cutoff]
            if not self._failed_logins[ip]:
                del self._failed_logins[ip]

        for ip in list(self._ip_alert_history.keys()):
            self._ip_alert_history[ip] = [t for t in self._ip_alert_history[ip] if t > cutoff]
            if not self._ip_alert_history[ip]:
                del self._ip_alert_history[ip]

    def assess_risk(
        self,
        alert: NormalizedAlert,
        threat_intel: Optional[ThreatIntelResult] = None
    ) -> RiskAssessment:
        """
        Evaluate deterministic factors and return score, severity, and explanation.
        """
        now = alert.timestamp if alert.timestamp.tzinfo else alert.timestamp.replace(tzinfo=timezone.utc)
        self._cleanup_old_records(now)

        ip = alert.source_ip or "unknown"
        user = (alert.target_user or "").lower()

        # Update alert history
        if ip != "unknown":
            self._ip_alert_history[ip].append(now)
            if user:
                self._ip_targeted_users[ip].add(user)

        factors: List[RiskFactor] = []
        score = 0

        # Check: Did this IP have previous failures?
        recent_failures_count = len(self._failed_logins[ip]) if ip != "unknown" else 0

        # Factor 1: Repeated Failed Login Attempts (+20)
        is_failure = alert.event_type in ["auth_failure", "brute_force"]
        if is_failure:
            if ip != "unknown":
                self._failed_logins[ip].append(now)
                recent_failures_count = len(self._failed_logins[ip])

            if recent_failures_count >= 3 or alert.event_type == "brute_force":
                pts = self.settings.POINTS_REPEATED_FAILED_LOGINS
                score += pts
                factors.append(RiskFactor(
                    name="Repeated Failed Login Attempts",
                    description=f"{recent_failures_count} consecutive failed authentication attempts recorded for source {ip}",
                    points=pts
                ))

        # Factor 2: Privileged Account Targeted (+20)
        if alert.is_privileged_user or user in ["root", "admin", "administrator", "sudo"]:
            pts = self.settings.POINTS_PRIVILEGED_ACCOUNT
            score += pts
            factors.append(RiskFactor(
                name="Privileged Account Targeted",
                description=f"High-privilege account '{alert.target_user}' targeted in security event",
                points=pts
            ))

        # Factor 3: Known Suspicious / Malicious IP Reputation (+30)
        if threat_intel and (threat_intel.abuse_confidence_score >= 50 or threat_intel.is_malicious):
            pts = self.settings.POINTS_MALICIOUS_IP_REPUTATION
            score += pts
            factors.append(RiskFactor(
                name="Known Malicious IP Reputation",
                description=f"Threat intelligence reports {threat_intel.abuse_confidence_score}% abuse confidence ({threat_intel.total_reports} prior abuse reports)",
                points=pts
            ))

        # Factor 4: Repeated Behavior Over Time (+15)
        total_recent_alerts = len(self._ip_alert_history[ip]) if ip != "unknown" else 0
        if total_recent_alerts >= 2:
            pts = self.settings.POINTS_REPEATED_BEHAVIOR
            score += pts
            factors.append(RiskFactor(
                name="Repeated Behavior Over Time",
                description=f"Multiple security events ({total_recent_alerts} events) observed from source within sliding window",
                points=pts
            ))

        # Factor 5: Successful Login After Repeated Failures (+30)
        if alert.event_type == "auth_success" and recent_failures_count >= 3:
            pts = self.settings.POINTS_SUCCESS_AFTER_FAILURE
            score += pts
            factors.append(RiskFactor(
                name="Successful Login After Repeated Failures",
                description=f"CRITICAL: Successful authentication from {ip} immediately following {recent_failures_count} failed attempts (possible credential crack)",
                points=pts
            ))

        # Factor 6 (Network Recon / Scan): +15 if Port Scan detected
        if alert.event_type == "port_scan":
            score += 15
            factors.append(RiskFactor(
                name="Network Reconnaissance Activity",
                description="Network port scan or service enumeration probe detected by IDS",
                points=15
            ))

        # Cap score at 100
        final_score = min(100, score)

        # Severity Mapping (Roadmap Section 9)
        # 0–30 LOW
        # 31–60 MEDIUM
        # 61–80 HIGH
        # 81–100 CRITICAL
        if final_score <= self.settings.RISK_THRESHOLD_LOW:
            severity = "LOW"
        elif final_score <= self.settings.RISK_THRESHOLD_MEDIUM:
            severity = "MEDIUM"
        elif final_score <= self.settings.RISK_THRESHOLD_HIGH:
            severity = "HIGH"
        else:
            severity = "CRITICAL"

        explanation = self._build_explanation(final_score, severity, factors)

        return RiskAssessment(
            score=final_score,
            severity=severity,
            contributing_factors=factors,
            explanation=explanation,
            calculated_at=now
        )

    def _build_explanation(self, score: int, severity: str, factors: List[RiskFactor]) -> str:
        if not factors:
            return f"Low baseline activity (Score: {score}/100, Severity: {severity}). No high-risk factors identified."

        details = "; ".join([f"{f.name} (+{f.points})" for f in factors])
        return (
            f"Assigned risk score {score}/100 [{severity}] based on deterministic evidence: "
            f"{details}."
        )

    def reset_state(self):
        """Reset state tracking (useful in test suites)."""
        self._failed_logins.clear()
        self._ip_alert_history.clear()
        self._ip_targeted_users.clear()
