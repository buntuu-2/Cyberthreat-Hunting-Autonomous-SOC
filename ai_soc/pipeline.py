import logging
from typing import Any, Optional, Callable, List
from datetime import datetime, timezone

from ai_soc.alerts.models import (
    NormalizedAlert,
    ThreatIntelResult,
    RiskAssessment,
    AIAnalysis,
    ResponseAction,
    IncidentRecord,
)
from ai_soc.alerts.parser import AlertParser
from ai_soc.alerts.normalizer import AlertNormalizer
from ai_soc.threat_intel.reputation import ThreatIntelEngine
from ai_soc.detection.risk_engine import RiskEngine
from ai_soc.ai.analyzer import AIThreatAnalyzer
from ai_soc.response.policy import ResponsePolicyEngine
from ai_soc.response.firewall import FirewallManager
from ai_soc.reports.incident_report import IncidentReportGenerator
from ai_soc.store import IncidentStore
from ai_soc.config.settings import get_settings

logger = logging.getLogger(__name__)


class SOCPipeline:
    """
    Core Autonomous SOC Pipeline.
    Orchestrates: Ingest -> Parse -> Normalize -> Threat Intel -> Risk Assessment -> AI Analysis -> Policy -> Automated Response -> Storage & Notification.
    """

    def __init__(self):
        self.settings = get_settings()
        self.threat_intel = ThreatIntelEngine()
        self.risk_engine = RiskEngine()
        self.ai_analyzer = AIThreatAnalyzer()
        self.response_policy = ResponsePolicyEngine()
        self.firewall = FirewallManager()
        self.report_generator = IncidentReportGenerator()
        self.store = IncidentStore()
        self._listeners: List[Callable[[IncidentRecord], None]] = []

    def subscribe(self, callback: Callable[[IncidentRecord], None]):
        """Subscribe to real-time incident event notifications."""
        self._listeners.append(callback)

    def process_raw(self, raw_input: Any) -> IncidentRecord:
        """Parse raw event string or dict and process through SOC workflow."""
        source, parsed_data = AlertParser.detect_and_parse(raw_input)
        normalized_alert = AlertNormalizer.normalize(source, parsed_data)
        return self.process_alert(normalized_alert)

    def process_alert(self, alert: NormalizedAlert) -> IncidentRecord:
        """Execute end-to-end security investigation and response workflow."""
        logger.info(f"Processing alert {alert.alert_id} ({alert.source}: {alert.title})")

        # 1. Threat Intelligence Enrichment (Module 4)
        intel_result: Optional[ThreatIntelResult] = None
        if alert.source_ip:
            intel_result = self.threat_intel.lookup_ip(alert.source_ip)

        # 2. Deterministic Risk Assessment (Module 6 & Section 9)
        risk = self.risk_engine.assess_risk(alert, intel_result)

        # 3. AI Threat Investigation & MITRE Mapping (Module 5 & Section 10)
        ai_analysis = self.ai_analyzer.analyze(alert, intel_result, risk)

        # 4. Response Policy Gatekeeper (Module 7)
        is_permitted, action_type, policy_reason = self.response_policy.evaluate(alert, risk)

        # 5. Autonomous Action Execution (Module 7)
        response_action: Optional[ResponseAction] = None
        if is_permitted and action_type == "UFW_BLOCK" and alert.source_ip:
            response_action = self.firewall.block_ip(
                ip=alert.source_ip,
                reason=policy_reason,
                risk_score=risk.score,
                rule_applied=f"POLICY_AUTO_BLOCK_{risk.severity}",
                ttl_seconds=self.settings.DEFAULT_BLOCK_TTL_SECONDS,
                executed_by="Autonomous SOC Policy Engine"
            )
        elif not is_permitted:
            response_action = ResponseAction(
                action_type=action_type,
                target_ip=alert.source_ip,
                status="SKIPPED" if action_type == "NO_ACTION" else ("BYPASSED" if action_type == "ALLOWLIST_BYPASS" else "PENDING_APPROVAL"),
                reason=policy_reason,
                risk_score=risk.score,
                rule_applied="POLICY_GATEKEEPER",
                is_active=False,
                executed_by="Autonomous Response Policy"
            )

        # 6. Create Incident Record
        incident = IncidentRecord(
            alert=alert,
            threat_intel=intel_result,
            risk_assessment=risk,
            ai_analysis=ai_analysis,
            response_action=response_action,
            status="CONTAINED" if (response_action and response_action.status == "SUCCESS") else "OPEN"
        )

        # 7. Persist to storage
        self.store.save(incident)

        # 8. Notify live listeners / WebSockets
        for listener in self._listeners:
            try:
                listener(incident)
            except Exception as e:
                logger.error(f"Error in pipeline listener: {e}")

        return incident


_global_pipeline: Optional[SOCPipeline] = None


def get_pipeline() -> SOCPipeline:
    global _global_pipeline
    if _global_pipeline is None:
        _global_pipeline = SOCPipeline()
    return _global_pipeline
