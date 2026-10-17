import pytest
from ai_soc.alerts.parser import AlertParser
from ai_soc.alerts.normalizer import AlertNormalizer


def test_parse_auth_log_failed():
    line = "Oct 15 00:30:14 ubuntu-endpoint sshd[28419]: Failed password for invalid user root from 198.51.100.42 port 49152 ssh2"
    source, parsed = AlertParser.detect_and_parse(line)
    assert source == "syslog"
    assert parsed["source_ip"] == "198.51.100.42"
    assert parsed["target_user"] == "root"
    assert parsed["event_type"] == "auth_failure"

    normalized = AlertNormalizer.normalize(source, parsed)
    assert normalized.source_ip == "198.51.100.42"
    assert normalized.target_user == "root"
    assert normalized.is_privileged_user is True


def test_parse_wazuh_json():
    wazuh_event = {
        "timestamp": "2026-10-15T00:30:15.000Z",
        "rule": {
            "level": 10,
            "description": "sshd: Multiple authentication failures",
            "id": "5712",
            "groups": ["syslog", "sshd", "authentication_failures"]
        },
        "agent": {"name": "ubuntu-lab"},
        "data": {
            "srcip": "198.51.100.42",
            "dstuser": "root"
        }
    }
    source, parsed = AlertParser.detect_and_parse(wazuh_event)
    assert source == "wazuh"
    normalized = AlertNormalizer.normalize(source, parsed)
    assert normalized.source == "wazuh"
    assert normalized.source_ip == "198.51.100.42"
    assert normalized.target_user == "root"
    assert normalized.is_privileged_user is True
    assert normalized.event_type == "brute_force"


def test_parse_suricata_eve_json():
    suricata_event = {
        "event_type": "alert",
        "src_ip": "45.33.32.156",
        "dest_ip": "192.168.1.100",
        "src_port": 54210,
        "dest_port": 80,
        "proto": "TCP",
        "alert": {
            "signature": "ET SCAN Potential Nmap SYN Port Scan",
            "signature_id": 2000537,
            "category": "Attempted Information Leak",
            "severity": 2
        }
    }
    source, parsed = AlertParser.detect_and_parse(suricata_event)
    assert source == "suricata"
    normalized = AlertNormalizer.normalize(source, parsed)
    assert normalized.source == "suricata"
    assert normalized.event_type == "port_scan"
    assert normalized.source_ip == "45.33.32.156"
    assert normalized.destination_port == 80
