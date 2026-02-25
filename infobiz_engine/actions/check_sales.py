"""Проверка продаж по всем продуктам."""

from infobiz_engine.state.state_manager import StateManager


async def run():
    """Показать статистику продаж."""
    sm = StateManager()
    products = sm.load_products()
    state = sm.load_state()

    product_list = products.get("products", [])
    if not product_list:
        print("Продуктов пока нет.")
        return

    print("=" * 50)
    print("ПРОДАЖИ")
    print("=" * 50)

    total_sales = 0
    total_revenue = 0

    for p in product_list:
        title = p.get("title", "?")
        status = p.get("status", "draft")
        sales = p.get("sales_count", 0)
        revenue = p.get("revenue_rub", 0)
        price = p.get("price_rub", 0)
        landing = p.get("landing_url", "—")

        total_sales += sales
        total_revenue += revenue

        print(f"\n{p.get('id', '?')} | {title}")
        print(f"  Статус: {status}")
        print(f"  Цена: {price}₽")
        print(f"  Продажи: {sales}")
        print(f"  Выручка: {revenue}₽")
        print(f"  Лендинг: {landing}")

    print(f"\n{'=' * 50}")
    print(f"ИТОГО: {total_sales} продаж, {total_revenue}₽")
    print(f"{'=' * 50}")

    sm.record_action("check_sales")
