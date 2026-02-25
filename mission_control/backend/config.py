"""
Mission Control Configuration

Uses @Alrton_bot token for Mini App auth.
"""
import os


class Settings:
    """Mission Control settings from environment variables."""

    def __init__(self):
        self.bot_token: str = os.getenv(
            "MISSION_CONTROL_BOT_TOKEN",
            "",
        )
        self.api_host: str = os.getenv("MISSION_CONTROL_API_HOST", "0.0.0.0")
        self.api_port: int = int(os.getenv("MISSION_CONTROL_API_PORT", "8006"))
        self.api_prefix: str = "/api/v1"
        self.secret_key: str = os.getenv(
            "MISSION_CONTROL_SECRET_KEY",
            os.getenv("PARTNER_PANEL_SECRET_KEY", "change-me-in-production"),
        )
        self.admin_ids: list[int] = [756877849]
        cors_str = os.getenv("MISSION_CONTROL_CORS_ORIGINS", "*")
        self.cors_origins: list[str] = [s.strip() for s in cors_str.split(",")]
        self.plamya_dir: str = os.getenv(
            "PLAMYA_HOME",
            os.path.expanduser("~/.plamya"),
        )


settings = Settings()
