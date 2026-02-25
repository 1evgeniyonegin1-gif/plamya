"""
Модуль для отправки медиа-контента из базы testimonials.

Куратор может отправлять:
- Фото до/после (похудение, коллаген, драйн и т.д.)
- Видео с отзывами
- Голосовые сообщения партнёров
- Кружочки (video_message)
- Чеки партнёров

Примеры использования:
- Пользователь спрашивает "помогает ли коллаген?" → отправляем фото до/после коллагена
- "Хочу услышать отзывы" → отправляем голосовое сообщение
- "Покажи результаты похудения" → фото до/после + видео
"""

from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from loguru import logger

from shared.testimonials.testimonials_manager import (
    TestimonialsManager,
    TestimonialCategory,
    get_testimonials_manager
)


class MediaResponder:
    """Отправляет медиа-контент из базы testimonials."""

    def __init__(self):
        self.manager = get_testimonials_manager()

    def should_send_media(self, user_message: str) -> Dict[str, Any]:
        """
        Определяет, нужно ли отправить медиа по запросу пользователя.

        Returns:
            dict: {
                'should_send': bool,
                'media_type': str,  # 'photo', 'video', 'voice', 'video_message'
                'category': str,
                'subcategory': str (optional),
                'keywords': List[str]
            }
        """
        message_lower = user_message.lower()

        # Триггеры для фото до/после
        photo_triggers = [
            "фото", "результат", "до и после", "до/после", "до после", "покажи",
            "выглядит", "работает ли", "помогает ли", "эффект",
            "похудел", "похудела", "изменил", "изменила",
            "изменения", "результаты"
        ]

        # Триггеры для видео
        video_triggers = [
            "видео", "ролик", "смотреть", "покажи видео",
            "как использовать", "инструкция", "как применять"
        ]

        # Триггеры для голосовых
        voice_triggers = [
            "голос", "послушать", "расскажи голосом", "хочу услышать",
            "отзыв", "мнение", "опыт", "история"
        ]

        # Триггеры для чеков
        check_triggers = [
            "чек", "заработок", "заработать", "доход", "сколько заработал",
            "бонус", "выплата", "прибыль", "деньги", "зарабатывать",
            "сколько можно", "можно заработать", "реальный доход"
        ]

        # Определяем категорию и подкатегорию
        result = {
            'should_send': False,
            'media_type': None,
            'category': None,
            'subcategory': None,
            'keywords': []
        }

        # Определяем тип медиа
        if any(t in message_lower for t in photo_triggers):
            result['media_type'] = 'photo'
        elif any(t in message_lower for t in video_triggers):
            result['media_type'] = 'video'
        elif any(t in message_lower for t in voice_triggers):
            result['media_type'] = 'voice'

        # Определяем категорию по ключевым словам
        # ВАЖНО: используем корни слов для лучшего matching
        category_keywords = {
            TestimonialCategory.BEFORE_AFTER: [
                # Похудение (все формы)
                "похуде", "похудел", "похудела", "стройн", "сброс", "минус",
                # Вес
                "вес", "килограмм", "кг",
                # Продукты NL (ED Smart, Energy Diet и др.)
                "ed smart", "edsmart", "energy diet", "energy slim", "энерджи",
                "3d slim", "3dslim", "slim",
                # Коллаген
                "коллаген", "collagen", "кожа", "лицо", "морщин",
                # DrainEffect
                "драйн", "drain", "draineffect", "отёк", "отек",
                # Детокс
                "детокс", "detox", "очищен",
                # Волосы
                "волос", "выпаден",
                # Целлюлит
                "целлюлит", "апельсинов",
                # Витамины
                "витамин", "greenflash",
                # Другие продукты
                "slime", "слайм",
                "патчи", "под глазами",
                "крем", "сыворотк",
                # Общие триггеры для до/после
                "результат", "до после", "до/после", "эффект", "помога", "работа"
            ],
            TestimonialCategory.CHECKS: check_triggers,
            TestimonialCategory.PRODUCTS: [
                "продукт", "купить", "заказать", "состав",
                "инструкция", "как принимать", "дозировка",
                "рецепт", "приготовить", "готовить"
            ],
            TestimonialCategory.SUCCESS_STORIES: [
                "история", "опыт", "путь", "достижени",
                "мотивац", "вдохновен", "пример",
                "с чего начать", "как начать"
            ]
        }

        # ПРИОРИТЕТ КАТЕГОРИЙ:
        # 1. CHECKS — чеки важнее всего (деньги/заработок)
        # 2. SUCCESS_STORIES — истории успеха
        # 3. BEFORE_AFTER — результаты продуктов
        # 4. PRODUCTS — информация о продуктах
        category_priority = [
            TestimonialCategory.CHECKS,
            TestimonialCategory.SUCCESS_STORIES,
            TestimonialCategory.BEFORE_AFTER,
            TestimonialCategory.PRODUCTS,
        ]

        for category in category_priority:
            keywords = category_keywords.get(category, [])
            matched = [kw for kw in keywords if kw in message_lower]
            if matched:
                result['category'] = category
                result['keywords'] = matched
                result['should_send'] = True

                # Если категория определена, но media_type нет — ставим фото по умолчанию
                if result['media_type'] is None:
                    if category == TestimonialCategory.CHECKS:
                        result['media_type'] = 'photo'  # Чеки — это фото
                    elif category == TestimonialCategory.SUCCESS_STORIES:
                        result['media_type'] = 'voice'  # Истории — голосовые
                    else:
                        result['media_type'] = 'photo'  # По умолчанию фото

                break

        # Определяем подкатегорию для before_after
        if result['category'] == TestimonialCategory.BEFORE_AFTER:
            subcategory_map = {
                # ED Smart, Energy Diet → weight_loss (это продукты для похудения)
                # УБРАН 'стройн' — он путал коллаген с "марафонами стройности"
                'weight_loss': [
                    'похудел', 'похудела', 'похудение', 'похуд',  # полные слова
                    'вес', 'килограмм', 'кг', 'минус', 'сброс',
                    'ed smart', 'edsmart', 'energy diet', 'energy slim', 'энерджи',
                    '3d slim', '3dslim', 'slim'
                ],
                'collagen': ['коллаген', 'collagen', 'кожа', 'морщин', 'лицо', 'упругость'],
                'drain_effect': ['драйн', 'drain', 'draineffect', 'отёк', 'отек', 'отечность'],
                'detox': ['детокс', 'detox', 'очищен'],
                'hair': ['волос', 'выпаден'],
                'cellulite': ['целлюлит', 'апельсинов'],
                'slime_3d': ['3d slime', 'слайм', 'slime'],
                'patches': ['патчи'],
                'skin_care': ['крем', 'сыворотк'],
                'vitamins': ['витамин', 'greenflash', 'адаптоген']
            }

            # Приоритизация: выбираем подкатегорию с максимальным числом совпадений
            # (вместо первого match, который мог быть неточным)
            matches = {}
            for subcat, keywords in subcategory_map.items():
                count = sum(1 for kw in keywords if kw in message_lower)
                if count > 0:
                    matches[subcat] = count

            if matches:
                result['subcategory'] = max(matches, key=matches.get)

        return result

    def get_media_for_response(
        self,
        media_config: Dict[str, Any],
        count: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Получает медиафайлы из базы testimonials.

        Args:
            media_config: Конфигурация из should_send_media()
            count: Количество файлов для отправки

        Returns:
            List[dict]: Список медиафайлов с путями и метаданными
        """
        if not media_config.get('should_send'):
            return []

        category = media_config['category']
        subcategory = media_config.get('subcategory')
        media_type = media_config['media_type']

        try:
            # Получаем testimonials
            if media_type == 'photo':
                if subcategory:
                    testimonials = self.manager.get_by_subcategory(
                        category,
                        subcategory,
                        count=count,
                        with_photos_only=True
                    )
                else:
                    testimonials = self.manager.get_random(
                        category,
                        count=count,
                        with_photos_only=True
                    )

            elif media_type == 'video':
                testimonials = self.manager.get_videos(
                    category=category,
                    include_video_messages=False,
                    max_duration=120,  # до 2 минут
                    count=count
                )

            elif media_type == 'voice':
                testimonials = self.manager.get_voice_messages(
                    category=category,
                    max_duration=60,  # до 1 минуты
                    count=count
                )

            else:
                testimonials = self.manager.get_random(
                    category,
                    count=count,
                    with_media_only=True
                )

            # Извлекаем файлы с абсолютными путями
            media_files = []
            for testimonial in testimonials:
                # Используем новый метод для получения файлов с абсолютными путями
                files = self.manager.get_media_files(testimonial)
                for file_info in files:
                    if file_info.get('exists', False):
                        media_files.append({
                            'path': str(file_info['path']),  # Абсолютный путь
                            'type': file_info['type'],
                            'caption': self._format_caption(testimonial),
                            'testimonial': testimonial
                        })
                    else:
                        logger.warning(f"Media file not found: {file_info['path']}")

            logger.info(f"Found {len(media_files)} media files for {category}/{subcategory}")
            return media_files[:count]

        except Exception as e:
            logger.error(f"Error getting media: {e}")
            return []

    def _format_caption(self, testimonial: Dict[str, Any]) -> str:
        """Форматирует подпись к медиа."""
        text = testimonial.get('text', '')
        author = testimonial.get('from', '')
        topic = testimonial.get('topic', '')

        # Обрезаем длинный текст
        if len(text) > 200:
            text = text[:200] + '...'

        caption = ""
        if topic:
            caption += f"📍 {topic}\n\n"
        if text:
            caption += f"{text}\n\n"
        if author and author != "Unknown":
            caption += f"— {author}"

        return caption.strip()

    def format_text_with_media_context(
        self,
        ai_response: str,
        media_config: Dict[str, Any]
    ) -> str:
        """
        Добавляет контекст к текстовому ответу, если отправляется медиа.

        Args:
            ai_response: Ответ от AI
            media_config: Конфигурация медиа

        Returns:
            str: Текст с контекстом медиа
        """
        if not media_config.get('should_send'):
            return ai_response

        media_type = media_config['media_type']
        category = media_config.get('category')

        # Добавляем вводную фразу
        intros = {
            'photo': [
                "Вот реальные результаты наших партнёров:",
                "Смотри, какие изменения:",
                "Вот что происходит:",
            ],
            'video': [
                "Смотри видео:",
                "Вот видео с подробностями:",
                "Записал для тебя:",
            ],
            'voice': [
                "Послушай опыт партнёра:",
                "Вот голосовое от коллеги:",
                "Реальная история:",
            ]
        }

        import random
        intro = random.choice(intros.get(media_type, ["Вот что у меня есть:"]))

        return f"{ai_response}\n\n{intro}"


# Глобальный экземпляр
_global_responder: Optional[MediaResponder] = None


def get_media_responder() -> MediaResponder:
    """Получить глобальный экземпляр MediaResponder (singleton)."""
    global _global_responder
    if _global_responder is None:
        _global_responder = MediaResponder()
    return _global_responder
