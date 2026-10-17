import os
from pathlib import Path
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Central configuration for AI Cyberthreat Hunting & Autonomous SOC."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # General
    ENV_MODE: str = "development"
    PROJECT_NAME: str = "AI Cyberthreat Hunting & Autonomous SOC"
    VERSION: str = "1.0.0"

    # Threat Intelligence APIs
    ABUSEIPDB_API_KEY: str = ""
    VIRUSTOTAL_API_KEY: str = ""
    MOCK_THREAT_INTEL: bool = True

    # AI Analyzer Configuration
    LLM_PROVIDER: str = "mock"  # "mock" | "gemini" | "openai" | "ollama"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # Risk Scoring Weights (Section 9 of Project Roadmap)
    POINTS_REPEATED_FAILED_LOGINS: int = 20
    POINTS_PRIVILEGED_ACCOUNT: int = 20
    POINTS_MALICIOUS_IP_REPUTATION: int = 30
    POINTS_REPEATED_BEHAVIOR: int = 15
    POINTS_SUCCESS_AFTER_FAILURE: int = 30

    # Risk Thresholds
    RISK_THRESHOLD_LOW: int = 30
    RISK_THRESHOLD_MEDIUM: int = 60
    RISK_THRESHOLD_HIGH: int = 80

    # Autonomous Response Configuration (Module 7)
    AUTO_RESPONSE_ENABLED: bool = True
    MIN_SEVERITY_AUTO_BLOCK: str = "HIGH"  # "MEDIUM", "HIGH", "CRITICAL"
    DEFAULT_BLOCK_TTL_SECONDS: int = 300   # 5 minutes temporary block
    ALLOWLISTED_IPS: str = "127.0.0.1,::1,192.168.1.1,10.0.0.1,localhost"
    FIREWALL_MODE: str = "simulation"       # "simulation" or "ufw"

    # Server / Dashboard
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Data Storage Directories
    DATA_DIR: Path = BASE_DIR / "data"
    REPORTS_DIR: Path = BASE_DIR / "data" / "reports"
    LOGS_DIR: Path = BASE_DIR / "data" / "logs"

    @property
    def allowlist_set(self) -> set[str]:
        return {ip.strip() for ip in self.ALLOWLISTED_IPS.split(",") if ip.strip()}


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return settings
