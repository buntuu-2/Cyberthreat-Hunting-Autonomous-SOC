#!/usr/bin/env python3
"""
AI Cyberthreat Hunting & Autonomous SOC
Main execution entry point for CLI and Server modes.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from ai_soc.config.settings import get_settings
from ai_soc.pipeline import get_pipeline
from simulator.attack_simulator import AttackSimulator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_soc_main")


def print_banner():
    banner = r"""
========================================================================
  AI CYBERTHREAT HUNTING & AUTONOMOUS SOC - COMMAND ENGINE
  Final Year Major Project
  Students: Utkarsh Maurya (2304231550021) & Prince Maurya (2304231550009)
  College:  School of Management Sciences, Lucknow
========================================================================
    """
    print(banner)


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    import uvicorn
    settings = get_settings()
    print_banner()
    logger.info(f"Starting SOC Command Center Web Server at http://{host}:{port}")
    logger.info(f"Firewall Mode: {settings.FIREWALL_MODE.upper()} | Auto-Response: {settings.AUTO_RESPONSE_ENABLED}")
    logger.info(f"AI Provider: {settings.LLM_PROVIDER.upper()} | Threat Intel: {'MOCK' if settings.MOCK_THREAT_INTEL else 'LIVE'}")
    uvicorn.run("dashboard.api:app", host=host, port=port, reload=reload)


def run_simulation(workflow: str):
    print_banner()
    pipeline = get_pipeline()
    simulator = AttackSimulator(pipeline=pipeline)

    logger.info(f"Running Attack Simulation Workflow: {workflow}")
    if workflow in ["A", "all"]:
        incidents = simulator.run_workflow_a_ssh_bruteforce()
        print(f"\n[+] Workflow A Complete: {len(incidents)} alerts processed.")
        print(f"    Final Incident: {incidents[-1].incident_id}")
        print(f"    Risk Score: {incidents[-1].risk_assessment.score}/100 [{incidents[-1].risk_assessment.severity}]")
        print(f"    Firewall Action: {incidents[-1].response_action.action_type if incidents[-1].response_action else 'None'}")

    if workflow in ["B", "all"]:
        inc = simulator.run_workflow_b_portscan()
        print(f"\n[+] Workflow B Complete: Port scan processed.")
        print(f"    Incident: {inc.incident_id}")
        print(f"    Risk Score: {inc.risk_assessment.score}/100 [{inc.risk_assessment.severity}]")

    if workflow in ["C", "all"]:
        inc = simulator.run_workflow_c_threat_intel()
        print(f"\n[+] Workflow C Complete: Threat intelligence indicator enriched.")
        print(f"    Incident: {inc.incident_id}")
        print(f"    Indicator: {inc.threat_intel.indicator if inc.threat_intel else 'N/A'}")
        print(f"    Abuse Score: {inc.threat_intel.abuse_confidence_score if inc.threat_intel else 0}%")

    if workflow in ["D", "all"]:
        inc = simulator.run_workflow_d_credential_compromise()
        print(f"\n[+] Workflow D Complete: Credential compromise processed.")
        print(f"    Incident: {inc.incident_id}")
        print(f"    Risk Score: {inc.risk_assessment.score}/100 [{inc.risk_assessment.severity}]")


def run_ingest_file(filepath: str):
    print_banner()
    p = Path(filepath)
    if not p.exists():
        logger.error(f"File not found: {filepath}")
        sys.exit(1)

    pipeline = get_pipeline()
    content = p.read_text(encoding="utf-8")
    
    # Check if multiple lines or single JSON
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    logger.info(f"Ingesting file {filepath} ({len(lines)} lines)")
    
    for i, line in enumerate(lines, 1):
        inc = pipeline.process_raw(line)
        print(f"[{i}/{len(lines)}] Alert: {inc.alert.title} | Risk: {inc.risk_assessment.score} ({inc.risk_assessment.severity}) | Action: {inc.response_action.action_type if inc.response_action else 'NONE'}")


def print_viva_qa():
    print_banner()
    print("""
========================================================================
           VIVA PREPARATION QUESTIONS & DEFENSE ANSWERS
========================================================================

Q1: What is a SOC?
A: A Security Operations Center is a centralized function or facility
   responsible for continuously monitoring, detecting, investigating, and
   responding to security events across endpoint and network assets.

Q2: What is SIEM?
A: Security Information and Event Management aggregates logs, normalizes them,
   correlates security events against detection rules, and triggers alerts.

Q3: Why Wazuh?
A: Wazuh provides open-source unified endpoint security monitoring,
   log analysis, file integrity monitoring, vulnerability detection, and alerting.

Q4: What is Suricata?
A: An open-source high-performance network threat detection engine providing
   IDS (Intrusion Detection), IPS (Intrusion Prevention), and network telemetry.

Q5: What is Threat Hunting?
A: A proactive, hypothesis-driven process of searching security data for stealthy
   adversary activity or IOCs that bypassed automated controls.

Q6: Why use Threat Intelligence?
A: It enriches indicators (IPs, hashes, domains) with external context, known
   malicious behavior, and historical reputation scores (e.g. AbuseIPDB).

Q7: Why AI?
A: AI assists Tier-1/2 analysts by summarizing complex alerts in analyst-friendly
   language, classifying attack categories, mapping to MITRE ATT&CK, and
   recommending investigation and response steps in seconds.

Q8: Is the SOC fully autonomous?
A: No. The system is semi-autonomous. AI is advisory, while deterministic
   rules and response policies control high-impact containment actions
   (e.g., temporary UFW firewall blocks) to prevent accidental outages.

Q9: Why use a risk engine if AI already gives a severity?
A: A deterministic risk engine makes response decisions transparent,
   repeatable, auditable, and less dependent on probabilistic LLM output.

Q10: What happens when an alert arrives?
A: The alert is ingested, parsed, normalized, enriched with threat intel,
   evaluated by the deterministic risk engine, investigated by the AI layer,
   checked against response policy, and then contained or recorded.
========================================================================
""")


def main():
    settings = get_settings()
    default_host = os.environ.get("HOST", settings.HOST)
    default_port = int(os.environ.get("PORT", str(settings.PORT)))

    parser = argparse.ArgumentParser(
        description="AI Cyberthreat Hunting & Autonomous SOC Command Engine"
    )
    parser.add_argument("--serve", action="store_true", help="Start the FastAPI Web Command Center Dashboard")
    parser.add_argument("--host", default=default_host, help="Host address for web server (default: from HOST env or 0.0.0.0)")
    parser.add_argument("--port", type=int, default=default_port, help="Port for web server (default: from PORT env or 8000)")
    parser.add_argument("--simulate", choices=["A", "B", "C", "D", "all"], help="Run attack simulation workflow")
    parser.add_argument("--ingest", type=str, help="Ingest a log file or JSON alerts file")
    parser.add_argument("--viva", action="store_true", help="Display Final Year Viva Q&A Guide")

    args = parser.parse_args()

    if args.simulate:
        run_simulation(args.simulate)
    elif args.ingest:
        run_ingest_file(args.ingest)
    elif args.viva:
        print_viva_qa()
    else:
        # Default behavior: run server
        run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
