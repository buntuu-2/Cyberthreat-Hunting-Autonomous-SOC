from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid

from ai_soc.alerts.models import NormalizedAlert


PRIVILEGED_USERS = {
    "root", "admin", "administrator", "wheel", "sudo", "shadow", "bin", "daemon", "operator"
}


class AlertNormalizer:
    """Normalizes raw parsed data from various security tools into a standard NormalizedAlert."""

    @classmethod
    def normalize(cls, source: str, data: Dict[str, Any]) -> NormalizedAlert:
        if source == "wazuh":
            return cls._normalize_wazuh(data)
        elif source == "suricata":
            return cls._normalize_suricata(data)
        elif source == "syslog":
            return cls._normalize_syslog(data)
        else:
            return cls._normalize_generic(source, data)

    @classmethod
    def _normalize_wazuh(cls, data: Dict[str, Any]) -> NormalizedAlert:
        rule = data.get("rule", {})
        rule_id = str(rule.get("id", ""))
        rule_desc = rule.get("description", "Wazuh Security Alert")
        raw_level = rule.get("level", 1)
        
        # Check inner data object
        inner_data = data.get("data", {})
        src_ip = inner_data.get("srcip") or data.get("src_ip")
        dst_ip = inner_data.get("dstip") or data.get("dest_ip")
        src_port = inner_data.get("srcport") or data.get("src_port")
        dst_port = inner_data.get("dstport") or data.get("dest_port")
        user = inner_data.get("dstuser") or inner_data.get("srcuser") or data.get("user")
        
        # Fallback to extracting from full_log if srcip is not in inner_data
        full_log = data.get("full_log", "")
        if not src_ip and full_log:
            import re
            ip_match = re.search(r"from\s+(\d{1,3}(?:\.\d{1,3}){3})", full_log)
            if ip_match:
                src_ip = ip_match.group(1)
        if not user and full_log:
            import re
            user_match = re.search(r"for\s+(?:invalid user\s+)?(\S+)\s+from", full_log)
            if user_match:
                user = user_match.group(1)

        # Classify event type from Wazuh rule groups/description
        groups = rule.get("groups", [])
        groups_str = " ".join(groups).lower() + " " + rule_desc.lower()
        
        if "brute" in groups_str or "multiple failed" in groups_str or int(rule_id or 0) in [5712, 5710, 5716]:
            event_type = "brute_force"
        elif "authentication_failed" in groups_str or "failed" in groups_str or int(rule_id or 0) in [5710, 5503]:
            event_type = "auth_failure"
        elif "portscan" in groups_str or "scan" in groups_str:
            event_type = "port_scan"
        elif "privilege" in groups_str or "sudo" in groups_str:
            event_type = "privilege_escalation"
        else:
            event_type = "generic"

        is_privileged = bool(user and str(user).lower() in PRIVILEGED_USERS)

        return NormalizedAlert(
            alert_id=str(data.get("id", uuid.uuid4())),
            timestamp=cls._parse_timestamp(data.get("timestamp")),
            source="wazuh",
            event_type=event_type,
            title=rule_desc,
            description=f"Wazuh Rule {rule_id} triggered (Level {raw_level}): {rule_desc}",
            source_ip=src_ip,
            destination_ip=dst_ip,
            source_port=int(src_port) if src_port else None,
            destination_port=int(dst_port) if dst_port else None,
            protocol=data.get("protocol", "TCP"),
            target_user=user,
            is_privileged_user=is_privileged,
            hostname=data.get("agent", {}).get("name", "ubuntu-endpoint"),
            rule_id=rule_id,
            rule_description=rule_desc,
            raw_severity=raw_level,
            raw_log=full_log or str(data),
            metadata={"agent": data.get("agent", {}), "decoder": data.get("decoder", {})}
        )

    @classmethod
    def _normalize_suricata(cls, data: Dict[str, Any]) -> NormalizedAlert:
        alert_info = data.get("alert", {})
        signature = alert_info.get("signature", "Suricata Network IDS Alert")
        signature_id = str(alert_info.get("signature_id", ""))
        severity = alert_info.get("severity", 3)
        category = alert_info.get("category", "")
        
        sig_lower = (signature + " " + category).lower()
        if "scan" in sig_lower or "nmap" in sig_lower:
            event_type = "port_scan"
        elif "brute" in sig_lower or "ssh" in sig_lower:
            event_type = "brute_force"
        elif "dos" in sig_lower or "flood" in sig_lower:
            event_type = "dos"
        else:
            event_type = "malicious_traffic"

        return NormalizedAlert(
            alert_id=str(uuid.uuid4()),
            timestamp=cls._parse_timestamp(data.get("timestamp")),
            source="suricata",
            event_type=event_type,
            title=signature,
            description=f"Suricata IDS Alert [{category}]: {signature}",
            source_ip=data.get("src_ip"),
            destination_ip=data.get("dest_ip"),
            source_port=data.get("src_port"),
            destination_port=data.get("dest_port"),
            protocol=data.get("proto", "TCP"),
            target_user=None,
            is_privileged_user=False,
            hostname=data.get("host", "sensor-node"),
            rule_id=signature_id,
            rule_description=signature,
            raw_severity=severity,
            raw_log=str(data),
            metadata={"category": category, "payload": data.get("payload_printable", "")}
        )

    @classmethod
    def _normalize_syslog(cls, data: Dict[str, Any]) -> NormalizedAlert:
        event_type = data.get("event_type", "generic")
        user = data.get("target_user")
        is_privileged = bool(user and str(user).lower() in PRIVILEGED_USERS)

        return NormalizedAlert(
            alert_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            source="syslog",
            event_type=event_type,
            title=data.get("title", "Linux System Log Event"),
            description=data.get("description", "Auth or system log notification"),
            source_ip=data.get("source_ip"),
            source_port=data.get("source_port"),
            target_user=user,
            is_privileged_user=is_privileged,
            raw_log=data.get("raw_log", "")
        )

    @classmethod
    def _normalize_generic(cls, source: str, data: Dict[str, Any]) -> NormalizedAlert:
        user = data.get("target_user") or data.get("user")
        is_privileged = bool(user and str(user).lower() in PRIVILEGED_USERS)

        return NormalizedAlert(
            alert_id=str(data.get("alert_id") or uuid.uuid4()),
            timestamp=cls._parse_timestamp(data.get("timestamp")),
            source=source or "synthetic",
            event_type=data.get("event_type", "generic"),
            title=data.get("title", "Security Alert"),
            description=data.get("description", "Event generated or normalized from generic data source"),
            source_ip=data.get("source_ip") or data.get("src_ip"),
            destination_ip=data.get("destination_ip") or data.get("dest_ip"),
            source_port=data.get("source_port") or data.get("src_port"),
            destination_port=data.get("destination_port") or data.get("dest_port"),
            protocol=data.get("protocol", "TCP"),
            target_user=user,
            is_privileged_user=is_privileged,
            hostname=data.get("hostname", "ubuntu-endpoint"),
            rule_id=str(data.get("rule_id", "0")),
            rule_description=data.get("rule_description", ""),
            raw_severity=data.get("raw_severity", 1),
            raw_log=data.get("raw_log", str(data)),
            metadata=data.get("metadata", {})
        )

    @staticmethod
    def _parse_timestamp(ts: Any) -> datetime:
        if not ts:
            return datetime.now(timezone.utc)
        if isinstance(ts, datetime):
            return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        try:
            # ISO 8601 parsing
            clean_ts = str(ts).replace("Z", "+00:00")
            return datetime.fromisoformat(clean_ts)
        except Exception:
            return datetime.now(timezone.utc)
