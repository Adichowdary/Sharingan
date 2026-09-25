"""
PhishGuard Configuration
"""
import os
import secrets


class Settings:
    """Application settings loaded from environment variables with defaults."""

    PROJECT_NAME: str = "PhishGuard"
    VERSION: str = "2.0.0"
    DESCRIPTION: str = "Phishing Simulation & Security Analysis Platform"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./phishguard.db")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_hex(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Server
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Campaign defaults
    DEFAULT_CAMPAIGN_EXPIRY_HOURS: int = 72
    MAX_TARGETS_PER_CAMPAIGN: int = 500

    # SMTP / Email Notifications (env-var based fallback)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    NOTIFICATION_FROM: str = os.getenv("NOTIFICATION_FROM", "")

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    NOTIFICATION_COOLDOWN_SECONDS: int = int(os.getenv("NOTIFICATION_COOLDOWN_SECONDS", "30"))


settings = Settings()
