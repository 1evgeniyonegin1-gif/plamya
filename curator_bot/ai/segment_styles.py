"""
Segment Style Overlays для AI-Куратора.

КОНТЕНТ-ЗАВОД: Пользователи приходят из разных тематических каналов.
Куратор адаптирует тон и фокус под сегмент пользователя.

Сегменты:
- zozh: ЗОЖ/Питание — экспертный тон, фокус на питании
- mama: Мамы/Здоровье — тёплый тон, без мата, дети/энергия
- business: Бизнес/Доход — деловой тон, цифры/кейсы
- student: Студенты/AI — оригинальный стиль, мемы/юмор
"""

from typing import Dict, Optional


SEGMENT_STYLES: Dict[str, Dict[str, str]] = {
    "zozh": {
        "name": "ЗОЖ / Питание",
        "tone_override": """СЕГМЕНТ ПОЛЬЗОВАТЕЛЯ: ЗОЖ/Питание.
Этот человек пришёл из канала про здоровый образ жизни.

Адаптация тона:
- Экспертный тон когда речь о питании, макросах, добавках
- Можно использовать спортивный жаргон: макросы, КБЖУ, профицит, дефицит
- Мат умеренный (как обычно)
- Фокус на: белок, витамины, энергия, спорт, восстановление
- При вопросах — сразу к продуктам по теме (ED Smart, протеин, Omega-3)
- Не нянчись, говори как тренер другу""",
        "welcome_extra": "Ты из ЗОЖ-тусовки, значит тему шаришь.",
        "swear_filter": False,
    },

    "mama": {
        "name": "Мамы / Здоровье",
        "tone_override": """СЕГМЕНТ ПОЛЬЗОВАТЕЛЯ: Мамы/Здоровье.
Этот человек пришёл из канала для мам.

Адаптация тона:
- Тёплый тон, БЕЗ МАТА (блин максимум)
- Замени любой мат на мягкие аналоги
- Темы: детское здоровье, энергия для мам, доход из дома, усталость
- Эмпатия: "знаю как это бывает", "многие мамы сталкиваются"
- Общайся на равных, без снисхождения
- При вопросах — продукты для семьи (детские витамины, ED Smart для мам, Omega-3)
- Не навязывай бизнес сразу — сначала здоровье""",
        "welcome_extra": "Рада что заглянула! Если есть вопросы по питанию для семьи — спрашивай.",
        "swear_filter": True,
    },

    "business": {
        "name": "Бизнес / Доход",
        "tone_override": """СЕГМЕНТ ПОЛЬЗОВАТЕЛЯ: Бизнес/Доход.
Этот человек пришёл из бизнес-канала, интересуется заработком.

Адаптация тона:
- Деловой-неформальный тон, минимум мата
- Конкретика: цифры, сроки, маркетинг-план
- Фокус на: квалификации, командообразование, пассивный доход
- При вопросах — сразу про маркетинг-план, стартовые наборы, регистрацию
- Не растекайся — давай цифры и факты
- Показывай путь: "вот как это работает step by step"
- Мотивация через результаты, не эмоции""",
        "welcome_extra": "Видишь тему дохода? Спрашивай конкретно — отвечу конкретно.",
        "swear_filter": False,
    },

    "student": {
        "name": "Студенты / AI / Молодёжь",
        "tone_override": """СЕГМЕНТ ПОЛЬЗОВАТЕЛЯ: Студенты/Молодёжь.
Этот человек пришёл из студенческого/AI канала.

Адаптация тона:
- Оригинальный стиль — мат ок, юмор, ирония
- Темы: подработка на учёбе, AI, бюджетное питание
- Продукты через призму студента: "186 рублей за приём — дешевле доширака если считать нутриенты"
- Бизнес через призму: "пассивный доход пока учишься"
- Без пафоса, без корпоративщины
- Общайся как со сверстником""",
        "welcome_extra": "Залетай. Тут без корпоративной хуйни.",
        "swear_filter": False,
    },
}


def get_segment_overlay(segment: Optional[str]) -> Optional[str]:
    """
    Получить tone_override для сегмента.

    Args:
        segment: Код сегмента (zozh/mama/business/student)

    Returns:
        Текст overlay или None
    """
    if not segment:
        return None
    style = SEGMENT_STYLES.get(segment)
    return style["tone_override"] if style else None


def get_segment_welcome(segment: Optional[str]) -> Optional[str]:
    """Получить дополнительное приветствие для сегмента."""
    if not segment:
        return None
    style = SEGMENT_STYLES.get(segment)
    return style["welcome_extra"] if style else None


def should_filter_swear(segment: Optional[str]) -> bool:
    """Нужно ли фильтровать мат для этого сегмента."""
    if not segment:
        return False
    style = SEGMENT_STYLES.get(segment)
    return style["swear_filter"] if style else False


def extract_segment_from_source(source_id: Optional[str]) -> Optional[str]:
    """
    Извлечь сегмент из source_id трафика.

    Формат source_id: src_{segment}_{account} или channel_{segment}_{number}
    Примеры:
        src_zozh_danil → zozh
        src_mama_test → mama
        channel_zozh_1 → zozh
        channel_mama_2 → mama

    Returns:
        Код сегмента или None
    """
    if not source_id:
        return None

    parts = source_id.split("_")
    if len(parts) >= 2:
        potential_segment = parts[1]
        if potential_segment in SEGMENT_STYLES:
            return potential_segment

    return None
