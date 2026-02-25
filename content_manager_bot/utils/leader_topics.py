"""
Парсер экспорта чата лидера для получения тем по категориям.

Telegram экспорт (result.json) парсится и категоризируется.
Бот берёт ТЕМЫ из экспорта, но пишет в СВОЁМ стиле (персоны + эмоции).

Использование:
    leader = LeaderTopicsParser()
    topic = leader.get_topic_by_category("product")
    # → "Как правильно пить Omega-3 для максимального эффекта"
"""
import json
import random
import re
from pathlib import Path
from typing import Optional, List, Dict
from loguru import logger


# Путь к экспорту лидера
LEADER_EXPORT_PATH = Path(__file__).parent.parent.parent / "content" / "leader_export"
EXPORT_FILE = LEADER_EXPORT_PATH / "result.json"


# Ключевые слова для категоризации постов
CATEGORY_KEYWORDS = {
    "product": [
        # Продукты NL
        "energy diet", "ed smart", "greenflash", "omega", "омега",
        "коллаген", "collagen", "витамин", "vitamin", "протеин",
        "белок", "магний", "magnesium", "детокс", "detox", "draineffect",
        "3d slim", "слим", "occuba", "beloved", "шампунь", "крем",
        "nlka", "happy smile", "enerwood", "чай",
        # Темы продуктов
        "состав", "как принимать", "дозировка", "эффект", "результат",
        "усвоение", "биодоступность", "форма выпуска",
    ],
    "motivation": [
        # Мотивационные темы
        "начать", "страх", "мечта", "цель", "вера", "сила",
        "не сдавайся", "путь", "победа", "успех", "изменить жизнь",
        "выход из зоны комфорта", "дисциплина", "привычка",
        "прокрастинация", "откладывать", "идеальный момент",
        "маленькие шаги", "большая цель",
    ],
    "business": [
        # Бизнес и MLM
        "бизнес", "сетевой", "mlm", "партнёр", "команда",
        "доход", "заработок", "маркетинг-план", "квалификация",
        "пирамида", "пассивный доход", "свобода", "график",
        "удалённая работа", "своё дело", "без начальника",
        "рекомендательный", "структура",
    ],
    "tips": [
        # Советы и лайфхаки
        "совет", "лайфхак", "как правильно", "ошибка", "ошибки",
        "секрет", "способ", "метод", "инструкция", "пошагово",
        "утро", "утренний ритуал", "привычка", "режим",
        "питание", "рацион", "калории",
    ],
    "news": [
        # Новости компании
        "новинка", "акция", "скидка", "промо", "событие",
        "мероприятие", "конференция", "обновление", "запуск",
        "анонс", "новость",
    ],
    "success": [
        # Истории успеха
        "история", "трансформация", "до и после", "результат",
        "отзыв", "клиент", "партнёр рассказывает", "мой путь",
        "как я начал", "первые шаги", "достижение",
    ],
}


class LeaderTopicsParser:
    """
    Парсер экспорта чата лидера.

    Загружает result.json из Telegram экспорта,
    категоризирует посты и возвращает темы по категориям.
    """

    def __init__(self, export_path: Optional[Path] = None):
        """
        Инициализация парсера.

        Args:
            export_path: Путь к папке с экспортом (по умолчанию content/leader_export/)
        """
        self.export_path = export_path or LEADER_EXPORT_PATH
        self.export_file = self.export_path / "result.json"

        # Кэш постов по категориям
        self._posts_by_category: Dict[str, List[Dict]] = {
            cat: [] for cat in CATEGORY_KEYWORDS.keys()
        }
        self._is_loaded = False

        # Пробуем загрузить при инициализации
        self._load_export()

    def _load_export(self) -> bool:
        """
        Загружает и парсит экспорт из JSON файла.

        Returns:
            bool: True если загрузка успешна
        """
        if not self.export_file.exists():
            logger.warning(f"Leader export not found: {self.export_file}")
            logger.info("To use leader topics, export chat from Telegram Desktop:")
            logger.info("  1. Open chat → ⋮ → Export chat history")
            logger.info("  2. Select JSON format")
            logger.info(f"  3. Save result.json to {self.export_path}")
            return False

        try:
            with open(self.export_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            messages = data.get("messages", [])
            logger.info(f"Loaded {len(messages)} messages from leader export")

            # Категоризируем посты
            categorized = 0
            for msg in messages:
                if msg.get("type") != "message":
                    continue

                # Извлекаем текст (может быть строкой или списком)
                text = self._extract_text(msg)
                if not text or len(text) < 50:  # Пропускаем короткие
                    continue

                # Определяем категорию
                category = self._categorize_text(text)
                if category:
                    # Извлекаем тему из текста
                    topic = self._extract_topic(text)
                    self._posts_by_category[category].append({
                        "id": msg.get("id"),
                        "date": msg.get("date"),
                        "text": text,
                        "topic": topic
                    })
                    categorized += 1

            self._is_loaded = True
            logger.info(f"Categorized {categorized} posts:")
            for cat, posts in self._posts_by_category.items():
                logger.info(f"  {cat}: {len(posts)} posts")

            return True

        except Exception as e:
            logger.error(f"Error loading leader export: {e}")
            return False

    def _extract_text(self, message: dict) -> str:
        """
        Извлекает текст из сообщения.

        Telegram экспорт может содержать text как строку или как список
        объектов с форматированием.
        """
        text = message.get("text", "")

        if isinstance(text, str):
            return text.strip()

        if isinstance(text, list):
            # Собираем текст из всех элементов
            parts = []
            for item in text:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(item.get("text", ""))
            return "".join(parts).strip()

        return ""

    def _categorize_text(self, text: str) -> Optional[str]:
        """
        Определяет категорию текста по ключевым словам.

        Returns:
            str или None: Название категории
        """
        text_lower = text.lower()

        # Считаем совпадения по каждой категории
        scores = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score

        if not scores:
            return None

        # Возвращаем категорию с наибольшим количеством совпадений
        return max(scores, key=scores.get)

    def _extract_topic(self, text: str) -> str:
        """
        Извлекает основную тему/идею из текста.

        Берёт первые 2-3 предложения как тему.
        """
        # Убираем emoji в начале
        text = re.sub(r'^[\U0001F300-\U0001F9FF\s]+', '', text)

        # Берём первые 2-3 предложения
        sentences = re.split(r'[.!?]\s+', text)
        topic_sentences = sentences[:3]

        topic = ". ".join(topic_sentences)

        # Ограничиваем длину
        if len(topic) > 200:
            topic = topic[:197] + "..."

        return topic.strip()

    def get_topic_by_category(self, category: str) -> Optional[str]:
        """
        Возвращает случайную тему для указанной категории.

        Args:
            category: Категория (product, motivation, business, tips, news, success)

        Returns:
            str или None: Тема для генерации поста
        """
        if not self._is_loaded:
            logger.warning("Leader export not loaded, returning None")
            return None

        posts = self._posts_by_category.get(category, [])
        if not posts:
            logger.warning(f"No posts found for category: {category}")
            return None

        # Выбираем случайный пост
        post = random.choice(posts)
        return post.get("topic")

    def get_random_topic(self) -> Optional[str]:
        """
        Возвращает случайную тему из любой категории.

        Returns:
            str или None: Тема для генерации поста
        """
        # Собираем все посты
        all_posts = []
        for posts in self._posts_by_category.values():
            all_posts.extend(posts)

        if not all_posts:
            return None

        post = random.choice(all_posts)
        return post.get("topic")

    def get_topics_for_category(self, category: str, limit: int = 10) -> List[str]:
        """
        Возвращает список тем для указанной категории.

        Args:
            category: Категория
            limit: Максимум тем

        Returns:
            List[str]: Список тем
        """
        posts = self._posts_by_category.get(category, [])
        topics = [p.get("topic") for p in posts if p.get("topic")]

        random.shuffle(topics)
        return topics[:limit]

    def get_stats(self) -> Dict[str, int]:
        """
        Возвращает статистику по категориям.

        Returns:
            Dict[str, int]: {категория: количество постов}
        """
        return {cat: len(posts) for cat, posts in self._posts_by_category.items()}

    def is_available(self) -> bool:
        """
        Проверяет, доступен ли экспорт лидера.

        Returns:
            bool: True если экспорт загружен
        """
        return self._is_loaded


# Глобальный экземпляр парсера (ленивая инициализация)
_leader_parser: Optional[LeaderTopicsParser] = None


def get_leader_parser() -> LeaderTopicsParser:
    """
    Возвращает глобальный экземпляр парсера.

    Returns:
        LeaderTopicsParser: Парсер экспорта лидера
    """
    global _leader_parser
    if _leader_parser is None:
        _leader_parser = LeaderTopicsParser()
    return _leader_parser


def get_topic_for_post_type(post_type: str) -> Optional[str]:
    """
    Возвращает тему из экспорта лидера для типа поста.

    Маппинг типов постов на категории:
    - product, product_deep_dive, product_comparison → product
    - motivation, transformation → motivation
    - business, business_lifestyle, business_myths → business
    - tips → tips
    - news, promo → news
    - success_story → success

    Args:
        post_type: Тип поста из ContentGenerator

    Returns:
        str или None: Тема от лидера или None если экспорт недоступен
    """
    parser = get_leader_parser()

    if not parser.is_available():
        return None

    # Маппинг типов постов на категории
    type_to_category = {
        "product": "product",
        "product_deep_dive": "product",
        "product_comparison": "product",
        "motivation": "motivation",
        "transformation": "motivation",
        "business": "business",
        "business_lifestyle": "business",
        "business_myths": "business",
        "tips": "tips",
        "news": "news",
        "promo": "news",
        "success_story": "success",
        "faq": "product",
        "myth_busting": "product",
    }

    category = type_to_category.get(post_type, "motivation")
    return parser.get_topic_by_category(category)
