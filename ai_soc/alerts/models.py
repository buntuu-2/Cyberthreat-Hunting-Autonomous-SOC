from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import uuid


class NormalizedAlert(BaseModel):
    """Normalized security alert schema across Wazuh, Suricata, and system logs."""
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = Field(..., description="wazuh | suricata | syslog | synthetic")
    event_type: str = Field(..., description="auth_failure | port_scan | privilege_escalation | brute_force | dos | malicious_traffic | generic")
    title: str
    description: str
    
    # Network indicators
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    source_port: Optional[int] = None
    destination_port: Optional[int] = None
    protocol: Optional[str] = "TCP"
    
    # Endpoint / Identity indicators
    target_user: Optional[str] = None
    is_privileged_user: bool = False
    hostname: Optional[str] = "ubuntu-endpoint"
    
    # SIEM / Rule references
    rule_id: Optional[str] = None
    rule_description: Optional[str] = None
    raw_severity: Optional[int] = 1  # Wazuh level 1-15 or Suricata 1-4
    
    raw_log: Optional[str] = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ThreatIntelResult(BaseModel):
    """Normalized threat intelligence indicator enrichment."""
    indicator: str
    indicator_type: str = "ip"
    abuse_confidence_score: int = 0  # 0 to 100
    is_malicious: bool = False
    is_whitelisted: bool = False
    country_code: Optional[str] = "XX"
    country_name: Optional[str] = "Unknown"
    isp: Optional[str] = "Unknown ISP"
    usage_type: Optional[str] = "Data Center / Web Hosting / Transit"
    total_reports: int = 0
    last_reported_at: Optional[str] = None
    threat_tags: List[str] = Field(default_factory=list)
    source_provider: str = "Internal / AbuseIPDB"
    cached: bool = False


class RiskFactor(BaseModel):
    """Individual contributing factor to risk score."""
    name: str
    description: str
    points: int


class RiskAssessment(BaseModel):
    """Deterministic, explainable risk assessment (Roadmap Section 9)."""
    score: int = 0  # 0 to 100
    severity: str = "LOW"  # LOW | MEDIUM | HIGH | CRITICAL
    contributing_factors: List[RiskFactor] = Field(default_factory=list)
    explanation: str = ""
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AIAnalysis(BaseModel):
    """AI-assisted threat investigation (Roadmap Section 10)."""
    attack_type: str
    mitre_attack_technique: str
    severity: str  # LOW | MEDIUM | HIGH | CRITICAL
    summary: str
    evidence_reasoning: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.85)
    recommended_action: str
    advisory_notice: str = "AI recommendations are advisory. Autonomous actions are strictly governed by deterministic policies."
    provider: str = "mock"


class ResponseAction(BaseModel):
    """Firewall or system response action record."""
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action_type: str  # "UFW_BLOCK" | "UFW_UNBLOCK" | "ALLOWLIST_BYPASS" | "MANUAL_APPROVAL_REQUIRED" | "NO_ACTION"
    target_ip: Optional[str] = None
    status: str  # "SUCCESS" | "FAILED" | "PENDING_APPROVAL" | "SKIPPED"
    reason: str
    risk_score: int
    rule_applied: str
    ttl_seconds: Optional[int] = 300
    expires_at: Optional[datetime] = None
    is_active: bool = True
    executed_by: str = "Autonomous Response Engine"


class IncidentRecord(BaseModel):
    """Complete incident pipeline entity for investigation and dashboard."""
    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    alert: NormalizedAlert
    threat_intel: Optional[ThreatIntelResult] = None
    risk_assessment: RiskAssessment
    ai_analysis: Optional[AIAnalysis] = None
    response_action: Optional[ResponseAction] = None
    status: str = "OPEN"  # "OPEN" | "CONTAINED" | "RESOLVED" | "FALSE_POSITIVE"
