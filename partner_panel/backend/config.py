"""
Partner Panel Configuration

Uses only PARTNER_PANEL_ prefixed environment variables
"""
import os


class Settings:
    """Partner Panel settings from environment variables"""

    def __init__(self):
        # Telegram Bot (для Mini App)
        self.bot_token: str = os.getenv("PARTNER_PANEL_BOT_TOKEN", "")

        # Database
        self.database_url: str = os.getenv(
            "PARTNER_PANEL_DATABASE_URL",
            "postgresql+asyncpg://postgres:password@localhost:5432/nl_international"
        )

        # API
        self.api_host: str = os.getenv("PARTNER_PANEL_API_HOST", "0.0.0.0")
        self.api_port: int = int(os.getenv("PARTNER_PANEL_API_PORT", "8000"))
        self.api_prefix: str = os.getenv("PARTNER_PANEL_API_PREFIX", "/api/v1")

        # Security
        self.secret_key: str = os.getenv("PARTNER_PANEL_SECRET_KEY", "change-me-in-production")

        # Telethon defaults
        self.default_api_id: int = int(os.getenv("PARTNER_PANEL_DEFAULT_API_ID", "0"))
        self.default_api_hash: str = os.getenv("PARTNER_PANEL_DEFAULT_API_HASH", "")

        # Mini App URL
        self.mini_app_url: str = os.getenv("PARTNER_PANEL_MINI_APP_URL", "https://apexflow01.ru")

        # CORS
        cors_str = os.getenv("PARTNER_PANEL_CORS_ORIGINS", "*")
        self.cors_origins: list[str] = [s.strip() for s in cors_str.split(",")]


settings = Settings()
