"""
Проактивные задачи онбординга для новичков NL International

Чеклисты по дням с КОНКРЕТНЫМИ ДЕЙСТВИЯМИ (не теорией!).
Интерактивные inline-кнопки для отметки выполнения.

ВАЖНО: Партнёр должен ДЕЙСТВОВАТЬ с первого дня, а не изучать теорию!
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from curator_bot.funnels.referral_links import (
    SHOP_MAIN_LINK,
    PARTNER_REGISTRATION_LINK,
    get_category_link,
)
from shared.config.settings import settings


class OnboardingTasks:
    """
    Чеклисты задач по дням онбординга.

    ПРИНЦИП: Действие > Теория
    - День 1-3: Купить продукт, попробовать, написать знакомым
    - День 4-5: Первые продажи, первый заработок
    - День 6-7: Маркетинг-план, масштабирование

    Теория приходит ПОСЛЕ практики, когда есть контекст.
    """

    # Задачи на первые 7 дней — ПЕРЕДЕЛАНО НА ДЕЙСТВИЯ
    TASKS_BY_DAY = {
        1: {
            "title": "День 1: Старт",
            "greeting": "Привет! Первый день = первое действие.\nНе изучай — пробуй!",
            "tasks": [
                {"id": "d1_order_70pv", "text": "Заказать стартовый набор на 70 PV", "hint": f"Это ОБЯЗАТЕЛЬНО для активации партнёрского статуса! ED Smart + DrainEffect = идеальный старт. Ссылка: {SHOP_MAIN_LINK}"},
                {"id": "d1_try", "text": "Попробовать продукт когда придёт", "hint": "Запомни первые впечатления — они важны"},
                {"id": "d1_photo", "text": "Сфоткать и отправить мне фото продукта", "hint": "Просто фото распаковки или первого приёма"},
            ],
            "emoji": "🚀"
        },
        2: {
            "title": "День 2: Первые разговоры",
            "greeting": "Продукт получен? Теперь поговорим с людьми.",
            "tasks": [
                {"id": "d2_list", "text": "Написать 3 знакомым: 'Пробую новое, интересно?'", "hint": "Не продавай — просто делись. Без давления."},
                {"id": "d2_reply", "text": "Получить хотя бы 1 отклик (да/нет неважно)", "hint": "Главное — диалог. Любой ответ = успех."},
                {"id": "d2_story", "text": "Выложить сторис с продуктом (по желанию)", "hint": "Покажи что пробуешь. Честно, без рекламы."},
            ],
            "emoji": "💬"
        },
        3: {
            "title": "День 3: Первый интерес",
            "greeting": "Кто-то заинтересовался? Отлично! Если нет — напиши ещё 3 людям.",
            "tasks": [
                {"id": "d3_dialog", "text": "Продолжить диалог с заинтересованным", "hint": "Расскажи свой опыт. Спроси что его волнует."},
                {"id": "d3_more", "text": "Написать ещё 3-5 контактам", "hint": "Чем больше разговоров — тем быстрее результат"},
                {"id": "d3_answer", "text": "Ответить на возражение (спроси меня как)", "hint": "Напиши: 'Мне сказали что дорого, как ответить?'"},
            ],
            "emoji": "🎯"
        },
        4: {
            "title": "День 4: Первая продажа",
            "greeting": "Цель дня — первый заработок. Даже 100₽ считается!",
            "tasks": [
                {"id": "d4_sell", "text": "Продать 1 продукт (или оформить друга как клиента)", "hint": f"Дай клиенту эту ссылку: {SHOP_MAIN_LINK}"},
                {"id": "d4_money", "text": "Увидеть свои первые начисления в ЛК", "hint": "Зайди в личный кабинет, раздел 'Мои бонусы'"},
                {"id": "d4_celebrate", "text": "Написать мне что получилось!", "hint": "Расскажи сколько заработал — это важно!"},
            ],
            "emoji": "💰"
        },
        5: {
            "title": "День 5: Масштабирование",
            "greeting": "Первая продажа есть? Теперь повторяем!",
            "tasks": [
                {"id": "d5_more", "text": "Написать ещё 5 контактам", "hint": "Расширяй круг. Новые люди = новые продажи."},
                {"id": "d5_repeat", "text": "Сделать повторную продажу", "hint": "Или первому клиенту допродажа, или новый клиент"},
                {"id": "d5_system", "text": "Понять свой рабочий скрипт (что говоришь)", "hint": "Напиши мне: 'Помоги составить скрипт'"},
            ],
            "emoji": "📈"
        },
        6: {
            "title": "День 6: Маркетинг-план",
            "greeting": "Продажи идут? Теперь разберёмся как расти дальше.",
            "tasks": [
                {"id": "d6_mp", "text": "Изучить квалификации M1, M2, M3", "hint": "Спроси: 'Расскажи про квалификации'"},
                {"id": "d6_calc", "text": "Посчитать сколько нужно для M1", "hint": "Напиши: 'Как выйти на M1?'"},
                {"id": "d6_plan", "text": "Составить план на месяц (конкретные цифры)", "hint": "Сколько контактов, сколько продаж, какой доход?"},
            ],
            "emoji": "📊"
        },
        7: {
            "title": "День 7: Команда",
            "greeting": "Неделя прошла! Теперь — о команде.",
            "tasks": [
                {"id": "d7_invite", "text": "Пригласить 1 человека как партнёра (не клиента)", "hint": "Тот, кто тоже хочет зарабатывать. Не продавать, а строить."},
                {"id": "d7_support", "text": "Связаться с наставником/куратором", "hint": "Пиши наставнику: @DanilLysenkoNL — расскажи о результатах, спроси совет."},
                {"id": "d7_goal", "text": "Поставить цель на следующие 30 дней", "hint": "Конкретно: X продаж, Y партнёров, Z₽ дохода"},
            ],
            "emoji": "👥"
        }
    }

    # Напоминания для неактивных пользователей — с акцентом на 70 PV
    INACTIVITY_REMINDERS = {
        4: f"Привет! Ты уже заказал стартовый набор на 70 PV? Это ПЕРВЫЙ и ГЛАВНЫЙ шаг!\n\nБез 70 PV ты не можешь получать бонусы. Ссылка: {SHOP_MAIN_LINK}\n\nНапиши 'помоги выбрать' — подскажу что взять!",
        12: f"Напоминаю: без заказа на 70 PV партнёрство не активно.\n\nЭто ~4000-5000₽ = твой рабочий инструмент + здоровье.\nСсылка: {SHOP_MAIN_LINK}",
        24: "Сутки прошли. Ты заказал 70 PV?\n\nЕсли что-то смущает — напиши. Разберём любое возражение.",
        48: "2 дня молчишь. Что застопорило?\n\nЕсли дорого — есть варианты. Если сомнения — обсудим. Напиши честно.",
        168: "Неделя тишины. Последняя попытка: ты ещё хочешь строить бизнес? Да/нет.\n\nБез ответа считаю что передумал.",
    }

    @classmethod
    def get_day_tasks(cls, day: int) -> Optional[Dict]:
        """
        Получить задачи на конкретный день

        Args:
            day: Номер дня (1-7)

        Returns:
            Dict с задачами или None
        """
        return cls.TASKS_BY_DAY.get(day)

    @classmethod
    def get_task_keyboard(cls, day: int, task_id: str, is_completed: bool = False) -> InlineKeyboardMarkup:
        """
        Создаёт inline-клавиатуру для задачи.

        Args:
            day: Номер дня
            task_id: ID задачи
            is_completed: Выполнена ли задача

        Returns:
            InlineKeyboardMarkup с кнопками
        """
        if is_completed:
            # Уже выполнено — показываем только галочку
            return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Выполнено", callback_data=f"onb_done:{task_id}")]
            ])

        # Не выполнено — показываем кнопки действий
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Выполнено", callback_data=f"onb_complete:{task_id}"),
                InlineKeyboardButton(text="⏭️ Пропустить", callback_data=f"onb_skip:{task_id}")
            ]
        ])

    @classmethod
    def get_day_keyboard(cls, day: int, completed_tasks: List[str] = None) -> InlineKeyboardMarkup:
        """
        Создаёт общую клавиатуру для дня с кнопками под каждой задачей.

        Args:
            day: Номер дня
            completed_tasks: Список ID выполненных задач

        Returns:
            InlineKeyboardMarkup
        """
        completed_tasks = completed_tasks or []
        day_info = cls.get_day_tasks(day)

        if not day_info:
            return None

        buttons = []
        for task in day_info["tasks"]:
            is_done = task["id"] in completed_tasks
            if is_done:
                buttons.append([
                    InlineKeyboardButton(text=f"✅ {task['text'][:30]}...", callback_data=f"onb_done:{task['id']}")
                ])
            else:
                buttons.append([
                    InlineKeyboardButton(text=f"⬜ {task['text'][:25]}...", callback_data=f"onb_view:{task['id']}")
                ])
                buttons.append([
                    InlineKeyboardButton(text="✅ Выполнено", callback_data=f"onb_complete:{task['id']}"),
                    InlineKeyboardButton(text="⏭️ Пропустить", callback_data=f"onb_skip:{task['id']}")
                ])

        # Кнопка перехода на следующий день (если все выполнены)
        total = len(day_info["tasks"])
        completed = sum(1 for t in day_info["tasks"] if t["id"] in completed_tasks)
        if completed == total and day < 7:
            buttons.append([
                InlineKeyboardButton(text=f"➡️ Перейти к Дню {day + 1}", callback_data=f"onb_next_day:{day + 1}")
            ])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @classmethod
    def format_tasks_message(
        cls,
        day: int,
        completed_tasks: List[str] = None,
        include_keyboard: bool = True
    ) -> tuple:
        """
        Форматирует сообщение с задачами на день.

        Args:
            day: Номер дня
            completed_tasks: Список ID выполненных задач
            include_keyboard: Включать ли inline-клавиатуру

        Returns:
            tuple: (текст сообщения, InlineKeyboardMarkup или None)
        """
        completed_tasks = completed_tasks or []
        day_info = cls.get_day_tasks(day)

        if not day_info:
            return ("Поздравляю! Ты прошёл базовый онбординг 🎉\nТеперь можешь спрашивать что угодно — помогу с продажами, продуктами, командой.", None)

        emoji = day_info["emoji"]
        message = f"{emoji} <b>{day_info['title']}</b>\n\n"
        message += f"{day_info['greeting']}\n\n"

        # Список задач
        for i, task in enumerate(day_info["tasks"], 1):
            is_done = task["id"] in completed_tasks
            checkbox = "✅" if is_done else f"{i}️⃣"

            if is_done:
                message += f"{checkbox} <s>{task['text']}</s>\n\n"
            else:
                message += f"{checkbox} <b>{task['text']}</b>\n"
                if task.get("hint"):
                    message += f"   <i>💡 {task['hint']}</i>\n\n"

        # Прогресс-бар
        completed_count = sum(1 for t in day_info["tasks"] if t["id"] in completed_tasks)
        total_count = len(day_info["tasks"])

        progress_bar = cls._make_progress_bar(completed_count, total_count)
        message += f"━━━━━━━━━━━━━━━\n"
        message += f"{progress_bar} {completed_count}/{total_count}"

        if completed_count == total_count:
            if day < 7:
                message += "\n\n🎉 Все задачи выполнены! Жми кнопку перехода к следующему дню."
            else:
                message += "\n\n🏆 Ты прошёл весь онбординг! Теперь ты готов к самостоятельной работе."

        # Генерируем клавиатуру
        keyboard = None
        if include_keyboard:
            keyboard = cls._make_tasks_keyboard(day, day_info["tasks"], completed_tasks)

        return (message, keyboard)

    @classmethod
    def _make_progress_bar(cls, completed: int, total: int) -> str:
        """Создаёт визуальный прогресс-бар"""
        filled = int(completed / total * 10) if total > 0 else 0
        empty = 10 - filled
        return "▓" * filled + "░" * empty

    @classmethod
    def _make_tasks_keyboard(
        cls,
        day: int,
        tasks: List[Dict],
        completed_tasks: List[str]
    ) -> InlineKeyboardMarkup:
        """Создаёт inline-клавиатуру для задач дня"""
        buttons = []

        # Находим первую невыполненную задачу
        first_pending = None
        for task in tasks:
            if task["id"] not in completed_tasks:
                first_pending = task
                break

        # Показываем кнопки только для первой невыполненной задачи
        # (чтобы не перегружать)
        if first_pending:
            buttons.append([
                InlineKeyboardButton(
                    text=f"✅ Выполнил: {first_pending['text'][:25]}...",
                    callback_data=f"onb_complete:{first_pending['id']}"
                )
            ])
            buttons.append([
                InlineKeyboardButton(
                    text="⏭️ Пропустить эту задачу",
                    callback_data=f"onb_skip:{first_pending['id']}"
                )
            ])

        # Кнопка перехода на следующий день
        all_done = all(t["id"] in completed_tasks for t in tasks)
        if all_done and day < 7:
            buttons.append([
                InlineKeyboardButton(
                    text=f"➡️ Перейти к Дню {day + 1}",
                    callback_data=f"onb_next_day:{day + 1}"
                )
            ])

        # Кнопка показа всего чеклиста
        buttons.append([
            InlineKeyboardButton(text="📋 Весь чеклист", callback_data=f"onb_show_all:{day}")
        ])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @classmethod
    def get_inactivity_reminder(cls, hours_inactive: int) -> Optional[str]:
        """
        Получить напоминание для неактивного пользователя

        Args:
            hours_inactive: Часов без активности

        Returns:
            Текст напоминания или None
        """
        for threshold, message in sorted(cls.INACTIVITY_REMINDERS.items()):
            if hours_inactive >= threshold:
                return message
        return None


def get_task_for_day(day: int) -> Optional[Dict]:
    """Обёртка для получения задач на день"""
    return OnboardingTasks.get_day_tasks(day)


async def get_user_progress(telegram_id: int) -> Dict:
    """
    Получить прогресс пользователя по онбордингу

    Args:
        telegram_id: Telegram ID пользователя

    Returns:
        Dict с прогрессом
    """
    from curator_bot.onboarding.onboarding_service import OnboardingService
    return await OnboardingService.get_user_progress_dict(telegram_id)


async def mark_task_completed(telegram_id: int, task_id: str) -> bool:
    """
    Отметить задачу как выполненную

    Args:
        telegram_id: Telegram ID пользователя
        task_id: ID задачи

    Returns:
        True если успешно
    """
    from curator_bot.onboarding.onboarding_service import OnboardingService
    result = await OnboardingService.mark_task_completed(telegram_id, task_id)
    if result:
        logger.info(f"Task {task_id} marked as completed for user {telegram_id}")
    return result
