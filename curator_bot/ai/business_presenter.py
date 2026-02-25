"""
Модуль для бизнес-презентации AI-Куратора

Отправляет фото чеков, истории успеха, презентации бизнеса.
Интегрируется с основным обработчиком сообщений.

ОБНОВЛЕНО: Теперь использует TestimonialsManager вместо отсутствующей папки telegram_knowledge.
"""
import random
from typing import Optional, List, Dict
from loguru import logger

from shared.testimonials import get_testimonials_manager, TestimonialCategory


class BusinessPresenter:
    """
    Презентер бизнеса NL International.

    Умеет отправлять:
    - Истории успеха с фото
    - Фото чеков партнёров
    - Краткие презентации бизнес-модели

    Данные берутся из TestimonialsManager (content/testimonials/).
    """

    def __init__(self):
        self.success_stories: List[Dict] = []
        self.business_posts: List[Dict] = []
        self._testimonials_manager = get_testimonials_manager()
        self._load_content()

    def _load_content(self):
        """Загружает контент из TestimonialsManager"""
        try:
            # Загружаем истории успеха из testimonials
            stories = self._testimonials_manager.get_random(
                TestimonialCategory.SUCCESS_STORIES,
                count=50,
                with_media_only=False
            )

            self.success_stories = [
                {
                    "text": s.get("full_text", s.get("text", "")),
                    "text_cleaned": s.get("full_text", s.get("text", "")),
                    "quality_score": 80,
                    "from": s.get("from", "Партнёр NL")
                }
                for s in stories if s.get("full_text") or s.get("text")
            ]
            logger.info(f"BusinessPresenter: loaded {len(self.success_stories)} success stories from testimonials")

            # Загружаем посты о бизнесе (чеки как источник информации о доходах)
            checks = self._testimonials_manager.get_random(
                TestimonialCategory.CHECKS,
                count=30,
                with_media_only=False
            )

            self.business_posts = [
                {
                    "text": c.get("full_text", c.get("text", "")),
                    "text_cleaned": c.get("full_text", c.get("text", "")),
                    "quality_score": 80,
                    "from": c.get("from", "Партнёр NL")
                }
                for c in checks if c.get("full_text") or c.get("text")
            ]

            # Добавляем стандартные питчи если нет данных
            if not self.business_posts:
                self.business_posts = [
                    {"text": self.get_quick_business_pitch(), "quality_score": 80}
                    for _ in range(5)
                ]

            logger.info(f"BusinessPresenter: loaded {len(self.business_posts)} business posts")

        except Exception as e:
            logger.error(f"Error loading business content: {e}")
            # Fallback — используем стандартные питчи
            self.business_posts = [
                {"text": self.get_quick_business_pitch(), "quality_score": 80}
            ]

    def should_send_business_media(self, message: str, ai_response: str) -> Optional[str]:
        """
        Определяет, нужно ли отправить медиа для бизнес-презентации.

        Args:
            message: Сообщение пользователя
            ai_response: Ответ AI

        Returns:
            Тип медиа ('success_story', 'business_proof', 'income_proof') или None
        """
        message_lower = message.lower()

        # ВАЖНО: Проверяем только сообщение пользователя, не ответ AI!
        # Иначе при "Привет" AI упоминает "результаты/партнёр" → триггер срабатывает

        # Истории успеха — когда говорим о результатах
        success_keywords = [
            "результат", "похудел", "скинул", "минус", "кг",
            "получилось", "история", "пример", "отзыв"
        ]
        if any(kw in message_lower for kw in success_keywords):
            return "success_story"

        # Доказательства дохода — когда говорим о заработке
        income_keywords = [
            "заработок", "доход", "сколько платят", "сколько зарабат",
            "чек", "выплат", "получаешь", "бонус", "деньги", "бабки"
        ]
        if any(kw in message_lower for kw in income_keywords):
            return "income_proof"

        # Бизнес в целом — квалификации, команда
        business_keywords = [
            "бизнес", "партнёр", "партнер", "квалификац", "команд",
            "m1", "m2", "m3", "b1", "b2", "b3", "top", "регистр"
        ]
        if any(kw in message_lower for kw in business_keywords):
            return "business_proof"

        return None

    def get_success_story(self) -> Optional[str]:
        """
        Возвращает случайную историю успеха (только текст).

        Returns:
            Краткий текст истории или None
        """
        if not self.success_stories:
            # Fallback — получаем напрямую из менеджера
            stories = self._testimonials_manager.get_text_only(
                TestimonialCategory.SUCCESS_STORIES,
                count=1
            )
            if stories:
                return self._shorten_text(stories[0])
            return None

        story = random.choice(self.success_stories)
        text = self._shorten_text(story.get("text_cleaned", story.get("text", "")))
        return text

    def get_income_proof(self) -> Optional[str]:
        """
        Возвращает текст о доходе/заработке.

        Returns:
            Текст о заработке или None
        """
        # Ищем посты с упоминанием чеков/дохода
        income_posts = [
            post for post in self.business_posts
            if any(kw in post.get("text", "").lower()
                   for kw in ["чек", "выплат", "доход", "заработ", "бонус", "квалификац"])
        ]

        if not income_posts:
            income_posts = self.business_posts

        if not income_posts:
            # Fallback — стандартный питч
            return self.get_quick_business_pitch()

        post = random.choice(income_posts)
        text = self._shorten_text(post.get("text_cleaned", post.get("text", "")))
        return text

    def get_business_presentation(self) -> Optional[str]:
        """
        Возвращает общую бизнес-презентацию (текст).

        Returns:
            Текст презентации или None
        """
        if not self.business_posts:
            return self.get_quick_business_pitch()

        post = random.choice(self.business_posts)
        text = self._shorten_text(post.get("text_cleaned", post.get("text", "")))
        return text

    def _shorten_text(self, text: str, max_length: int = 1500) -> str:
        """
        Сокращает текст до разумной длины.
        Увеличен лимит с 500 до 1500 чтобы не обрезать важную информацию.
        """
        if len(text) <= max_length:
            return text

        # Обрезаем по последнему предложению
        shortened = text[:max_length]
        last_period = shortened.rfind(".")
        last_newline = shortened.rfind("\n")

        cut_point = max(last_period, last_newline)
        if cut_point > max_length // 2:
            return shortened[:cut_point + 1]

        return shortened + "..."

    def get_quick_business_pitch(self) -> str:
        """
        Возвращает краткую презентацию бизнеса (без фото).
        Для случаев когда нет подходящего фото.
        """
        pitches = [
            "Смотри как это работает: рекомендуешь продукты друзьям — получаешь процент. "
            "Чем больше людей — тем больше зарабатываешь. На M1 это 15-30к в месяц.",

            "NL — это не про продажи. Это про рекомендации. "
            "Сам пользуешься, рассказываешь другим, получаешь бонусы. Просто.",

            "Регистрация бесплатная. Покупаешь для себя со скидкой 25%, "
            "рекомендуешь друзьям — получаешь % от их покупок. Компании 25 лет.",

            "M1 = 750 баллов команды = 15-30к в месяц. "
            "M3 = 3000 баллов = 50-100к. Это реально, я сам прошёл этот путь."
        ]
        return random.choice(pitches)


# Глобальный экземпляр
business_presenter = BusinessPresenter()


def get_business_presenter() -> BusinessPresenter:
    """Возвращает глобальный экземпляр презентера"""
    return business_presenter
