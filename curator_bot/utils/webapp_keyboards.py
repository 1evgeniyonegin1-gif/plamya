"""
WebApp клавиатуры для Curator Mini App

Содержит кнопки для открытия Mini App с разными разделами.
"""
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
    ReplyKeyboardMarkup, KeyboardButton,
)
import os


# URL Mini App (можно настроить через .env)
CURATOR_MINIAPP_URL = os.getenv("CURATOR_MINIAPP_URL", "https://curator.apexflow01.ru")


def get_miniapp_reply_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    Persistent reply keyboard с Mini App кнопками.
    Появляется внизу чата у поля ввода сообщения.

    Args:
        is_admin: Если True, добавляет кнопку дневника
    """
    rows = [
        [
            KeyboardButton(
                text="🛒 Продукция NL",
                web_app=WebAppInfo(url=f"{CURATOR_MINIAPP_URL}?tab=products")
            ),
            KeyboardButton(
                text="💼 Бизнес",
                web_app=WebAppInfo(url=f"{CURATOR_MINIAPP_URL}?tab=business")
            ),
        ]
    ]
    if is_admin:
        rows.append([KeyboardButton(text="📓 Дневник")])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
    )


def get_miniapp_keyboard() -> InlineKeyboardMarkup:
    """
    Основная клавиатура с Mini App кнопками.

    Содержит две кнопки:
    - Продукция NL (открывает каталог)
    - Бизнес с APEXFLOW (открывает бизнес-раздел)
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛒 Продукция NL",
            web_app=WebAppInfo(url=f"{CURATOR_MINIAPP_URL}?tab=products")
        )],
        [InlineKeyboardButton(
            text="💼 Бизнес с APEXFLOW",
            web_app=WebAppInfo(url=f"{CURATOR_MINIAPP_URL}?tab=business")
        )],
    ])


def get_products_button() -> InlineKeyboardMarkup:
    """
    Отдельная кнопка для каталога продуктов.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛒 Смотреть каталог",
            web_app=WebAppInfo(url=f"{CURATOR_MINIAPP_URL}?tab=products")
        )],
    ])


def get_business_button() -> InlineKeyboardMarkup:
    """
    Отдельная кнопка для бизнес-раздела.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💼 Узнать про бизнес",
            web_app=WebAppInfo(url=f"{CURATOR_MINIAPP_URL}?tab=business")
        )],
    ])


def get_catalog_inline_button() -> InlineKeyboardButton:
    """
    Отдельная инлайн-кнопка для встраивания в другие клавиатуры.
    """
    return InlineKeyboardButton(
        text="🛒 Каталог",
        web_app=WebAppInfo(url=f"{CURATOR_MINIAPP_URL}?tab=products")
    )


def get_business_inline_button() -> InlineKeyboardButton:
    """
    Отдельная инлайн-кнопка для встраивания в другие клавиатуры.
    """
    return InlineKeyboardButton(
        text="💼 Бизнес",
        web_app=WebAppInfo(url=f"{CURATOR_MINIAPP_URL}?tab=business")
    )
