"""
Уведомления о лидах для владельца бота
"""
from aiogram import Bot
from shared.config.settings import settings
from curator_bot.database.models import User
from loguru import logger


async def notify_hot_lead(bot: Bot, user: User):
    """
    Отправляет уведомление о горячем лиде владельцу

    Args:
        bot: Экземпляр бота
        user: Горячий лид
    """
    try:
        admin_ids = settings.admin_ids_list

        intent_names = {
            "client": "Клиент (здоровье)",
            "business": "Бизнес",
            "curious": "Любопытный",
        }

        pain_names = {
            "weight": "Похудение",
            "energy": "Энергия",
            "immunity": "Иммунитет",
            "beauty": "Красота",
            "kids": "Дети",
            "sport": "Спорт",
        }

        income_names = {
            "10_30k": "10-30к/мес",
            "50_100k": "50-100к/мес",
            "200k_plus": "200к+/мес",
            "unsure": "Не определился",
        }

        message = f"""🔥 <b>ГОРЯЧИЙ ЛИД!</b>

👤 <b>Имя:</b> {user.first_name or 'Не указано'}
📱 <b>Телефон:</b> {user.phone or 'Не оставил'}
📧 <b>Email:</b> {user.email or 'Не оставил'}

🎯 <b>Интерес:</b> {intent_names.get(user.user_intent, user.user_intent or '-')}
💊 <b>Боль:</b> {pain_names.get(user.pain_point, user.pain_point or '-')}
💰 <b>Цель дохода:</b> {income_names.get(user.income_goal, user.income_goal or '-')}

📊 <b>Прошёл шагов:</b> {user.funnel_step}
🏆 <b>Скоринг:</b> {user.lead_score} баллов

👉 <b>Telegram:</b> @{user.username or f'id{user.telegram_id}'}"""

        for admin_id in admin_ids:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=message
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")

        logger.info(f"Hot lead notification sent for user {user.telegram_id}")

    except Exception as e:
        logger.error(f"Error notifying hot lead: {e}")


async def notify_new_contact(bot: Bot, user: User, contact_type: str):
    """
    Уведомляет о новом контакте (телефон/email)

    Args:
        bot: Экземпляр бота
        user: Пользователь
        contact_type: Тип контакта (phone/email)
    """
    try:
        admin_ids = settings.admin_ids_list

        contact_value = user.phone if contact_type == "phone" else user.email

        message = f"""📞 <b>НОВЫЙ КОНТАКТ!</b>

👤 <b>Имя:</b> {user.first_name or 'Не указано'}
{'📱 <b>Телефон:</b>' if contact_type == 'phone' else '📧 <b>Email:</b>'} {contact_value}

🎯 <b>Интерес:</b> {user.user_intent or '-'}
💊 <b>Боль:</b> {user.pain_point or '-'}

👉 <b>Telegram:</b> @{user.username or f'id{user.telegram_id}'}"""

        for admin_id in admin_ids:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=message
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")

        logger.info(f"New contact notification sent for user {user.telegram_id}")

    except Exception as e:
        logger.error(f"Error notifying new contact: {e}")
