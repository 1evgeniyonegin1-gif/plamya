"""Конфигурация Sales Engine."""

import os
from pathlib import Path

# ── Пути ──────────────────────────────────────────
PROJECT_DIR = Path("c:/Users/mafio/OneDrive/Документы/projects/nl-international-ai-bots")
KNOWLEDGE_BASE = PROJECT_DIR / "content" / "knowledge_base"
PRODUCTS_DIR = KNOWLEDGE_BASE / "products"
BUSINESS_DIR = KNOWLEDGE_BASE / "business"
FAQ_DIR = KNOWLEDGE_BASE / "faq"
SUCCESS_STORIES_DIR = KNOWLEDGE_BASE / "success_stories"

PLAMYA_HOME = Path.home() / ".plamya"
PLAMYA_SHARED = PLAMYA_HOME / "shared"
INBOX_PATH = PLAMYA_SHARED / "INBOX.md"
STATUS_PATH = PLAMYA_SHARED / "STATUS.md"
NL_CONTENT_PATH = PLAMYA_SHARED / "NL_CONTENT.md"

# ── AI ────────────────────────────────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# ── Сегменты ──────────────────────────────────────
SEGMENTS = ["zozh", "mama", "business", "student"]

SEGMENT_NAMES = {
    "zozh": "ЗОЖ / Питание",
    "mama": "Мамы / Здоровье",
    "business": "Бизнес / Доход",
    "student": "Студенты / Молодёжь",
}

# ── Топ продукты по сегментам ─────────────────────
TOP_PRODUCTS = {
    "zozh": [
        {"name": "ED Smart", "price": "186₽/порция", "hook": "Дешевле кафе, сбалансированный КБЖУ"},
        {"name": "DrainEffect", "price": "от 1,500₽", "hook": "Видимый результат с первого раза"},
        {"name": "Omega-3", "price": "890₽", "hook": "Качественные жирные кислоты"},
        {"name": "Протеин", "price": "от 1,200₽", "hook": "30г белка на порцию"},
    ],
    "mama": [
        {"name": "Детские витамины NLKA", "price": "от 600₽", "hook": "Натуральный состав для детей"},
        {"name": "ED Smart (для мам)", "price": "186₽/порция", "hook": "Быстрый завтрак когда нет времени"},
        {"name": "Коллаген", "price": "от 1,390₽", "hook": "Кожа, волосы, суставы"},
        {"name": "Omega-3", "price": "890₽", "hook": "Для мамы и малыша"},
    ],
    "business": [
        {"name": "Стартовый набор 70PV", "price": "~6,700₽", "hook": "Всё для старта бизнеса"},
        {"name": "ED Smart", "price": "186₽/порция", "hook": "Самый продаваемый продукт NL"},
        {"name": "DrainEffect", "price": "от 1,500₽", "hook": "Лёгкий первый результат для клиента"},
    ],
    "student": [
        {"name": "ED Smart", "price": "186₽/порция", "hook": "Дешевле доширака, но полезнее"},
        {"name": "DrainEffect", "price": "от 1,500₽", "hook": "После вечеринки — мастхэв"},
        {"name": "Протеиновый батончик", "price": "от 150₽", "hook": "Перекус между парами"},
    ],
}

# ── Типы контента ─────────────────────────────────
CONTENT_TYPES = [
    "product_review",       # Обзор продукта от лица Данила
    "personal_result",      # Личный результат использования
    "objection_breaker",    # Пост-ответ на возражение
    "segment_story",        # История для конкретного сегмента
    "business_opportunity", # Возможность бизнеса
    "social_proof",         # Социальное доказательство
    "comparison",           # Сравнение с аналогами/конкурентами
    "educational",          # Образовательный контент (нутрицевтика, КБЖУ)
]

# ── Анти-AI слова (из style_dna.py) ──────────────
ANTI_AI_WORDS = [
    "безусловно", "несомненно", "стоит отметить", "важно подчеркнуть",
    "в заключение", "подводя итоги", "трансформация", "путешествие",
    "уникальный", "качественный", "инновационный", "эксклюзивный",
    "давайте разберёмся", "позвольте поделиться", "я бы хотел отметить",
    "ключевой момент", "на самом деле", "по сути", "в целом",
]
