"""
Inline клавиатуры для контент-менеджер бота
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import Optional


class Keyboards:
    """Клавиатуры для взаимодействия с администратором"""

    @staticmethod
    def reply_main_menu() -> ReplyKeyboardMarkup:
        """
        Минимальная reply-клавиатура: только Дневник.
        Всё остальное управление через Command Center Mini App.
        """
        builder = ReplyKeyboardBuilder()

        builder.row(
            KeyboardButton(text="📓 Дневник")
        )

        return builder.as_markup(resize_keyboard=True, persistent=True)

    @staticmethod
    def main_menu(pending_count: int = 0) -> InlineKeyboardMarkup:
        """
        Главное меню бота

        Args:
            pending_count: Количество постов на модерации (для бейджа)

        Returns:
            InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()

        # Контент
        pending_text = f"📋 На модерации ({pending_count})" if pending_count > 0 else "📋 На модерации"
        builder.row(
            InlineKeyboardButton(
                text="📝 Создать пост",
                callback_data="menu:generate"
            ),
            InlineKeyboardButton(
                text=pending_text,
                callback_data="menu:pending"
            )
        )

        # Аналитика
        builder.row(
            InlineKeyboardButton(
                text="📊 Статистика",
                callback_data="menu:stats"
            ),
            InlineKeyboardButton(
                text="🏆 Топ посты",
                callback_data="menu:top"
            )
        )

        # Настройки
        builder.row(
            InlineKeyboardButton(
                text="⏰ Автопостинг",
                callback_data="menu:schedule"
            )
        )

        # Справка
        builder.row(
            InlineKeyboardButton(
                text="❓ Справка",
                callback_data="menu:help"
            )
        )

        return builder.as_markup()

    @staticmethod
    def post_type_selection_with_back() -> InlineKeyboardMarkup:
        """
        Клавиатура выбора типа поста с кнопкой возврата в меню

        Returns:
            InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(
                text="📦 О продуктах",
                callback_data="gen_type:product"
            ),
            InlineKeyboardButton(
                text="💪 Мотивация",
                callback_data="gen_type:motivation"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="📰 Новости",
                callback_data="gen_type:news"
            ),
            InlineKeyboardButton(
                text="💡 Советы",
                callback_data="gen_type:tips"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🌟 История успеха",
                callback_data="gen_type:success_story"
            ),
            InlineKeyboardButton(
                text="🎁 Промо/Акция",
                callback_data="gen_type:promo"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="menu:main"
            )
        )

        return builder.as_markup()

    @staticmethod
    def top_posts_menu() -> InlineKeyboardMarkup:
        """Меню выбора топа постов"""
        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(
                text="👁 По просмотрам",
                callback_data="top:views"
            ),
            InlineKeyboardButton(
                text="❤️ По реакциям",
                callback_data="top:reactions"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="📈 По вовлечённости",
                callback_data="top:engagement"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="menu:main"
            )
        )

        return builder.as_markup()

    @staticmethod
    def stats_menu() -> InlineKeyboardMarkup:
        """Меню статистики с выбором периода"""
        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(
                text="📊 За 7 дней",
                callback_data="stats:7"
            ),
            InlineKeyboardButton(
                text="📊 За 30 дней",
                callback_data="stats:30"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="📊 Все время",
                callback_data="stats:all"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔄 Обновить метрики",
                callback_data="stats:update"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="menu:main"
            )
        )

        return builder.as_markup()

    @staticmethod
    def post_moderation(post_id: int, has_image: bool = False) -> InlineKeyboardMarkup:
        """
        Клавиатура для модерации поста

        Args:
            post_id: ID поста в базе данных
            has_image: Есть ли изображение у поста

        Returns:
            InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(
                text="✅ Опубликовать",
                callback_data=f"publish:{post_id}"
            ),
            InlineKeyboardButton(
                text="📋 Опубликовал",
                callback_data=f"mark_published:{post_id}"
            ),
            InlineKeyboardButton(
                text="📅 Запланировать",
                callback_data=f"schedule:{post_id}"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="📝 AI-редакт",
                callback_data=f"edit:{post_id}"
            ),
            InlineKeyboardButton(
                text="✏️ Свой текст",
                callback_data=f"manual_edit:{post_id}"
            ),
            InlineKeyboardButton(
                text="🔄 Заново",
                callback_data=f"regenerate:{post_id}"
            )
        )
        # Кнопки для изображений
        if has_image:
            builder.row(
                InlineKeyboardButton(
                    text="🖼 Другая",
                    callback_data=f"regen_image:{post_id}"
                ),
                InlineKeyboardButton(
                    text="🚫 Убрать",
                    callback_data=f"remove_image:{post_id}"
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text="🖼 Картинка",
                    callback_data=f"gen_image:{post_id}"
                )
            )
        builder.row(
            InlineKeyboardButton(
                text="❌ Удалить",
                callback_data=f"reject:{post_id}"
            ),
            InlineKeyboardButton(
                text="🔙 Меню",
                callback_data="menu:main"
            )
        )

        return builder.as_markup()

    @staticmethod
    def post_type_selection() -> InlineKeyboardMarkup:
        """
        Клавиатура для выбора типа поста

        Returns:
            InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(
                text="📦 О продуктах",
                callback_data="gen_type:product"
            ),
            InlineKeyboardButton(
                text="💪 Мотивация",
                callback_data="gen_type:motivation"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="📰 Новости",
                callback_data="gen_type:news"
            ),
            InlineKeyboardButton(
                text="💡 Советы",
                callback_data="gen_type:tips"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🌟 История успеха",
                callback_data="gen_type:success_story"
            ),
            InlineKeyboardButton(
                text="🎁 Промо/Акция",
                callback_data="gen_type:promo"
            )
        )

        return builder.as_markup()

    @staticmethod
    def confirm_action(action: str, post_id: int) -> InlineKeyboardMarkup:
        """
        Клавиатура подтверждения действия

        Args:
            action: Действие (publish, reject, delete)
            post_id: ID поста

        Returns:
            InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(
                text="✅ Да, подтверждаю",
                callback_data=f"confirm_{action}:{post_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"cancel:{post_id}"
            )
        )

        return builder.as_markup()

    @staticmethod
    def schedule_time_selection(post_id: int) -> InlineKeyboardMarkup:
        """
        Клавиатура для выбора времени публикации

        Args:
            post_id: ID поста

        Returns:
            InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(
                text="⏰ Через 1 час",
                callback_data=f"sched_time:1h:{post_id}"
            ),
            InlineKeyboardButton(
                text="⏰ Через 3 часа",
                callback_data=f"sched_time:3h:{post_id}"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🌅 Завтра 9:00",
                callback_data=f"sched_time:tomorrow_9:{post_id}"
            ),
            InlineKeyboardButton(
                text="🌆 Завтра 18:00",
                callback_data=f"sched_time:tomorrow_18:{post_id}"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="📅 Указать время",
                callback_data=f"sched_time:custom:{post_id}"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=f"cancel:{post_id}"
            )
        )

        return builder.as_markup()

    @staticmethod
    def pending_posts_navigation(
        current_page: int,
        total_pages: int,
        post_id: Optional[int] = None
    ) -> InlineKeyboardMarkup:
        """
        Навигация по списку постов на модерации

        Args:
            current_page: Текущая страница
            total_pages: Всего страниц
            post_id: ID текущего поста (для действий)

        Returns:
            InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()

        # Кнопки действий для текущего поста
        if post_id:
            builder.row(
                InlineKeyboardButton(
                    text="✅ Опубликовать",
                    callback_data=f"publish:{post_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject:{post_id}"
                )
            )

        # Навигация
        nav_buttons = []
        if current_page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data=f"pending_page:{current_page - 1}"
                )
            )
        if current_page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="Вперёд ▶️",
                    callback_data=f"pending_page:{current_page + 1}"
                )
            )

        if nav_buttons:
            builder.row(*nav_buttons)

        # Кнопка возврата в меню
        builder.row(
            InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="menu:main"
            )
        )

        return builder.as_markup()

    @staticmethod
    def back_to_menu() -> InlineKeyboardMarkup:
        """Кнопка возврата в меню"""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="menu:main"
            )
        )
        return builder.as_markup()

    @staticmethod
    def auto_schedule_settings() -> InlineKeyboardMarkup:
        """Настройки автоматической генерации для всех 6 типов контента"""
        builder = InlineKeyboardBuilder()

        # Ряд 1: Продукты и Мотивация (ежедневно)
        builder.row(
            InlineKeyboardButton(
                text="📦 Продукты",
                callback_data="autosched:product"
            ),
            InlineKeyboardButton(
                text="💪 Мотивация",
                callback_data="autosched:motivation"
            )
        )
        # Ряд 2: Новости и Советы
        builder.row(
            InlineKeyboardButton(
                text="📰 Новости",
                callback_data="autosched:news"
            ),
            InlineKeyboardButton(
                text="💡 Советы",
                callback_data="autosched:tips"
            )
        )
        # Ряд 3: Истории успеха и Промо
        builder.row(
            InlineKeyboardButton(
                text="🌟 Истории успеха",
                callback_data="autosched:success_story"
            ),
            InlineKeyboardButton(
                text="🎁 Промо",
                callback_data="autosched:promo"
            )
        )
        # Ряд 4: Статус и Назад
        builder.row(
            InlineKeyboardButton(
                text="📊 Статус расписания",
                callback_data="autosched:status"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="menu:main"
            )
        )

        return builder.as_markup()

    @staticmethod
    def traffic_engine_menu() -> InlineKeyboardMarkup:
        """Подменю Traffic Engine"""
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="📊 Статус",
                callback_data="te:status"
            ),
            InlineKeyboardButton(
                text="👤 Аккаунты",
                callback_data="te:accounts"
            ),
            InlineKeyboardButton(
                text="❌ Ошибки",
                callback_data="te:errors"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="menu:main"
            )
        )
        return builder.as_markup()

    @staticmethod
    def account_detail_buttons(accounts: list) -> InlineKeyboardMarkup:
        """Inline-кнопки для выбора аккаунта (подробности)"""
        builder = InlineKeyboardBuilder()
        for acc in accounts:
            phone_masked = acc.phone[:4] + "***" + acc.phone[-2:] if len(acc.phone) > 6 else acc.phone
            segment = getattr(acc, "segment", "") or ""
            builder.row(
                InlineKeyboardButton(
                    text=f"📋 {phone_masked} [{segment}]",
                    callback_data=f"te:acc_detail:{acc.id}"
                )
            )
        builder.row(
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="te:accounts"
            )
        )
        return builder.as_markup()

    @staticmethod
    def analytics_menu() -> InlineKeyboardMarkup:
        """Меню аналитики"""
        builder = InlineKeyboardBuilder()

        builder.row(
            InlineKeyboardButton(
                text="📊 Аналитика за 7 дней",
                callback_data="analytics:7"
            ),
            InlineKeyboardButton(
                text="📊 За 30 дней",
                callback_data="analytics:30"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🏆 Топ по просмотрам",
                callback_data="top:views"
            ),
            InlineKeyboardButton(
                text="❤️ Топ по реакциям",
                callback_data="top:reactions"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="📈 Топ по вовлеченности",
                callback_data="top:engagement"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔄 Обновить статистику",
                callback_data="update_stats"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="menu:main"
            )
        )

        return builder.as_markup()
