"""Генерация промо-контента для продукта."""

import logging

from infobiz_engine.state.state_manager import StateManager
from infobiz_engine.ai.copywriter import generate_promo_posts

logger = logging.getLogger("producer.promo")


async def run(product_id: str):
    """Сгенерировать промо-посты для продукта.

    Args:
        product_id: ID продукта
    """
    sm = StateManager()

    product = sm.get_product(product_id)
    if not product:
        print(f"Продукт не найден: {product_id}")
        return

    # Найти нишу для ЦА
    niche = sm.get_niche_by_slug(product.get("niche_slug", ""))
    target_audience = niche.get("target_audience", "") if niche else ""

    print(f"Генерирую промо для: {product.get('title', '?')}...")
    print()

    try:
        posts = await generate_promo_posts(
            course_title=product.get("title", ""),
            target_audience=target_audience,
            price_rub=product.get("price_rub", 4990),
            landing_url=product.get("landing_url", ""),
            count=3,
        )
    except Exception as e:
        print(f"Ошибка AI: {e}")
        return

    if not posts:
        print("AI не вернул посты.")
        return

    print(f"--- ПРОМО-ПОСТЫ ({len(posts)}) ---\n")
    for i, post in enumerate(posts, 1):
        print(f"#{i} [{post.get('type', 'hook')}]")
        print(post.get("text", ""))
        if post.get("cta"):
            print(f"\nCTA: {post['cta']}")
        print(f"\n{'—' * 40}\n")

    sm.record_action("publish_promo")
    sm.update_status(f"Промо: {len(posts)} постов для {product.get('title', '?')}")
