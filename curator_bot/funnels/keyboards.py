"""
Inline-клавиатуры для воронки продаж
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


# ============================================
# ГЛАВНОЕ МЕНЮ (Reply-кнопки внизу экрана)
# ============================================

def get_main_menu_reply_keyboard() -> ReplyKeyboardMarkup:
    """Reply-кнопки внизу экрана (всегда видны)"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍎 Здоровье"), KeyboardButton(text="💼 Бизнес"), KeyboardButton(text="💡 Узнать больше")],
            [KeyboardButton(text="❓ Задать вопрос"), KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )


# ============================================
# ЭТАП 1: Квалификация после /start
# ============================================

def get_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора пути после /start"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🍎 Хочу улучшить здоровье",
            callback_data="intent_client"
        )],
        [InlineKeyboardButton(
            text="💼 Интересует заработок",
            callback_data="intent_business"
        )],
        [InlineKeyboardButton(
            text="❓ Просто хочу узнать больше",
            callback_data="intent_curious"
        )],
    ])


# ============================================
# ЭТАП 1.2: Выявление боли (для клиентов)
# ============================================

def get_pain_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора боли для клиентов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔥 Похудеть / контроль веса",
            callback_data="pain_weight"
        )],
        [InlineKeyboardButton(
            text="⚡ Больше энергии",
            callback_data="pain_energy"
        )],
        [InlineKeyboardButton(
            text="💪 Укрепить иммунитет",
            callback_data="pain_immunity"
        )],
        [InlineKeyboardButton(
            text="✨ Красота: кожа, волосы, ногти",
            callback_data="pain_beauty"
        )],
        [InlineKeyboardButton(
            text="🧒 Здоровье детей",
            callback_data="pain_kids"
        )],
        [InlineKeyboardButton(
            text="🏃 Спорт и восстановление",
            callback_data="pain_sport"
        )],
        [InlineKeyboardButton(
            text="← Назад",
            callback_data="back_to_start"
        )],
    ])


# ============================================
# ЭТАП 1.3: Выявление интереса (для бизнеса)
# ============================================

def get_income_goal_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора цели дохода для бизнеса"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💰 Подработка 10-30к/мес",
            callback_data="income_10_30k"
        )],
        [InlineKeyboardButton(
            text="📈 Серьёзный доход 50-100к/мес",
            callback_data="income_50_100k"
        )],
        [InlineKeyboardButton(
            text="🚀 Бизнес 200к+/мес",
            callback_data="income_200k_plus"
        )],
        [InlineKeyboardButton(
            text="🤔 Пока не уверен, расскажи",
            callback_data="income_unsure"
        )],
        [InlineKeyboardButton(
            text="← Назад",
            callback_data="back_to_start"
        )],
    ])


# ============================================
# ЭТАП 2: Цепочки прогрева — клиенты
# ============================================

def get_continue_keyboard() -> InlineKeyboardMarkup:
    """Кнопка 'Продолжить' для прогрева"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Продолжить →",
            callback_data="funnel_continue"
        )],
        [InlineKeyboardButton(
            text="← Назад",
            callback_data="back_to_pain"
        )],
    ])


def get_weight_goal_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора цели по весу"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="5-10 кг",
            callback_data="weight_5_10"
        )],
        [InlineKeyboardButton(
            text="10-20 кг",
            callback_data="weight_10_20"
        )],
        [InlineKeyboardButton(
            text="Больше 20 кг",
            callback_data="weight_20_plus"
        )],
        [InlineKeyboardButton(
            text="Хочу поддерживать вес",
            callback_data="weight_maintain"
        )],
        [InlineKeyboardButton(
            text="← Назад",
            callback_data="back_to_pain"
        )],
    ])


def get_energy_goal_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора проблемы с энергией"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🌅 Не могу проснуться",
            callback_data="energy_morning"
        )],
        [InlineKeyboardButton(
            text="😴 Спад энергии после обеда",
            callback_data="energy_afternoon"
        )],
        [InlineKeyboardButton(
            text="🔋 Хроническая усталость",
            callback_data="energy_chronic"
        )],
        [InlineKeyboardButton(
            text="😰 Стресс и выгорание",
            callback_data="energy_stress"
        )],
        [InlineKeyboardButton(
            text="← Назад",
            callback_data="back_to_pain"
        )],
    ])


def get_immunity_goal_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора проблемы с иммунитетом"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🤧 Частые простуды (3-4+ раз в год)",
            callback_data="immunity_frequent_colds"
        )],
        [InlineKeyboardButton(
            text="🔄 Долгое восстановление после болезни",
            callback_data="immunity_recovery"
        )],
        [InlineKeyboardButton(
            text="❄️ Зимняя поддержка иммунитета",
            callback_data="immunity_winter"
        )],
        [InlineKeyboardButton(
            text="👶 Для ребёнка (садик/школа)",
            callback_data="immunity_kids"
        )],
        [InlineKeyboardButton(
            text="← Назад",
            callback_data="back_to_pain"
        )],
    ])


def get_beauty_goal_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора проблемы с красотой"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✨ Упругость кожи, морщины",
            callback_data="beauty_skin"
        )],
        [InlineKeyboardButton(
            text="💇 Волосы (выпадение, рост)",
            callback_data="beauty_hair"
        )],
        [InlineKeyboardButton(
            text="💅 Ногти (ломкость, слоение)",
            callback_data="beauty_nails"
        )],
        [InlineKeyboardButton(
            text="🌟 Всё вместе (комплексно)",
            callback_data="beauty_complex"
        )],
        [InlineKeyboardButton(
            text="← Назад",
            callback_data="back_to_pain"
        )],
    ])


def get_kids_goal_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора проблемы для детей"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🤧 Частые болезни (садик/школа)",
            callback_data="kids_immunity"
        )],
        [InlineKeyboardButton(
            text="🧠 Концентрация, память, учёба",
            callback_data="kids_brain"
        )],
        [InlineKeyboardButton(
            text="📏 Рост, кости, зубы",
            callback_data="kids_growth"
        )],
        [InlineKeyboardButton(
            text="🌟 Всё вместе (комплекс)",
            callback_data="kids_complex"
        )],
        [InlineKeyboardButton(
            text="← Назад",
            callback_data="back_to_pain"
        )],
    ])


def get_sport_goal_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора цели для спортсменов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💪 Набор мышечной массы",
            callback_data="sport_mass"
        )],
        [InlineKeyboardButton(
            text="🔥 Сушка / снижение % жира",
            callback_data="sport_cut"
        )],
        [InlineKeyboardButton(
            text="🏃 Выносливость (бег, кроссфит)",
            callback_data="sport_endurance"
        )],
        [InlineKeyboardButton(
            text="🔄 Быстрое восстановление",
            callback_data="sport_recovery"
        )],
        [InlineKeyboardButton(
            text="← Назад",
            callback_data="back_to_pain"
        )],
    ])


def get_product_interest_keyboard() -> InlineKeyboardMarkup:
    """Кнопки интереса к продукту после описания"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Да, подбери для меня",
            callback_data="product_select"
        )],
        [InlineKeyboardButton(
            text="💰 Сколько это стоит?",
            callback_data="product_price"
        )],
        [InlineKeyboardButton(
            text="❓ Есть вопросы",
            callback_data="product_questions"
        )],
        [InlineKeyboardButton(
            text="← Назад",
            callback_data="back_to_step1"
        )],
    ])


def get_order_keyboard(product_link: str) -> InlineKeyboardMarkup:
    """Клавиатура заказа продукта"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛒 Заказать со скидкой 25%",
            url=product_link
        )],
        [InlineKeyboardButton(
            text="❓ У меня вопрос",
            callback_data="product_questions"
        )],
        [InlineKeyboardButton(
            text="← Назад",
            callback_data="back_to_product_interest"
        )],
    ])


# ============================================
# ЭТАП 2: Цепочки прогрева — бизнес
# ============================================

def get_business_continue_keyboard() -> InlineKeyboardMarkup:
    """Кнопка продолжения бизнес-прогрева"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Показать расчёт →",
            callback_data="business_calc"
        )],
        [InlineKeyboardButton(
            text="← Назад",
            callback_data="back_to_income"
        )],
    ])


def get_business_next_keyboard() -> InlineKeyboardMarkup:
    """Кнопка 'Да, расскажи' для бизнеса"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Да, расскажи →",
            callback_data="business_next"
        )],
        [InlineKeyboardButton(
            text="← Назад",
            callback_data="back_to_calc"
        )],
    ])


def get_registration_keyboard(registration_link: str) -> InlineKeyboardMarkup:
    """Клавиатура регистрации партнёра"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Да, хочу зарегистрироваться",
            url=registration_link
        )],
        [InlineKeyboardButton(
            text="❓ Есть вопросы",
            callback_data="business_questions"
        )],
        [InlineKeyboardButton(
            text="← Назад",
            callback_data="back_to_growth"
        )],
    ])


# ============================================
# ЭТАП 4: Сбор контактов
# ============================================

def get_contact_request_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура запроса контакта"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📱 На телефон (WhatsApp)",
            callback_data="contact_phone"
        )],
        [InlineKeyboardButton(
            text="📧 На email",
            callback_data="contact_email"
        )],
        [InlineKeyboardButton(
            text="❌ Не нужно",
            callback_data="contact_skip"
        )],
    ])


# ============================================
# ЭТАП 5: Напоминания
# ============================================

def get_reminder_response_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура ответа на напоминание"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="+ Хочу продолжить",
            callback_data="reminder_continue"
        )],
        [InlineKeyboardButton(
            text="Пока не актуально",
            callback_data="reminder_later"
        )],
    ])


# ============================================
# Вспомогательные клавиатуры
# ============================================

def get_back_to_start_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата к выбору пути"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="← Вернуться к выбору",
            callback_data="back_to_start"
        )],
    ])


def get_ask_question_keyboard() -> InlineKeyboardMarkup:
    """Кнопка 'Задать вопрос'"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="❓ Задать вопрос",
            callback_data="ask_question"
        )],
    ])


# ============================================
# Воронка "Узнать больше" — провокационные вопросы
# ============================================

def get_curious_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с провокационными вопросами для curious"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🚨 Это развод или нет?",
            callback_data="curious_scam"
        )],
        [InlineKeyboardButton(
            text="💸 Почему многие бросают NL?",
            callback_data="curious_quit"
        )],
        [InlineKeyboardButton(
            text="🤷 Кому НЕ подойдёт NL?",
            callback_data="curious_not_for"
        )],
        [InlineKeyboardButton(
            text="⚠️ Что скрывают про Energy Diet?",
            callback_data="curious_hidden"
        )],
        [InlineKeyboardButton(
            text="← Назад",
            callback_data="back_to_start"
        )],
    ])


def get_curious_response_business_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после ответа curious — переход в бизнес"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💼 Расскажи подробнее про бизнес",
            callback_data="intent_business"
        )],
        [InlineKeyboardButton(
            text="🔄 Ещё вопросы",
            callback_data="intent_curious"
        )],
    ])


def get_curious_response_health_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после ответа curious — переход в здоровье"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🍎 Расскажи подробнее про здоровье",
            callback_data="intent_client"
        )],
        [InlineKeyboardButton(
            text="🔄 Ещё вопросы",
            callback_data="intent_curious"
        )],
    ])


def get_curious_response_both_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после ответа curious — выбор направления"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🍎 Про здоровье",
            callback_data="intent_client"
        )],
        [InlineKeyboardButton(
            text="💼 Про бизнес",
            callback_data="intent_business"
        )],
        [InlineKeyboardButton(
            text="🔄 Ещё вопросы",
            callback_data="intent_curious"
        )],
    ])
