"""Конфигурация Infobiz Engine (ПРОДЮСЕР)."""

import os
from pathlib import Path

# Пути
PROJECT_DIR = Path(__file__).parent.parent
CONTENT_DIR = PROJECT_DIR / "infobiz_content"

# PLAMYA state (бывший OpenClaw)
PLAMYA_HOME = Path.home() / ".plamya"
PLAMYA_AGENT_DIR = PLAMYA_HOME / "producer"
PLAMYA_SHARED = PLAMYA_HOME / "shared"
STATE_FILE = PLAMYA_AGENT_DIR / "PRODUCER_STATE.json"
NICHES_FILE = PLAMYA_AGENT_DIR / "PRODUCER_NICHES.json"
PRODUCTS_FILE = PLAMYA_AGENT_DIR / "PRODUCER_PRODUCTS.json"
PIPELINE_FILE = PLAMYA_AGENT_DIR / "PRODUCER_PIPELINE.json"
INBOX_FILE = PLAMYA_SHARED / "INBOX.md"
STATUS_FILE = PLAMYA_SHARED / "STATUS.md"

# Deepseek
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# Данил
DANIL_TELEGRAM_ID = 756877849

# VPS для деплоя лендингов
VPS_HOST = "194.87.86.103"
VPS_USER = "root"
VPS_COURSES_DIR = "/var/www/courses"

# Лимиты безопасности
LIMITS = {
    "max_niches_per_day": 5,
    "max_courses_per_day": 1,
    "max_lessons_per_cycle": 3,
    "max_api_calls_per_day": 100,
    "max_deploy_per_day": 3,
    "min_niche_score": 70,
    "max_daily_deepseek_cost_usd": 1.0,
}

# Рабочие часы (MSK = UTC+3)
WORK_HOURS_START = 9   # 09:00 MSK
WORK_HOURS_END = 23    # 23:00 MSK
UTC_OFFSET = 3         # MSK

# Фокус-ниши (высокая AI-генерируемость)
FOCUS_NICHES = [
    "создание телеграм ботов",
    "python с нуля",
    "нейросети для бизнеса",
    "ChatGPT промпт-инжиниринг",
    "Excel продвинутый",
    "Google Sheets автоматизация",
    "no-code разработка",
    "Tilda создание сайтов",
    "Figma для начинающих",
    "копирайтинг и контент",
    "финансовая грамотность",
    "личная продуктивность",
    "фриланс с нуля",
    "SMM продвижение",
    "автоматизация бизнеса",
]

# Платформы курсов для анализа конкурентов
COMPETITOR_PLATFORMS = [
    "stepik.org",
    "skillbox.ru",
    "udemy.com",
    "coursera.org",
    "geekbrains.ru",
]

# Анти-AI слова (не использовать в контенте)
ANTI_AI_WORDS = [
    "безусловно", "несомненно", "примечательно", "поразительно",
    "стоит отметить", "в заключение", "давайте разберёмся",
    "уникальная возможность", "революционный", "синергия",
    "трансформация", "парадигма", "инновационный", "кардинально",
    "фундаментально", "беспрецедентный", "не могу не отметить",
    "позвольте", "хотелось бы подчеркнуть", "важно понимать",
    "в рамках данного", "ключевой аспект", "на сегодняшний день",
    "в современном мире", "давайте рассмотрим",
]
