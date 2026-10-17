import json
import logging
from typing import Optional, Dict, Any
import requests

from ai_soc.alerts.models import NormalizedAlert, ThreatIntelResult, RiskAssessment, AIAnalysis
from ai_soc.config.settings import get_settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are an expert SOC Tier 2 Cyberthreat Intelligence Analyst.
Analyze the provided security event, threat intelligence enrichment, and deterministic risk score.
Produce a strictly formatted JSON object with:
- "attack_type": Specific attack classification (e.g. "SSH Brute-Force Authentication Attack")
- "mitre_attack_technique": MITRE ATT&CK ID and technique name (e.g. "T1110.001 - Password Guessing")
- "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
- "summary": 2-3 sentences explaining the incident for an executive or SOC manager.
- "evidence_reasoning": Clear explanation detailing which observables (IP reputation, targeted user, frequency, ports) justify the classification.
- "confidence": Float between 0.0 and 1.0.
- "recommended_action": Concrete remediation and defense steps.
"""


class AIThreatAnalyzer:
    """
    AI-driven SOC Investigation Layer.
    Advisory role only: never executes system commands directly.
    """

    def __init__(self):
        self.settings = get_settings()

    def analyze(
        self,
        alert: NormalizedAlert,
        threat_intel: Optional[ThreatIntelResult],
        risk_assessment: RiskAssessment
    ) -> AIAnalysis:
        provider = self.settings.LLM_PROVIDER.lower()

        # Try live LLM provider if configured
        if provider == "gemini" and self.settings.GEMINI_API_KEY:
            try:
                return self._call_gemini(alert, threat_intel, risk_assessment)
            except Exception as e:
                logger.warning(f"Gemini API analysis failed: {e}. Falling back to internal SOC intelligence model.")

        elif provider == "openai" and self.settings.OPENAI_API_KEY:
            try:
                return self._call_openai(alert, threat_intel, risk_assessment)
            except Exception as e:
                logger.warning(f"OpenAI API analysis failed: {e}. Falling back to internal SOC intelligence model.")

        elif provider == "ollama":
            try:
                return self._call_ollama(alert, threat_intel, risk_assessment)
            except Exception as e:
                logger.warning(f"Ollama local model failed: {e}. Falling back to internal SOC intelligence model.")

        # Default high-fidelity heuristic AI analyzer (100% offline & demo guaranteed)
        return self._heuristic_soc_analysis(alert, threat_intel, risk_assessment)

    def _heuristic_soc_analysis(
        self,
        alert: NormalizedAlert,
        threat_intel: Optional[ThreatIntelResult],
        risk_assessment: RiskAssessment
    ) -> AIAnalysis:
        """Deterministic expert system that mirrors enterprise SOC analyst reasoning."""
        event_type = alert.event_type
        user = alert.target_user or "unknown"
        src_ip = alert.source_ip or "N/A"
        abuse_score = threat_intel.abuse_confidence_score if threat_intel else 0
        score = risk_assessment.score
        severity = risk_assessment.severity

        if event_type in ["brute_force", "auth_failure"]:
            attack_type = "SSH Brute-Force Authentication Attack"
            mitre = "T1110.001 - Brute Force: Password Guessing"
            summary = (
                f"Automated credential brute-force attack detected from source IP {src_ip} "
                f"targeting account '{user}'. High-frequency authentication failures suggest dictionary or automated password sprayer."
            )
            evidence_reasoning = (
                f"Observable evidence includes: repeated SSH authentication failures targeting '{user}', "
                f"source IP {src_ip} with {abuse_score}% external threat intelligence abuse score, "
                f"and deterministic risk score of {score}/100 [{severity}]."
            )
            action = (
                f"Execute immediate temporary firewall block on {src_ip} via UFW. "
                f"Review /var/log/auth.log for successful logins from this subnet. "
                f"Enforce SSH key-only authentication and disable root password access."
            )
            confidence = 0.94

        elif event_type == "port_scan":
            attack_type = "Network Reconnaissance / Port Scanning Probe"
            mitre = "T1046 - Network Service Discovery"
            summary = (
                f"Reconnaissance port scan identified from {src_ip}. Host sent rapid probes "
                f"across multiple ports to map accessible network services and identify potential vulnerabilities."
            )
            evidence_reasoning = (
                f"Suricata network IDS event detected probe signatures. Indicator {src_ip} has "
                f"{abuse_score}% abuse score on reputation databases. Risk score evaluated at {score}/100."
            )
            action = (
                f"Drop inbound traffic from {src_ip}. Inspect firewall logs for probes targeting sensitive service ports (22, 3306, 8080). "
                f"Ensure non-essential external service ports remain closed."
            )
            confidence = 0.89

        elif event_type == "privilege_escalation":
            attack_type = "Local Privilege Escalation / Sudo Abuse"
            mitre = "T1548.003 - Abuse Elevation Control Mechanism: Sudo and Sudo Caching"
            summary = (
                f"Privileged command execution attempt detected on host {alert.hostname}. "
                f"User '{user}' attempted unauthorized sudo command or permission escalation."
            )
            evidence_reasoning = (
                f"Audit trail caught execution against privileged identity. "
                f"Targeted user '{user}' has root privileges. Risk engine assigned {score}/100."
            )
            action = (
                f"Inspect active session for user {user}. Verify sudoers configuration and revoke suspicious sudo permissions. "
                f"Check process tree for spawned interactive shell or backdoors."
            )
            confidence = 0.91

        elif event_type == "auth_success" and score >= 60:
            attack_type = "Compromised Credentials / Successful Post-Brute Login"
            mitre = "T1078.003 - Valid Accounts: Local Accounts"
            summary = (
                f"CRITICAL: Host {src_ip} successfully logged in as '{user}' after repeated prior failure events. "
                f"High probability of credential cracking success or session hijack."
            )
            evidence_reasoning = (
                f"Temporal correlation between multiple failed authentication events followed by accepted login from "
                f"untrusted IP {src_ip} (Threat Score: {abuse_score}%). Combined risk score reached {score}/100 [CRITICAL]."
            )
            action = (
                f"Immediately terminate active session for {user}. Force password reset and revoke active SSH authorized_keys. "
                f"Isolate host and perform forensic memory analysis."
            )
            confidence = 0.97

        else:
            attack_type = "Suspicious Network Anomaly"
            mitre = "T1071 - Application Layer Protocol"
            summary = (
                f"Unusual network activity observed from {src_ip} on port {alert.destination_port or 'unknown'}. "
                f"Event recorded by sensor {alert.source} with severity {severity}."
            )
            evidence_reasoning = (
                f"Telemetry triggered rule '{alert.rule_description or alert.title}'. "
                f"Indicator reputation evaluated with risk score {score}/100."
            )
            action = "Monitor host telemetry, cross-reference with DNS logs, and alert SOC tier 1."
            confidence = 0.75

        return AIAnalysis(
            attack_type=attack_type,
            mitre_attack_technique=mitre,
            severity=severity,
            summary=summary,
            evidence_reasoning=evidence_reasoning,
            confidence=confidence,
            recommended_action=action,
            provider="Expert SOC Intelligence Engine (Local Heuristic)"
        )

    def _call_gemini(
        self,
        alert: NormalizedAlert,
        threat_intel: Optional[ThreatIntelResult],
        risk_assessment: RiskAssessment
    ) -> AIAnalysis:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.settings.GEMINI_API_KEY}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": SYSTEM_PROMPT},
                        {
                            "text": json.dumps({
                                "alert": alert.model_dump(mode="json"),
                                "threat_intel": threat_intel.model_dump(mode="json") if threat_intel else None,
                                "risk_score": risk_assessment.score,
                                "risk_severity": risk_assessment.severity,
                                "contributing_factors": [f.model_dump() for f in risk_assessment.contributing_factors]
                            }, indent=2)
                        }
                    ]
                }
            ],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        res = requests.post(url, json=payload, timeout=8)
        res.raise_for_status()
        text_content = res.json()["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text_content)
        parsed["provider"] = "Google Gemini 1.5 Flash"
        return AIAnalysis(**parsed)

    def _call_openai(
        self,
        alert: NormalizedAlert,
        threat_intel: Optional[ThreatIntelResult],
        risk_assessment: RiskAssessment
    ) -> AIAnalysis:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({
                    "alert": alert.model_dump(mode="json"),
                    "threat_intel": threat_intel.model_dump(mode="json") if threat_intel else None,
                    "risk_score": risk_assessment.score,
                    "risk_severity": risk_assessment.severity
                })}
            ],
            "response_format": {"type": "json_object"}
        }
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        res.raise_for_status()
        content = res.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        parsed["provider"] = "OpenAI GPT-4o-mini"
        return AIAnalysis(**parsed)

    def _call_ollama(
        self,
        alert: NormalizedAlert,
        threat_intel: Optional[ThreatIntelResult],
        risk_assessment: RiskAssessment
    ) -> AIAnalysis:
        url = f"{self.settings.OLLAMA_HOST}/api/generate"
        payload = {
            "model": self.settings.OLLAMA_MODEL,
            "prompt": f"{SYSTEM_PROMPT}\n\nSecurity Event:\n{alert.model_dump_json()}\nThreat Intel:\n{threat_intel.model_dump_json() if threat_intel else 'None'}\nRisk Score: {risk_assessment.score}\nProvide JSON response only.",
            "format": "json",
            "stream": False
        }
        res = requests.post(url, json=payload, timeout=12)
        res.raise_for_status()
        content = res.json().get("response", "{}")
        parsed = json.loads(content)
        parsed["provider"] = f"Local Ollama ({self.settings.OLLAMA_MODEL})"
        return AIAnalysis(**parsed)
