"""
Command Center Configuration

Uses CONTENT_MANAGER_BOT_TOKEN for Mini App auth (same bot).
"""
import os


class Settings:
    """Command Center settings from environment variables"""

    def __init__(self):
        self.bot_token: str = os.getenv("CONTENT_MANAGER_BOT_TOKEN", "")
        self.api_host: str = os.getenv("COMMAND_CENTER_API_HOST", "0.0.0.0")
        self.api_port: int = int(os.getenv("COMMAND_CENTER_API_PORT", "8004"))
        self.api_prefix: str = "/api/v1"
        self.secret_key: str = os.getenv(
            "COMMAND_CENTER_SECRET_KEY",
            os.getenv("PARTNER_PANEL_SECRET_KEY", "change-me-in-production"),
        )
        self.admin_ids: list[int] = [
            int(x.strip())
            for x in os.getenv("ADMIN_TELEGRAM_IDS", "756877849").split(",")
            if x.strip()
        ]
        cors_str = os.getenv("COMMAND_CENTER_CORS_ORIGINS", "*")
        self.cors_origins: list[str] = [s.strip() for s in cors_str.split(",")]


settings = Settings()
