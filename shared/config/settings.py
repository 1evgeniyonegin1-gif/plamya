"""
Общие настройки для обоих ботов
"""
import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator


class Settings(BaseSettings):
    """Общие настройки приложения"""

    # Telegram Bot Tokens
    curator_bot_token: str = Field(..., env="CURATOR_BOT_TOKEN")
    content_manager_bot_token: str = Field(..., env="CONTENT_MANAGER_BOT_TOKEN")
    channel_username: str = Field(..., env="CHANNEL_USERNAME")

    # Group ID (устаревшее — Topics удалены, оставлено для совместимости)
    group_id: str = Field(default="", env="GROUP_ID")

    # Curator Bot Username (для ссылок в постах)
    curator_bot_username: str = Field(default="@nl_mentor1_bot", env="CURATOR_BOT_USERNAME")

    # AI API Keys
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    anthropic_base_url: str = Field(default="", env="ANTHROPIC_BASE_URL")  # Прокси для обхода блокировки
    gigachat_auth_token: str = Field(default="", env="GIGACHAT_AUTH_TOKEN")
    gigachat_client_id: str = Field(default="", env="GIGACHAT_CLIENT_ID")

    # YandexGPT (Yandex Cloud)
    yandex_service_account_id: str = Field(default="", env="YANDEX_SERVICE_ACCOUNT_ID")
    yandex_key_id: str = Field(default="", env="YANDEX_KEY_ID")
    yandex_private_key: str = Field(default="", env="YANDEX_PRIVATE_KEY")
    yandex_private_key_file: str = Field(default="", env="YANDEX_PRIVATE_KEY_FILE")
    yandex_folder_id: str = Field(default="", env="YANDEX_FOLDER_ID")
    yandex_model: str = Field(default="yandexgpt-32k", env="YANDEX_MODEL")

    @model_validator(mode='after')
    def load_private_key_from_file(self) -> 'Settings':
        """Загружает приватный ключ из файла если указан путь"""
        if self.yandex_private_key_file and not self.yandex_private_key:
            key_path = Path(self.yandex_private_key_file)
            if key_path.exists():
                self.yandex_private_key = key_path.read_text(encoding='utf-8')
        return self

    # YandexART удалён — используем готовые фото из базы unified_products/

    # Deepseek API
    deepseek_api_key: str = Field(default="", env="DEEPSEEK_API_KEY")
    deepseek_model: str = Field(default="deepseek-chat", env="DEEPSEEK_MODEL")

    # Database
    database_url: str = Field(..., env="DATABASE_URL")

    # Admin Settings
    admin_telegram_ids: str = Field(..., env="ADMIN_TELEGRAM_IDS")

    @property
    def admin_ids_list(self) -> List[int]:
        """Преобразует строку ID админов в список"""
        return [int(id_.strip()) for id_ in self.admin_telegram_ids.split(",")]

    # AI Model Configuration
    curator_ai_model: str = Field(default="gemini-1.5-flash", env="CURATOR_AI_MODEL")
    content_manager_ai_model: str = Field(default="gpt-3.5-turbo", env="CONTENT_MANAGER_AI_MODEL")

    # Redis (optional)
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")

    # Telethon (для мониторинга каналов-образцов)
    # Получить на https://my.telegram.org/apps
    telethon_api_id: int = Field(default=0, env="TELETHON_API_ID")
    telethon_api_hash: str = Field(default="", env="TELETHON_API_HASH")
    telethon_session_name: str = Field(default="nl_style_monitor", env="TELETHON_SESSION_NAME")

    # Channel Monitoring Settings
    channel_monitor_interval: int = Field(default=30, env="CHANNEL_MONITOR_INTERVAL")  # Интервал обновления (минуты)
    channel_min_quality_score: float = Field(default=7.0, env="CHANNEL_MIN_QUALITY_SCORE")  # Минимальная оценка для RAG
    channel_min_views: int = Field(default=500, env="CHANNEL_MIN_VIEWS")  # Минимум просмотров
    channel_fetch_limit: int = Field(default=30, env="CHANNEL_FETCH_LIMIT")  # Лимит постов за раз
    channel_fetch_days_back: int = Field(default=30, env="CHANNEL_FETCH_DAYS_BACK")  # Период загрузки (дни)
    channel_auto_rag_sync: bool = Field(default=True, env="CHANNEL_AUTO_RAG_SYNC")  # Автодобавление в RAG
    channel_ai_style_analysis: bool = Field(default=False, env="CHANNEL_AI_STYLE_ANALYSIS")  # AI-анализ стиля

    # Other Settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    timezone: str = Field(default="Europe/Moscow", env="TIMEZONE")

    # ═══════════════════════════════════════════════════════════════
    # Thematic Channels (тематические каналы для автопостинга)
    # ═══════════════════════════════════════════════════════════════

    # Формат: channel_id или @username для каждого сегмента
    thematic_channel_zozh: Optional[str] = Field(default=None, env="THEMATIC_CHANNEL_ZOZH")
    thematic_channel_business: Optional[str] = Field(default=None, env="THEMATIC_CHANNEL_BUSINESS")

    # Расписание автопостинга в тематические каналы (часы MSK)
    thematic_post_hours: str = Field(default="10,14,19", env="THEMATIC_POST_HOURS")
    # Постов в день на канал
    thematic_posts_per_day: int = Field(default=2, env="THEMATIC_POSTS_PER_DAY")

    @property
    def thematic_post_hours_list(self) -> List[int]:
        """Преобразует строку часов в список"""
        return [int(h.strip()) for h in self.thematic_post_hours.split(",")]

    @property
    def thematic_channels(self) -> dict:
        """Возвращает словарь {segment: channel_id_or_username}"""
        channels = {}
        if self.thematic_channel_zozh:
            channels["zozh"] = self.thematic_channel_zozh
        if self.thematic_channel_business:
            channels["business"] = self.thematic_channel_business
        return channels

    # ═══════════════════════════════════════════════════════════════
    # Channel Funnel Settings (Воронка каналов)
    # ═══════════════════════════════════════════════════════════════

    # VIP Channel (закрытый канал для партнёров)
    vip_channel_id: Optional[int] = Field(default=None, env="VIP_CHANNEL_ID")
    vip_channel_username: Optional[str] = Field(default=None, env="VIP_CHANNEL_USERNAME")
    vip_channel_invite_link: Optional[str] = Field(default=None, env="VIP_CHANNEL_INVITE_LINK")  # Статическая ссылка для тестов

    # Invite Post Settings (Инвайт-посты)
    invite_post_hours_valid: int = Field(default=6, env="INVITE_POST_HOURS_VALID")  # Часов действия ссылки
    invite_post_usage_limit: int = Field(default=100, env="INVITE_POST_USAGE_LIMIT")  # Лимит использований
    invite_post_min_days: int = Field(default=2, env="INVITE_POST_MIN_DAYS")  # Мин. дней между инвайтами

    # Invite Post Schedule (Расписание инвайт-постов)
    # Формат: "18,19,20,21" — часы по MSK когда можно публиковать
    invite_post_schedule_hours: str = Field(default="18,19,20,21", env="INVITE_POST_SCHEDULE_HOURS")

    # Дни недели для инвайт-постов (0=Пн, 6=Вс)
    # Формат: "0,1,2,3,4,5" — Пн-Сб (без воскресенья)
    invite_post_weekdays: str = Field(default="0,1,2,3,4,5", env="INVITE_POST_WEEKDAYS")

    @property
    def invite_schedule_hours_list(self) -> List[int]:
        """Преобразует строку часов в список"""
        return [int(h.strip()) for h in self.invite_post_schedule_hours.split(",")]

    @property
    def invite_weekdays_list(self) -> List[int]:
        """Преобразует строку дней недели в список"""
        return [int(d.strip()) for d in self.invite_post_weekdays.split(",")]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Глобальный экземпляр настроек
settings = Settings()
