import pytest
from ai_soc.pipeline import SOCPipeline
from simulator.attack_simulator import AttackSimulator


def test_end_to_end_pipeline_workflow_a():
    pipeline = SOCPipeline()
    simulator = AttackSimulator(pipeline=pipeline)

    incidents = simulator.run_workflow_a_ssh_bruteforce(attacker_ip="198.51.100.42", target_user="root", attempts=4)
    assert len(incidents) == 4

    final_incident = incidents[-1]
    assert final_incident.risk_assessment.score >= 80
    assert final_incident.risk_assessment.severity == "CRITICAL"
    assert final_incident.ai_analysis is not None
    assert "SSH" in final_incident.ai_analysis.attack_type
    assert final_incident.response_action is not None
    assert final_incident.response_action.action_type == "UFW_BLOCK"
    assert final_incident.response_action.status == "SUCCESS"

    # Test report generation
    md_report = pipeline.report_generator.generate_markdown(final_incident)
    assert "SECURITY INCIDENT REPORT" in md_report
    assert "198.51.100.42" in md_report
    assert "Deterministic Risk Score Breakdown" in md_report


def test_end_to_end_pipeline_workflow_b():
    pipeline = SOCPipeline()
    simulator = AttackSimulator(pipeline=pipeline)

    incident = simulator.run_workflow_b_portscan(scanner_ip="45.33.32.156")
    assert incident.alert.event_type == "port_scan"
    assert incident.threat_intel is not None
    assert incident.threat_intel.abuse_confidence_score > 50
    assert incident.risk_assessment.score > 30
