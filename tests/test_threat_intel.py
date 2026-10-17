import pytest
from ai_soc.threat_intel.reputation import ThreatIntelEngine


def test_private_loopback_ip_handling():
    engine = ThreatIntelEngine()
    result = engine.lookup_ip("127.0.0.1")
    assert result.is_whitelisted is True
    assert result.abuse_confidence_score == 0
    assert result.is_malicious is False

    result_lan = engine.lookup_ip("192.168.1.50")
    assert result_lan.is_whitelisted is True
    assert result_lan.abuse_confidence_score == 0


def test_mock_threat_intel_known_malicious():
    engine = ThreatIntelEngine()
    result = engine.lookup_ip("198.51.100.42")
    assert result.is_malicious is True
    assert result.abuse_confidence_score >= 80
    assert "SSH Brute Force" in result.threat_tags


def test_caching_behavior():
    engine = ThreatIntelEngine()
    ip = "45.33.32.156"
    res1 = engine.lookup_ip(ip)
    assert res1.cached is False

    res2 = engine.lookup_ip(ip)
    assert res2.cached is True
    assert res2.indicator == ip
