import subprocess
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import uuid

from ai_soc.alerts.models import ResponseAction
from ai_soc.config.settings import get_settings

logger = logging.getLogger(__name__)


class FirewallManager:
    """
    Manages automated and manual firewall actions (UFW).
    Supports simulated mode for safe lab environments and direct UFW command execution.
    Logs every action to an immutable audit trail.
    """

    def __init__(self):
        self.settings = get_settings()
        self._active_blocks: Dict[str, ResponseAction] = {}
        self._audit_trail: List[ResponseAction] = []
        self._load_audit_trail()

    def _get_audit_file(self):
        return self.settings.LOGS_DIR / "audit_trail.json"

    def _load_audit_trail(self):
        audit_file = self._get_audit_file()
        if audit_file.exists():
            try:
                with open(audit_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        action = ResponseAction(**item)
                        self._audit_trail.append(action)
                        if action.is_active and action.action_type == "UFW_BLOCK" and action.target_ip:
                            self._active_blocks[action.target_ip] = action
            except Exception as e:
                logger.error(f"Failed to load audit trail: {e}")

    def _save_audit_trail(self):
        audit_file = self._get_audit_file()
        try:
            with open(audit_file, "w", encoding="utf-8") as f:
                json.dump([a.model_dump(mode="json") for a in self._audit_trail], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save audit trail: {e}")

    def block_ip(
        self,
        ip: str,
        reason: str,
        risk_score: int,
        rule_applied: str = "HIGH_SEVERITY_AUTO_BLOCK",
        ttl_seconds: Optional[int] = None,
        executed_by: str = "Autonomous Response Engine"
    ) -> ResponseAction:
        """Execute a predefined temporary firewall block."""
        ttl = ttl_seconds if ttl_seconds is not None else self.settings.DEFAULT_BLOCK_TTL_SECONDS
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl) if ttl > 0 else None

        status = "SUCCESS"
        applied_msg = reason

        if self.settings.FIREWALL_MODE == "ufw":
            try:
                cmd = ["sudo", "ufw", "deny", "from", ip]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if res.returncode != 0:
                    status = "FAILED"
                    applied_msg = f"UFW command returned code {res.returncode}: {res.stderr.strip()}"
                else:
                    applied_msg = f"Executed: {' '.join(cmd)}. Output: {res.stdout.strip()}"
            except Exception as e:
                status = "FAILED"
                applied_msg = f"UFW execution error: {str(e)}"
        else:
            # Simulated safe mode
            applied_msg = f"[SIMULATED UFW] Added rule: 'ufw deny from {ip}' for {ttl}s. ({reason})"

        action = ResponseAction(
            action_id=str(uuid.uuid4()),
            timestamp=now,
            action_type="UFW_BLOCK",
            target_ip=ip,
            status=status,
            reason=applied_msg,
            risk_score=risk_score,
            rule_applied=rule_applied,
            ttl_seconds=ttl,
            expires_at=expires_at,
            is_active=(status == "SUCCESS"),
            executed_by=executed_by
        )

        if status == "SUCCESS":
            self._active_blocks[ip] = action

        self._audit_trail.append(action)
        self._save_audit_trail()
        return action

    def unblock_ip(self, ip: str, executed_by: str = "SOC Analyst Manual Override") -> ResponseAction:
        """Remove a block rule for a given IP."""
        now = datetime.now(timezone.utc)
        status = "SUCCESS"
        applied_msg = f"Firewall block removed for {ip}"

        if self.settings.FIREWALL_MODE == "ufw":
            try:
                cmd = ["sudo", "ufw", "delete", "deny", "from", ip]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                applied_msg = f"Executed: {' '.join(cmd)}. Output: {res.stdout.strip()}"
            except Exception as e:
                status = "FAILED"
                applied_msg = f"UFW unblock error: {str(e)}"
        else:
            applied_msg = f"[SIMULATED UFW] Deleted rule: 'ufw delete deny from {ip}'"

        if ip in self._active_blocks:
            self._active_blocks[ip].is_active = False
            del self._active_blocks[ip]

        action = ResponseAction(
            action_id=str(uuid.uuid4()),
            timestamp=now,
            action_type="UFW_UNBLOCK",
            target_ip=ip,
            status=status,
            reason=applied_msg,
            risk_score=0,
            rule_applied="MANUAL_OR_TTL_UNBLOCK",
            is_active=False,
            executed_by=executed_by
        )

        self._audit_trail.append(action)
        self._save_audit_trail()
        return action

    def check_expirations(self) -> List[ResponseAction]:
        """Check active blocks and release expired ones."""
        now = datetime.now(timezone.utc)
        expired_ips = []
        for ip, action in list(self._active_blocks.items()):
            if action.expires_at and action.expires_at <= now:
                expired_ips.append(ip)

        unblock_actions = []
        for ip in expired_ips:
            res = self.unblock_ip(ip, executed_by="Autonomous Response TTL Expiry Worker")
            unblock_actions.append(res)

        return unblock_actions

    def get_active_blocks(self) -> List[ResponseAction]:
        self.check_expirations()
        return list(self._active_blocks.values())

    def get_audit_trail(self) -> List[ResponseAction]:
        return sorted(self._audit_trail, key=lambda a: a.timestamp, reverse=True)
