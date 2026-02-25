"""Конфигурация Chappie Engine."""

import json
import os
from pathlib import Path

# Пути
PROJECT_DIR = Path(__file__).parent.parent
KNOWLEDGE_BASE = PROJECT_DIR / "content" / "knowledge_base"
PRODUCTS_DIR = KNOWLEDGE_BASE / "products"
BUSINESS_DIR = KNOWLEDGE_BASE / "business"
FAQ_DIR = KNOWLEDGE_BASE / "faq"
SUCCESS_STORIES_DIR = KNOWLEDGE_BASE / "success_stories"

# PLAMYA state (бывший OpenClaw)
PLAMYA_HOME = Path.home() / ".plamya"
PLAMYA_AGENT_DIR = PLAMYA_HOME / "chappie"
PLAMYA_SHARED = PLAMYA_HOME / "shared"
STATE_FILE = PLAMYA_AGENT_DIR / "CHAPPIE_STATE.json"
KNOWLEDGE_FILE = PLAMYA_AGENT_DIR / "CHAPPIE_KNOWLEDGE.json"
GOALS_FILE = PLAMYA_AGENT_DIR / "CHAPPIE_GOALS.json"
PROBLEMS_FILE = PLAMYA_AGENT_DIR / "CHAPPIE_PROBLEMS.json"
INBOX_FILE = PLAMYA_SHARED / "INBOX.md"
STATUS_FILE = PLAMYA_SHARED / "STATUS.md"
CONFIG_FILE = PLAMYA_HOME / "embers" / "chappie.json"

# Telegram API (загружаются из config файла)
_config_data = {}
if CONFIG_FILE.exists():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        _config_data = json.load(f)

SESSION_STRING = _config_data.get("session_string", "")
API_ID = _config_data.get("api_id", 0)
API_HASH = _config_data.get("api_hash", "")
DANIL_TELEGRAM_ID = _config_data.get("danil_telegram_id", 756877849)
DANIL_USERNAME = _config_data.get("danil_username", "DanilLysenkoNL")

# NL-каналы для мониторинга и обучения (заполняется после list_my_chats)
NL_CHANNELS = _config_data.get("nl_channels", [])

# Legacy alias
COMPETITOR_CHANNELS = NL_CHANNELS

# Лимиты безопасности (ЖЁСТКИЕ, нельзя обойти)
LIMITS = {
    "max_posts_per_channel_per_day": 3,
    "max_posts_total_per_day": 12,
    "max_stories_per_day": 3,
    "max_dms_new_per_day": 3,        # Фаза 1: 3, потом до 5
    "max_dms_reply_per_day": 10,
    "max_channel_joins_per_day": 1,
    "max_story_views_per_day": 20,
    "max_api_calls_per_day": 50,
    # Минимальные интервалы (секунды)
    "min_interval_post": 10800,       # 3 часа
    "min_interval_story": 14400,      # 4 часа
    "min_interval_dm_new": 7200,      # 2 часа
    "min_interval_dm_reply": 900,     # 15 минут
    "min_interval_channel_join": 86400,  # 24 часа
    "min_interval_story_view": 30,    # 30 секунд
}

# Прогрев (30 дней)
WARMUP_SCHEDULE = {
    # (day_from, day_to): {action: max_per_day}
    (1, 7): {"posts": 1, "stories": 0, "dms": 0, "channels": 0},
    (8, 14): {"posts": 2, "stories": 1, "dms": 0, "channels": 1},
    (15, 21): {"posts": 3, "stories": 2, "dms": 1, "channels": 2},
    (22, 30): {"posts": 4, "stories": 3, "dms": 2, "channels": 3},
}
# После 30 дней — полные лимиты

# Рабочие часы (MSK = UTC+3)
WORK_HOURS_START = 9   # 09:00 MSK
WORK_HOURS_END = 22    # 22:00 MSK
UTC_OFFSET = 3         # MSK

# Аварийные стопы
EMERGENCY_FLOOD_WAIT_THRESHOLD = 60     # секунд → стоп на 6 часов
EMERGENCY_FLOOD_WAIT_CRITICAL = 300     # секунд → стоп на 24 часа
EMERGENCY_CONSECUTIVE_ERRORS = 3         # ошибок подряд → стоп на 1 час
