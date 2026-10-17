import json
import logging
from typing import List, Optional
from datetime import datetime

from ai_soc.alerts.models import IncidentRecord
from ai_soc.config.settings import get_settings

logger = logging.getLogger(__name__)


class IncidentStore:
    """Stores incident records in memory and syncs to disk for persistence."""

    def __init__(self):
        self.settings = get_settings()
        self._incidents: List[IncidentRecord] = []
        self._load_from_disk()

    def _get_storage_file(self):
        return self.settings.DATA_DIR / "incidents.json"

    def _load_from_disk(self):
        filepath = self._get_storage_file()
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        self._incidents.append(IncidentRecord(**item))
            except Exception as e:
                logger.error(f"Error loading incidents from disk: {e}")

    def save(self, incident: IncidentRecord):
        self._incidents.insert(0, incident)  # newest first
        # Keep latest 500 incidents in memory
        if len(self._incidents) > 500:
            self._incidents = self._incidents[:500]

        filepath = self._get_storage_file()
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump([inc.model_dump(mode="json") for inc in self._incidents[:100]], f, indent=2)
        except Exception as e:
            logger.error(f"Error saving incidents to disk: {e}")

    def get_all(self, limit: int = 100) -> List[IncidentRecord]:
        return self._incidents[:limit]

    def get_by_id(self, incident_id: str) -> Optional[IncidentRecord]:
        for inc in self._incidents:
            if inc.incident_id == incident_id:
                return inc
        return None

    def clear(self):
        self._incidents.clear()
        filepath = self._get_storage_file()
        if filepath.exists():
            try:
                filepath.unlink()
            except Exception:
                pass
