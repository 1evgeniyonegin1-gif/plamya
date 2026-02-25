"""Настройка оплаты для продукта (YooKassa)."""

import logging

from infobiz_engine.state.state_manager import StateManager

logger = logging.getLogger("producer.payment")


async def run(product_id: str, price_rub: int):
    """Создать ссылку на оплату для продукта.

    NOTE: Для полной интеграции нужен API ключ YooKassa.
    Пока создаёт placeholder и напоминает настроить.

    Args:
        product_id: ID продукта
        price_rub: Цена в рублях
    """
    sm = StateManager()

    product = sm.get_product(product_id)
    if not product:
        print(f"Продукт не найден: {product_id}")
        return

    print(f"Настройка оплаты для: {product.get('title', '?')}")
    print(f"Цена: {price_rub}₽")
    print()

    # TODO: Когда у Данила будет YooKassa аккаунт — интегрировать API
    # POST https://api.yookassa.ru/v3/payments
    # {
    #     "amount": {"value": f"{price_rub}.00", "currency": "RUB"},
    #     "capture": true,
    #     "confirmation": {"type": "redirect", "return_url": "..."},
    #     "description": f"Курс: {product.get('title', '')}"
    # }

    print("⚠️ YooKassa API ещё не настроен.")
    print("Для настройки нужно:")
    print("  1. Зарегистрироваться на yookassa.ru")
    print("  2. Получить shopId и secretKey")
    print("  3. Добавить YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY в config")
    print()
    print("Пока используй прямой перевод или Telegram Payments.")

    # Обновить цену в продукте
    sm.update_product(product_id, {"price_rub": price_rub})
    sm.record_action("setup_payment")

    sm.update_status(f"Настройка оплаты: {product.get('title', '?')} ({price_rub}₽)")
