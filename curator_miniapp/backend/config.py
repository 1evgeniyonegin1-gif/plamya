"""
Curator Mini App Configuration

Настройки для Mini App куратора
"""
import os


class Settings:
    """Curator Mini App settings from environment variables"""

    def __init__(self):
        # Telegram Bot (для Mini App auth)
        self.bot_token: str = os.getenv("CURATOR_BOT_TOKEN", "")

        # Database (используем ту же БД что и curator_bot)
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:password@localhost:5432/nl_international"
        )

        # API
        self.api_host: str = os.getenv("CURATOR_MINIAPP_API_HOST", "0.0.0.0")
        self.api_port: int = int(os.getenv("CURATOR_MINIAPP_API_PORT", "8002"))
        self.api_prefix: str = os.getenv("CURATOR_MINIAPP_API_PREFIX", "/api/v1")

        # Security
        self.secret_key: str = os.getenv(
            "CURATOR_MINIAPP_SECRET_KEY",
            os.getenv("PARTNER_PANEL_SECRET_KEY", "change-me-in-production")
        )

        # Mini App URL
        self.mini_app_url: str = os.getenv("CURATOR_MINIAPP_URL", "https://curator.apexflow01.ru")

        # CORS
        cors_str = os.getenv("CURATOR_MINIAPP_CORS_ORIGINS", "*")
        self.cors_origins: list[str] = [s.strip() for s in cors_str.split(",")]

        # Referral links
        self.referral_registration: str = "https://nlstar.com/ref/eiPusg/"
        self.referral_catalog: str = "https://nlstar.com/ref/q9zfpK/"
        self.referral_promo: str = "https://nlstar.com/ref/ZQaq98/"
        self.referral_new_products: str = "https://nlstar.com/ref/djUFSb/"
        self.referral_starter_kits: str = "https://nlstar.com/ref/tjWAvH/"

        # Contact for CTA
        self.business_contact_username: str = os.getenv("BUSINESS_CONTACT_USERNAME", "DanilLysenkoNL")
        self.owner_telegram_id: int = int(os.getenv("ADMIN_TELEGRAM_IDS", "756877849").split(",")[0])


settings = Settings()
