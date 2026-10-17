import ipaddress
import time
from typing import Dict, Optional
import requests

from ai_soc.alerts.models import ThreatIntelResult
from ai_soc.config.settings import get_settings


# Curated realistic mock database for lab simulations and viva defense
MOCK_THREAT_DATABASE = {
    "198.51.100.42": {
        "abuse_score": 95,
        "is_malicious": True,
        "country_code": "RU",
        "country_name": "Russian Federation",
        "isp": "Mir Telematics Ltd",
        "usage_type": "Data Center / VPN / Proxy",
        "total_reports": 184,
        "threat_tags": ["SSH Brute Force", "Port Scanner", "Bad Bot"],
        "is_whitelisted": False,
    },
    "45.33.32.156": {
        "abuse_score": 88,
        "is_malicious": True,
        "country_code": "US",
        "country_name": "United States",
        "isp": "Linode LLC",
        "usage_type": "Hosting Provider",
        "total_reports": 92,
        "threat_tags": ["Nmap Scan", "SYN Flood", "Reconnaissance"],
        "is_whitelisted": False,
    },
    "185.220.101.5": {
        "abuse_score": 98,
        "is_malicious": True,
        "country_code": "DE",
        "country_name": "Germany",
        "isp": "Zwiebelfreunde e.V.",
        "usage_type": "Tor Exit Node",
        "total_reports": 412,
        "threat_tags": ["Tor Exit Node", "Anonymizer", "Exploit Prober"],
        "is_whitelisted": False,
    },
    "203.0.113.195": {
        "abuse_score": 55,
        "is_malicious": False,
        "country_code": "NL",
        "country_name": "Netherlands",
        "isp": "Cloud Provider B.V.",
        "usage_type": "Shared Hosting",
        "total_reports": 14,
        "threat_tags": ["Suspicious Activity"],
        "is_whitelisted": False,
    },
    "8.8.8.8": {
        "abuse_score": 0,
        "is_malicious": False,
        "country_code": "US",
        "country_name": "United States",
        "isp": "Google LLC",
        "usage_type": "Public DNS",
        "total_reports": 0,
        "threat_tags": ["Verified Public DNS"],
        "is_whitelisted": True,
    },
    "1.1.1.1": {
        "abuse_score": 0,
        "is_malicious": False,
        "country_code": "US",
        "country_name": "United States",
        "isp": "Cloudflare Inc.",
        "usage_type": "Public DNS",
        "total_reports": 0,
        "threat_tags": ["Verified Public DNS"],
        "is_whitelisted": True,
    }
}


class ThreatIntelEngine:
    """Enriches IP indicators with reputation, country, ISP, and abuse confidence."""

    def __init__(self):
        self.settings = get_settings()
        self._cache: Dict[str, ThreatIntelResult] = {}

    def is_private_or_loopback(self, ip_str: str) -> bool:
        """Check if an IP is local, loopback, or RFC 1918 private."""
        try:
            ip = ipaddress.ip_address(ip_str.strip())
            # Don't treat RFC 5737 test-nets (198.51.100.x, 203.0.113.x) as local if in mock database
            if ip_str.strip() in MOCK_THREAT_DATABASE:
                return False
            # Truly private: loopback (127.0.0.0/8) or RFC 1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
            return ip.is_loopback or ip.is_private
        except ValueError:
            return True

    def lookup_ip(self, ip_str: Optional[str]) -> ThreatIntelResult:
        """Query reputation info for an IP address with caching and fallback."""
        if not ip_str:
            return ThreatIntelResult(
                indicator="N/A",
                indicator_type="ip",
                abuse_confidence_score=0,
                is_malicious=False,
                is_whitelisted=True,
                isp="Internal / Not Available",
                details="No source IP indicator provided."
            )

        ip_clean = ip_str.strip()

        # Check Cache
        if ip_clean in self._cache:
            cached_result = self._cache[ip_clean].model_copy()
            cached_result.cached = True
            return cached_result

        # Check explicit mock database first (for curated test indicators)
        if ip_clean in MOCK_THREAT_DATABASE:
            mock_result = self._query_mock_db(ip_clean)
            self._cache[ip_clean] = mock_result
            return mock_result

        # Handle Internal / Loopback IPs safely
        if self.is_private_or_loopback(ip_clean):
            result = ThreatIntelResult(
                indicator=ip_clean,
                indicator_type="ip",
                abuse_confidence_score=0,
                is_malicious=False,
                is_whitelisted=True,
                country_code="LOCAL",
                country_name="Private Subnet",
                isp="Local Area Network / Loopback",
                usage_type="RFC 1918 Private / Loopback",
                total_reports=0,
                threat_tags=["Internal Network"],
                source_provider="Local Filter"
            )
            self._cache[ip_clean] = result
            return result

        # If live API key is configured and mock mode is disabled, query AbuseIPDB
        if self.settings.ABUSEIPDB_API_KEY and not self.settings.MOCK_THREAT_INTEL:
            try:
                live_result = self._query_abuseipdb(ip_clean)
                self._cache[ip_clean] = live_result
                return live_result
            except Exception as e:
                # Fall back gracefully on network or rate limit errors
                pass

        # Use mock / offline threat intel database
        mock_result = self._query_mock_db(ip_clean)
        self._cache[ip_clean] = mock_result
        return mock_result

    def _query_mock_db(self, ip_str: str) -> ThreatIntelResult:
        if ip_str in MOCK_THREAT_DATABASE:
            entry = MOCK_THREAT_DATABASE[ip_str]
            return ThreatIntelResult(
                indicator=ip_str,
                indicator_type="ip",
                abuse_confidence_score=entry["abuse_score"],
                is_malicious=entry["is_malicious"],
                is_whitelisted=entry["is_whitelisted"],
                country_code=entry["country_code"],
                country_name=entry["country_name"],
                isp=entry["isp"],
                usage_type=entry["usage_type"],
                total_reports=entry["total_reports"],
                last_reported_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                threat_tags=entry["threat_tags"],
                source_provider="Simulated Threat Intel / AbuseIPDB"
            )

        # Deterministic simulation for arbitrary public IPs
        # Produce consistent hash-based reputation for unrecognized public IPs
        val = sum(ord(c) for c in ip_str) % 100
        is_mal = val >= 70
        return ThreatIntelResult(
            indicator=ip_str,
            indicator_type="ip",
            abuse_confidence_score=val if is_mal else 15,
            is_malicious=is_mal,
            is_whitelisted=False,
            country_code="US" if val % 2 == 0 else "FR",
            country_name="United States" if val % 2 == 0 else "France",
            isp="Autonomous System AS" + str(1000 + val),
            usage_type="Public IPv4 Host",
            total_reports=val // 3,
            last_reported_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            threat_tags=["Suspicious Host"] if is_mal else ["Standard Traffic"],
            source_provider="Simulated Threat Intel Feed"
        )

    def _query_abuseipdb(self, ip_str: str) -> ThreatIntelResult:
        url = "https://api.abuseipdb.com/api/v2/check"
        querystring = {"ipAddress": ip_str, "maxAgeInDays": "90"}
        headers = {
            "Accept": "application/json",
            "Key": self.settings.ABUSEIPDB_API_KEY
        }
        resp = requests.get(url, headers=headers, params=querystring, timeout=5)
        resp.raise_for_status()
        data = resp.json().get("data", {})

        score = data.get("abuseConfidenceScore", 0)
        return ThreatIntelResult(
            indicator=ip_str,
            indicator_type="ip",
            abuse_confidence_score=score,
            is_malicious=score >= 50,
            is_whitelisted=data.get("isWhitelisted", False),
            country_code=data.get("countryCode", "XX"),
            country_name=data.get("countryName", "Unknown"),
            isp=data.get("isp", "Unknown ISP"),
            usage_type=data.get("usageType", "Commercial"),
            total_reports=data.get("totalReports", 0),
            last_reported_at=data.get("lastReportedAt"),
            threat_tags=["AbuseIPDB Verified"] if score >= 50 else ["Low Risk"],
            source_provider="AbuseIPDB Live API"
        )
