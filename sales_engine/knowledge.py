"""
Загрузчик базы знаний NL International.
Читает markdown-файлы из knowledge_base/ и подготавливает контекст для AI.
"""

from pathlib import Path
from .config import PRODUCTS_DIR, BUSINESS_DIR, FAQ_DIR, SUCCESS_STORIES_DIR


def load_product_knowledge() -> dict[str, str]:
    """Загружает все файлы о продуктах."""
    products = {}
    if not PRODUCTS_DIR.exists():
        return products
    for f in PRODUCTS_DIR.rglob("*.md"):
        products[f.stem] = f.read_text(encoding="utf-8")
    return products


def load_business_knowledge() -> str:
    """Загружает знания о бизнес-модели."""
    texts = []
    if not BUSINESS_DIR.exists():
        return ""
    for f in sorted(BUSINESS_DIR.glob("*.md")):
        texts.append(f.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(texts)


def load_faq() -> list[dict]:
    """Загружает FAQ."""
    faqs = []
    if not FAQ_DIR.exists():
        return faqs
    for f in sorted(FAQ_DIR.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        faqs.append({"topic": f.stem, "content": content})
    return faqs


def load_success_stories() -> list[dict]:
    """Загружает истории успеха."""
    stories = []
    if not SUCCESS_STORIES_DIR.exists():
        return stories
    for f in sorted(SUCCESS_STORIES_DIR.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        stories.append({"name": f.stem, "content": content})
    return stories


def get_product_context(product_name: str) -> str:
    """Получает контекст по конкретному продукту."""
    products = load_product_knowledge()
    # Ищем по частичному совпадению
    for key, content in products.items():
        if product_name.lower() in key.lower() or key.lower() in product_name.lower():
            return content
    return ""


def get_compact_product_list() -> str:
    """Краткий список продуктов для промпта (экономия токенов)."""
    return """
Ключевые продукты NL International:
1. ED Smart — функциональное питание, 186₽/порция, 16+ вкусов, замена приёма пищи
2. DrainEffect — дренирующий напиток, видимый результат за 30 мин
3. Коллаген Greenflash — пептиды/морской/трини, от 1,390₽, 95% биодоступность
4. Omega-3 — 890₽, жирные кислоты
5. Greenflash витамины — комплексы для иммунитета, энергии
6. Be Loved косметика — уход за лицом/телом
7. NLKA детская линия — витамины для детей
8. Стартовый набор — 70 PV (~6,700₽), вход в бизнес

Регистрация БЕСПЛАТНАЯ. Клиентский клуб — скидка до 10% без обязательств.
""".strip()
