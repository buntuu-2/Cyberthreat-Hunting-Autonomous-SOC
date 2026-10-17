import time
import json
import logging
from typing import List
from datetime import datetime, timezone

from ai_soc.alerts.models import IncidentRecord, NormalizedAlert
from ai_soc.pipeline import SOCPipeline, get_pipeline

logger = logging.getLogger(__name__)


class AttackSimulator:
    """
    Simulates controlled laboratory security events for demonstration and viva defense.
    Implements Workflows A, B, and C directly from Roadmap Section 7.
    """

    def __init__(self, pipeline: SOCPipeline = None):
        self.pipeline = pipeline or get_pipeline()

    def run_workflow_a_ssh_bruteforce(
        self,
        attacker_ip: str = "198.51.100.42",
        target_user: str = "root",
        attempts: int = 4
    ) -> List[IncidentRecord]:
        """
        Workflow A: SSH Brute-Force Attack.
        Simulates repeated failed password attempts targeting root,
        causing deterministic risk accumulation and automated UFW block.
        """
        logger.info(f"==> Launching Workflow A: SSH Brute-Force from {attacker_ip} against user '{target_user}'")
        incidents = []

        for i in range(1, attempts + 1):
            raw_log = f"Oct 15 00:30:{10 + i * 2:02d} ubuntu-endpoint sshd[28419]: Failed password for invalid user {target_user} from {attacker_ip} port {49150 + i} ssh2"
            alert = NormalizedAlert(
                source="wazuh",
                event_type="auth_failure" if i < attempts else "brute_force",
                title=f"SSH Authentication Failure (Attempt #{i})",
                description=f"Multiple failed SSH logins detected for user {target_user} from {attacker_ip}",
                source_ip=attacker_ip,
                destination_ip="192.168.1.100",
                source_port=49150 + i,
                destination_port=22,
                protocol="TCP",
                target_user=target_user,
                is_privileged_user=(target_user in ["root", "admin"]),
                hostname="ubuntu-endpoint",
                rule_id="5712" if i == attempts else "5710",
                rule_description="sshd: Brute force / repeated authentication failures" if i == attempts else "sshd: Failed authentication attempt",
                raw_severity=10 if i == attempts else 5,
                raw_log=raw_log
            )
            incident = self.pipeline.process_alert(alert)
            incidents.append(incident)
            time.sleep(0.05)

        logger.info(f"Workflow A Complete. Final Incident: {incidents[-1].incident_id}, Risk: {incidents[-1].risk_assessment.score}/100 [{incidents[-1].risk_assessment.severity}]")
        return incidents

    def run_workflow_b_portscan(
        self,
        scanner_ip: str = "45.33.32.156",
        target_ip: str = "192.168.1.100"
    ) -> IncidentRecord:
        """
        Workflow B: Network Port Scan Detection.
        Simulates Suricata IDS detecting an Nmap SYN reconnaissance scan.
        """
        logger.info(f"==> Launching Workflow B: Port Scan from {scanner_ip}")
        alert = NormalizedAlert(
            source="suricata",
            event_type="port_scan",
            title="ET SCAN Potential Nmap SYN Port Scan Detected",
            description=f"Rapid TCP SYN probes against common service ports detected from {scanner_ip}",
            source_ip=scanner_ip,
            destination_ip=target_ip,
            source_port=54210,
            destination_port=80,
            protocol="TCP",
            hostname="sensor-node-01",
            rule_id="2000537",
            rule_description="ET SCAN Potential Nmap SYN Port Scan Detected",
            raw_severity=2,
            raw_log=f"Suricata EVE IDS alert: signature=ET SCAN Potential Nmap SYN Port Scan src={scanner_ip} dst={target_ip}"
        )
        incident = self.pipeline.process_alert(alert)
        logger.info(f"Workflow B Complete. Incident: {incident.incident_id}, Risk: {incident.risk_assessment.score}/100 [{incident.risk_assessment.severity}]")
        return incident

    def run_workflow_c_threat_intel(
        self,
        indicator_ip: str = "185.220.101.5"
    ) -> IncidentRecord:
        """
        Workflow C: Threat Intelligence Enrichment.
        Simulates inbound connection from known malicious Tor exit node.
        """
        logger.info(f"==> Launching Workflow C: Threat Intelligence Enrichment for {indicator_ip}")
        alert = NormalizedAlert(
            source="suricata",
            event_type="malicious_traffic",
            title="ET CURRENT_EVENTS Tor Exit Node Inbound Traffic",
            description=f"Inbound network session originating from verified Tor Exit Node {indicator_ip}",
            source_ip=indicator_ip,
            destination_ip="192.168.1.100",
            source_port=41209,
            destination_port=443,
            protocol="TCP",
            hostname="sensor-node-01",
            rule_id="2024891",
            rule_description="ET CURRENT_EVENTS Tor Exit Node Traffic Detected",
            raw_severity=1,
            raw_log=f"Suricata alert: Tor exit node connection from {indicator_ip}"
        )
        incident = self.pipeline.process_alert(alert)
        logger.info(f"Workflow C Complete. Incident: {incident.incident_id}, Risk: {incident.risk_assessment.score}/100 [{incident.risk_assessment.severity}]")
        return incident

    def run_workflow_d_credential_compromise(
        self,
        attacker_ip: str = "198.51.100.42",
        compromised_user: str = "root"
    ) -> IncidentRecord:
        """
        Workflow D: Credential Compromise.
        Simulates an accepted login after repeated failures, triggering +30 critical factor.
        """
        # Ensure there are failures first
        self.run_workflow_a_ssh_bruteforce(attacker_ip=attacker_ip, target_user=compromised_user, attempts=3)

        alert = NormalizedAlert(
            source="syslog",
            event_type="auth_success",
            title=f"SSH Login Accepted for user {compromised_user}",
            description=f"Accepted password authentication for {compromised_user} from {attacker_ip}",
            source_ip=attacker_ip,
            destination_ip="192.168.1.100",
            source_port=49156,
            destination_port=22,
            protocol="TCP",
            target_user=compromised_user,
            is_privileged_user=True,
            hostname="ubuntu-endpoint",
            rule_id="5715",
            rule_description="sshd: Authentication successful after multiple failures",
            raw_severity=9,
            raw_log=f"Oct 15 00:30:25 ubuntu-endpoint sshd[28450]: Accepted password for {compromised_user} from {attacker_ip} port 49156 ssh2"
        )
        return self.pipeline.process_alert(alert)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AI SOC Attack Simulator")
    parser.add_argument("--workflow", choices=["A", "B", "C", "D", "all"], default="all")
    args = parser.parse_args()

    simulator = AttackSimulator()

    if args.workflow in ["A", "all"]:
        simulator.run_workflow_a_ssh_bruteforce()
    if args.workflow in ["B", "all"]:
        simulator.run_workflow_b_portscan()
    if args.workflow in ["C", "all"]:
        simulator.run_workflow_c_threat_intel()
    if args.workflow in ["D", "all"]:
        simulator.run_workflow_d_credential_compromise()
