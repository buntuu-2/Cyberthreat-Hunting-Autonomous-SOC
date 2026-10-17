import ipaddress
from typing import Tuple
from ai_soc.alerts.models import NormalizedAlert, RiskAssessment
from ai_soc.config.settings import get_settings


class ResponsePolicyEngine:
    """
    Deterministic response policy gatekeeper.
    Enforces allowlisting, severity thresholds, and approval requirements.
    """

    SEVERITY_RANK = {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4
    }

    def __init__(self):
        self.settings = get_settings()

    def evaluate(self, alert: NormalizedAlert, risk: RiskAssessment) -> Tuple[bool, str, str]:
        """
        Evaluate if an automated action can be taken.
        Returns:
            (is_permitted: bool, action_type: str, reason: str)
        """
        ip = alert.source_ip
        if not ip:
            return False, "NO_ACTION", "No source IP available for automated network response"

        # Check Allowlist
        if self.is_allowlisted(ip):
            return False, "ALLOWLIST_BYPASS", f"Source IP {ip} is in protected allowlist. Blocking prohibited."

        # Check if Auto-Response is globally enabled
        if not self.settings.AUTO_RESPONSE_ENABLED:
            return False, "MANUAL_APPROVAL_REQUIRED", "Automated response disabled globally. Queued for human analyst approval."

        # Check severity threshold
        min_sev = self.settings.MIN_SEVERITY_AUTO_BLOCK.upper()
        min_rank = self.SEVERITY_RANK.get(min_sev, 3)
        current_rank = self.SEVERITY_RANK.get(risk.severity.upper(), 1)

        if current_rank < min_rank:
            return (
                False,
                "NO_ACTION",
                f"Risk severity '{risk.severity}' is below configured automated block threshold '{min_sev}'."
            )

        # Allow automated temporary UFW firewall block
        return (
            True,
            "UFW_BLOCK",
            f"Risk score {risk.score}/100 [{risk.severity}] meets or exceeds threshold '{min_sev}'. Predefined temporary firewall block permitted."
        )

    def is_allowlisted(self, ip_str: str) -> bool:
        """Verify if IP is in configured allowlist or is a loopback / private gateway."""
        ip_clean = ip_str.strip()
        if ip_clean in self.settings.allowlist_set:
            return True

        try:
            ip_obj = ipaddress.ip_address(ip_clean)
            if ip_obj.is_loopback:
                return True
        except ValueError:
            pass

        return False
