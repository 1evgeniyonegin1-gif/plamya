"""
Configuration for Traffic Engine.

Загружает настройки из .env файла.
"""

import random
from typing import Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ===========================================
# SEGMENT CONFIGURATION (Контент-завод Данила)
# ===========================================
# Каждый аккаунт привязан к сегменту → комментирует только в каналах этого сегмента
SEGMENTS: Dict[str, Dict] = {
    "zozh": {
        "name": "ЗОЖ / Питание",
        "profile_suffix": "ЗОЖ",
        "tone": "экспертный, про питание/макросы/добавки, мат умеренный",
        "swear_filter": False,
    },
    "mama": {
        "name": "Мамы / Здоровье",
        "profile_suffix": "Мамам",
        "tone": "тёплый, БЕЗ мата, темы детей/энергии/дохода из дома",
        "swear_filter": True,
    },
    "business": {
        "name": "Бизнес / Доход",
        "profile_suffix": "Бизнес",
        "tone": "деловой, минимальный мат, цифры/кейсы/доход",
        "swear_filter": False,
    },
    "student": {
        "name": "Студенты / AI",
        "profile_suffix": "Студентам",
        "tone": "как оригинал — мат ок, юмор, мемы, AI/философия",
        "swear_filter": False,
    },
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # ===========================================
    # DATABASE
    # ===========================================
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/info_business",
        description="PostgreSQL connection URL"
    )

    # ===========================================
    # TELEGRAM API
    # ===========================================
    telegram_api_id: int = Field(
        default=0,
        description="Telegram API ID from my.telegram.org"
    )
    telegram_api_hash: str = Field(
        default="",
        description="Telegram API Hash from my.telegram.org"
    )

    # ===========================================
    # ADMIN BOT
    # ===========================================
    admin_bot_token: str = Field(
        default="",
        description="Admin bot token from @BotFather"
    )
    admin_telegram_ids: str = Field(
        default="756877849",
        description="Comma-separated list of admin Telegram IDs"
    )

    @property
    def admin_ids(self) -> List[int]:
        """Parse admin IDs from comma-separated string."""
        if not self.admin_telegram_ids:
            return []
        return [int(x.strip()) for x in self.admin_telegram_ids.split(",")]

    # ===========================================
    # AI PROVIDERS
    # ===========================================
    # Claude (Anthropic)
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key for Claude"
    )

    # YandexGPT (резерв)
    yandex_service_account_id: Optional[str] = Field(default=None)
    yandex_key_id: Optional[str] = Field(default=None)
    yandex_private_key_raw: Optional[str] = Field(default=None, alias="yandex_private_key")
    yandex_private_key_file: Optional[str] = Field(default=None)
    yandex_folder_id: Optional[str] = Field(default=None)

    @property
    def yandex_private_key(self) -> Optional[str]:
        """Parse private key from file or env variable."""
        # First try to read from file
        if self.yandex_private_key_file:
            try:
                with open(self.yandex_private_key_file, 'r') as f:
                    return f.read()
            except Exception:
                pass
        # Fall back to env variable
        if not self.yandex_private_key_raw:
            return None
        # Convert literal \n to actual newlines
        return self.yandex_private_key_raw.replace("\\n", "\n")

    # ===========================================
    # RATE LIMITS (консервативные — безопасные для аккаунтов)
    # ===========================================
    max_comments_per_day: int = Field(default=15, ge=1, le=200)
    max_invites_per_day: int = Field(default=8, ge=0, le=100)  # 0 = отключено
    max_story_views_per_day: int = Field(default=60, ge=0, le=500)  # 0 = отключено
    max_story_reactions_per_day: int = Field(default=15, ge=0, le=200)  # 0 = отключено

    # Daily variance: ±20% рандом чтобы лимиты не были одинаковые каждый день
    daily_variance_min: float = Field(default=0.8, description="Min multiplier for daily limits")
    daily_variance_max: float = Field(default=1.2, description="Max multiplier for daily limits")

    min_comment_interval_sec: int = Field(default=120, ge=10)
    max_comment_interval_sec: int = Field(default=600, ge=30)
    min_invite_interval_sec: int = Field(default=120, ge=30)
    max_invite_interval_sec: int = Field(default=600, ge=60)
    min_story_interval_sec: int = Field(default=5, ge=1)
    max_story_interval_sec: int = Field(default=30, ge=2)

    def get_daily_limit(self, base_limit: int) -> int:
        """Get daily limit with ±20% random variance."""
        multiplier = random.uniform(self.daily_variance_min, self.daily_variance_max)
        return max(1, int(base_limit * multiplier))

    # Story viewing settings
    story_view_min_quality_score: int = Field(
        default=70,
        ge=0,
        le=100,
        description="Minimum quality_score for selecting users from target audience for story viewing"
    )

    # ===========================================
    # WORKING HOURS (Human Simulation)
    # ===========================================
    work_start_hour: int = Field(default=9, ge=0, le=23)
    work_end_hour: int = Field(default=23, ge=1, le=24)

    # ===========================================
    # WARMUP (Прогрев аккаунтов — 14 дней)
    # ===========================================
    warmup_days: int = Field(
        default=14,
        description="Days to warmup new accounts before full activity"
    )
    # Постепенное увеличение лимитов по дням прогрева (мягкий рамп)
    # День 1-3: только сторис, День 4-6: 2-3 коммента, День 7-10: 5-8, День 11-14: 10-12, День 15+: полные лимиты
    warmup_day1_comments: int = Field(default=0, description="Max comments on day 1-3 (only stories)")
    warmup_day3_comments: int = Field(default=2, description="Max comments on day 4-6")
    warmup_day5_comments: int = Field(default=5, description="Max comments on day 7-10")
    warmup_day7_comments: int = Field(default=10, description="Max comments on day 11-14")
    warmup_day1_invites: int = Field(default=0, description="Max invites on day 1-6 (disabled)")
    warmup_day3_invites: int = Field(default=0, description="Max invites on day 4-6 (disabled)")
    warmup_day5_invites: int = Field(default=2, description="Max invites on day 7-10")
    warmup_day7_invites: int = Field(default=5, description="Max invites on day 11-14")
    warmup_day1_stories: int = Field(default=10, description="Max story views on day 1-3")
    warmup_day3_stories: int = Field(default=20, description="Max story views on day 4-6")
    warmup_day5_stories: int = Field(default=40, description="Max story views on day 7-10")
    warmup_day7_stories: int = Field(default=50, description="Max story views on day 11-14")
    # Интервалы между действиями при прогреве (увеличенные)
    warmup_min_interval_sec: int = Field(default=180, description="Min interval during warmup")
    warmup_max_interval_sec: int = Field(default=900, description="Max interval during warmup")

    # ===========================================
    # NOTIFICATIONS (Telegram alerts)
    # ===========================================
    alert_bot_token: str = Field(
        default="",
        description="Telegram bot token for sending alerts"
    )
    alert_admin_id: int = Field(
        default=756877849,
        description="Telegram ID to receive alerts"
    )
    alerts_enabled: bool = Field(
        default=True,
        description="Enable/disable Telegram alerts"
    )
    notify_success: bool = Field(
        default=False,
        alias="traffic_notify_success",
        description="Send Telegram notification on every successful action (for testing)"
    )

    # ===========================================
    # LOGGING
    # ===========================================
    log_level: str = Field(default="INFO")

    # ===========================================
    # ENCRYPTION (for session strings)
    # ===========================================
    encryption_key: str = Field(
        default="",
        description="Fernet encryption key for session strings"
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance (for dependency injection)."""
    return settings
