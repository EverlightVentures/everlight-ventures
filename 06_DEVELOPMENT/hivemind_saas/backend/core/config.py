"""
Central settings - loaded from environment variables.
Copy .env.example to .env and fill in values.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    app_name: str = "Everlight Hive Mind"
    environment: str = "development"
    debug: bool = False

    # Database (Supabase Postgres)
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/hivemind"
    supabase_url: str = ""
    supabase_service_key: str = ""

    # Auth (Supabase Auth or Clerk)
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "https://app.everlight.ai"]

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_spark: str = ""    # $49/mo price ID
    stripe_price_hive: str = ""     # $129/mo price ID
    stripe_price_enterprise: str = ""  # $399/mo price ID

    # Slack
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_audit_channel: str = "#hive-audit"
    slack_alerts_channel: str = "#hive-alerts"
    slack_sales_channel: str = "#hive-sales"

    # AI Keys (platform-level, for the hive)
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""

    # Encryption (for storing tenant API keys)
    encryption_key: str = ""  # Fernet key, 32-byte URL-safe base64

    # Redis (for pub/sub and job queues)
    redis_url: str = "redis://localhost:6379"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
