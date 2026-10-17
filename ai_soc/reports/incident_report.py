import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from ai_soc.alerts.models import IncidentRecord
from ai_soc.config.settings import get_settings


class IncidentReportGenerator:
    """Generates detailed security incident reports in Markdown, HTML, and JSON formats."""

    def __init__(self):
        self.settings = get_settings()

    def generate_markdown(self, incident: IncidentRecord) -> str:
        alert = incident.alert
        intel = incident.threat_intel
        risk = incident.risk_assessment
        ai = incident.ai_analysis
        resp = incident.response_action

        factors_md = ""
        if risk.contributing_factors:
            factors_md = "| Evidence Factor | Description | Points |\n|---|---|---|\n"
            for f in risk.contributing_factors:
                factors_md += f"| **{f.name}** | {f.description} | `+{f.points}` |\n"
        else:
            factors_md = "_No high-risk factors identified._\n"

        intel_md = "_No external threat intelligence available._"
        if intel:
            intel_md = f"""
- **Indicator:** `{intel.indicator}` ({intel.usage_type})
- **Reputation / Abuse Score:** **{intel.abuse_confidence_score}%** (Total Reports: {intel.total_reports})
- **Origin / ISP:** {intel.isp} ({intel.country_name} [{intel.country_code}])
- **Threat Tags:** {', '.join(intel.threat_tags) if intel.threat_tags else 'None'}
- **Provider:** {intel.source_provider}
"""

        ai_md = "_No AI analysis performed._"
        if ai:
            ai_md = f"""
- **Attack Classification:** **{ai.attack_type}**
- **MITRE ATT&CK:** `{ai.mitre_attack_technique}`
- **Analyst Summary:** {ai.summary}
- **Evidence & Reasoning:** {ai.evidence_reasoning}
- **Confidence:** {int(ai.confidence * 100)}%
- **Recommended Action:** {ai.recommended_action}
- **Advisory Principle:** _{ai.advisory_notice}_
"""

        response_md = "_No autonomous response triggered._"
        if resp:
            response_md = f"""
- **Action Type:** `{resp.action_type}` ({resp.status})
- **Target IP:** `{resp.target_ip or 'N/A'}`
- **Execution Reason:** {resp.reason}
- **Rule Applied:** `{resp.rule_applied}`
- **Time to Live (TTL):** {resp.ttl_seconds} seconds
- **Executed By:** {resp.executed_by}
"""

        report = f"""# 🛡️ SECURITY INCIDENT REPORT
**Incident ID:** `{incident.incident_id}`  
**Generated At:** {incident.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Status:** **{incident.status}**  
**Severity:** **{risk.severity}** (Score: {risk.score}/100)

---

## 1. Executive Summary
{ai.summary if ai else alert.description}

---

## 2. Telemetry & Alert Details
- **Source Platform:** `{alert.source.upper()}`
- **Event Category:** `{alert.event_type}`
- **Alert Title:** {alert.title}
- **Source IP / Host:** `{alert.source_ip or 'N/A'}`:{alert.source_port or 'N/A'}
- **Target Destination:** `{alert.destination_ip or 'N/A'}`:{alert.destination_port or 'N/A'} ({alert.protocol})
- **Targeted User:** `{alert.target_user or 'N/A'}` (Privileged: **{alert.is_privileged_user}**)
- **Affected Endpoint:** `{alert.hostname}`
- **Detection Rule:** `{alert.rule_id}` - {alert.rule_description or 'N/A'}
- **Raw Event Excerpt:**
```text
{alert.raw_log or alert.description}
```

---

## 3. Threat Intelligence Enrichment
{intel_md}

---

## 4. Deterministic Risk Score Breakdown
{factors_md}

**Final Assessment:** {risk.explanation}

---

## 5. AI Investigation & MITRE ATT&CK
{ai_md}

---

## 6. Response & Containment Action
{response_md}

---

_Report generated autonomously by AI Cyberthreat Hunting & Autonomous SOC Engine._
"""
        return report

    def save_report(self, incident: IncidentRecord, fmt: str = "markdown") -> Path:
        """Save report to data/reports/ directory."""
        ts_str = incident.created_at.strftime("%Y%m%d_%H%M%S")
        filename = f"incident_{ts_str}_{incident.incident_id[:8]}"

        if fmt == "markdown" or fmt == "md":
            filepath = self.settings.REPORTS_DIR / f"{filename}.md"
            filepath.write_text(self.generate_markdown(incident), encoding="utf-8")
            return filepath
        elif fmt == "json":
            filepath = self.settings.REPORTS_DIR / f"{filename}.json"
            filepath.write_text(incident.model_dump_json(indent=2), encoding="utf-8")
            return filepath
        elif fmt == "html":
            filepath = self.settings.REPORTS_DIR / f"{filename}.html"
            content = self.generate_markdown(incident).replace("\n", "<br>")
            html = f"<html><head><title>Incident {incident.incident_id}</title><style>body{{font-family:sans-serif;padding:30px;background:#0f172a;color:#f8fafc;}}</style></head><body>{content}</body></html>"
            filepath.write_text(html, encoding="utf-8")
            return filepath

        raise ValueError(f"Unsupported format: {fmt}")
