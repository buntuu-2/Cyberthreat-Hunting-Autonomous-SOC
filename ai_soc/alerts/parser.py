import json
import re
from typing import Dict, Any, Tuple, Optional


class AlertParser:
    """Parses raw security events from Wazuh, Suricata, Linux auth.log, or JSON feeds."""

    # Regex patterns for Linux auth.log
    SSH_FAILED_PATTERN = re.compile(
        r"Failed password for (invalid user )?(?P<user>\S+) from (?P<ip>\d{1,3}(?:\.\d{1,3}){3}) port (?P<port>\d+)"
    )
    SSH_ACCEPTED_PATTERN = re.compile(
        r"Accepted (?:password|publickey) for (?P<user>\S+) from (?P<ip>\d{1,3}(?:\.\d{1,3}){3}) port (?P<port>\d+)"
    )
    SUDO_COMMAND_PATTERN = re.compile(
        r"sudo:\s+(?P<user>\S+)\s*:\s*TTY=\S+\s*;\s*PWD=\S+\s*;\s*USER=(?P<target_user>\S+)\s*;\s*COMMAND=(?P<command>.*)"
    )

    @classmethod
    def detect_and_parse(cls, raw_input: Any) -> Tuple[str, Dict[str, Any]]:
        """Detect the source format and parse into an intermediate dictionary."""
        if isinstance(raw_input, str):
            raw_input = raw_input.strip()
            if not raw_input:
                raise ValueError("Empty input string")
            
            # Check if JSON
            if raw_input.startswith("{") and raw_input.endswith("}"):
                try:
                    data = json.loads(raw_input)
                    return cls._detect_json_source(data), data
                except json.JSONDecodeError:
                    pass
            
            # Try auth.log parsing
            parsed_log = cls.parse_auth_log_line(raw_input)
            if parsed_log:
                return "syslog", parsed_log
            
            # Generic text fallback
            return "generic", {"raw_log": raw_input}

        elif isinstance(raw_input, dict):
            return cls._detect_json_source(raw_input), raw_input

        raise ValueError(f"Unsupported event type: {type(raw_input)}")

    @classmethod
    def _detect_json_source(cls, data: Dict[str, Any]) -> str:
        # Wazuh alert fingerprint: has "rule" and "agent" or "decoder"
        if "rule" in data and ("agent" in data or "decoder" in data or "wazuh" in str(data)):
            return "wazuh"
        
        # Suricata EVE fingerprint: has "event_type" and ("alert" in data or "src_ip" in data)
        if "event_type" in data or ("src_ip" in data and "dest_ip" in data and "proto" in data):
            return "suricata"
        
        if "source" in data and data["source"] in ["wazuh", "suricata", "syslog", "synthetic"]:
            return data["source"]

        return "synthetic"

    @classmethod
    def parse_auth_log_line(cls, line: str) -> Optional[Dict[str, Any]]:
        """Extract structured fields from /var/log/auth.log lines."""
        match_failed = cls.SSH_FAILED_PATTERN.search(line)
        if match_failed:
            groups = match_failed.groupdict()
            return {
                "event_type": "auth_failure",
                "source_ip": groups.get("ip"),
                "source_port": int(groups.get("port", 0)),
                "target_user": groups.get("user"),
                "title": f"SSH Authentication Failure for user {groups.get('user')}",
                "description": f"Failed SSH password attempt from {groups.get('ip')} for account {groups.get('user')}",
                "raw_log": line
            }

        match_accepted = cls.SSH_ACCEPTED_PATTERN.search(line)
        if match_accepted:
            groups = match_accepted.groupdict()
            return {
                "event_type": "auth_success",
                "source_ip": groups.get("ip"),
                "source_port": int(groups.get("port", 0)),
                "target_user": groups.get("user"),
                "title": f"SSH Authentication Succeeded for user {groups.get('user')}",
                "description": f"Accepted SSH login from {groups.get('ip')} for account {groups.get('user')}",
                "raw_log": line
            }

        match_sudo = cls.SUDO_COMMAND_PATTERN.search(line)
        if match_sudo:
            groups = match_sudo.groupdict()
            return {
                "event_type": "privilege_escalation",
                "target_user": groups.get("target_user"),
                "invoking_user": groups.get("user"),
                "command": groups.get("command"),
                "title": f"Privileged Sudo Execution by {groups.get('user')}",
                "description": f"User {groups.get('user')} executed command as {groups.get('target_user')}: {groups.get('command')}",
                "raw_log": line
            }

        return None
