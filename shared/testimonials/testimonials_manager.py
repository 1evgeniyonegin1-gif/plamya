"""
Менеджер для работы с отзывами и историями успеха.
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class TestimonialCategory(str, Enum):
    """Категории testimonials."""
    BEFORE_AFTER = "before_after"
    CHECKS = "checks"
    SUCCESS_STORIES = "success_stories"
    PRODUCTS = "products"


class TestimonialsManager:
    """
    Менеджер для работы с testimonials (отзывы, истории успеха, чеки).

    Примеры использования:

    # Получить случайную историю успеха
    manager = TestimonialsManager()
    story = manager.get_random(TestimonialCategory.SUCCESS_STORIES)

    # Получить 3 случайных чека
    checks = manager.get_random(TestimonialCategory.CHECKS, count=3)

    # Получить истории по подкатегории
    weight_loss = manager.get_by_subcategory(
        TestimonialCategory.BEFORE_AFTER,
        "weight_loss",
        count=5
    )

    # Поиск по ключевым словам
    collagen_stories = manager.search("коллаген", limit=10)
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Инициализация менеджера.

        Args:
            base_dir: Базовая директория с testimonials.
                     По умолчанию: PROJECT_ROOT/content/testimonials
        """
        if base_dir is None:
            # Автоматически определяем путь к testimonials
            current_file = Path(__file__)
            self.project_root = current_file.parent.parent.parent
            base_dir = self.project_root / "content" / "testimonials"
        else:
            self.project_root = Path(base_dir).parent.parent

        self.base_dir = Path(base_dir)
        self._cache: Dict[str, List[Dict[str, Any]]] = {}

        # Загружаем summary
        summary_path = self.base_dir / "summary.json"
        if summary_path.exists():
            with open(summary_path, 'r', encoding='utf-8') as f:
                self.summary = json.load(f)
        else:
            self.summary = {}

    def _load_category(self, category: TestimonialCategory) -> List[Dict[str, Any]]:
        """Загружает данные категории из файла."""
        if category.value in self._cache:
            return self._cache[category.value]

        metadata_path = self.base_dir / category.value / "metadata.json"
        if not metadata_path.exists():
            return []

        with open(metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            messages = data.get('messages', [])
            self._cache[category.value] = messages
            return messages

    def get_random(
        self,
        category: TestimonialCategory,
        count: int = 1,
        with_photos_only: bool = False,
        with_videos_only: bool = False,
        with_media_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Получить случайные testimonials из категории.

        Args:
            category: Категория (BEFORE_AFTER, CHECKS и т.д.)
            count: Количество результатов
            with_photos_only: Возвращать только с фото
            with_videos_only: Возвращать только с видео
            with_media_only: Возвращать только с любым медиа

        Returns:
            Список testimonials
        """
        messages = self._load_category(category)

        if with_photos_only:
            messages = [m for m in messages if m.get('has_photo')]
        elif with_videos_only:
            messages = [m for m in messages if m.get('has_video')]
        elif with_media_only:
            messages = [m for m in messages if m.get('has_media')]

        if not messages:
            return []

        # Если запросили больше, чем есть - вернём все
        count = min(count, len(messages))
        return random.sample(messages, count)

    def get_by_subcategory(
        self,
        category: TestimonialCategory,
        subcategory: str,
        count: int = 1,
        with_photos_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Получить testimonials по подкатегории.

        Args:
            category: Основная категория
            subcategory: Подкатегория (например, "weight_loss", "skin")
            count: Количество результатов
            with_photos_only: Только с фото

        Returns:
            Список testimonials
        """
        messages = self._load_category(category)

        # Фильтруем по подкатегории
        filtered = []
        for msg in messages:
            # Проверяем прямое поле subcategory (основной способ)
            msg_subcategory = msg.get('subcategory', '')
            if msg_subcategory == subcategory:
                if not with_photos_only or msg.get('has_photo'):
                    filtered.append(msg)
                continue

            # Fallback: проверяем categories dict
            categories = msg.get('categories', {})
            if category.value in categories:
                subcats = categories[category.value]
                if subcategory in subcats:
                    if not with_photos_only or msg.get('has_photo'):
                        filtered.append(msg)

        if not filtered:
            return []

        count = min(count, len(filtered))
        return random.sample(filtered, count)

    def search(
        self,
        query: str,
        category: Optional[TestimonialCategory] = None,
        limit: int = 10,
        with_photos_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Поиск testimonials по ключевым словам.

        Args:
            query: Поисковый запрос
            category: Искать в конкретной категории (или во всех)
            limit: Максимальное количество результатов
            with_photos_only: Только с фото

        Returns:
            Список найденных testimonials
        """
        query_lower = query.lower()
        results = []

        # Определяем, в каких категориях искать
        categories = [category] if category else list(TestimonialCategory)

        for cat in categories:
            messages = self._load_category(cat)
            for msg in messages:
                if len(results) >= limit:
                    break

                # Проверяем, есть ли запрос в тексте
                text = msg.get('full_text', msg.get('text', '')).lower()
                if query_lower in text:
                    if not with_photos_only or msg.get('has_photo'):
                        results.append(msg)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику по всем категориям."""
        return self.summary.get('stats', {})

    def get_category_info(self, category: TestimonialCategory) -> Dict[str, Any]:
        """Получить информацию о конкретной категории."""
        categories_info = self.summary.get('categories', {})
        return categories_info.get(category.value, {})

    def get_absolute_path(self, relative_path: str) -> Path:
        """
        Преобразует относительный путь из metadata.json в абсолютный.

        Args:
            relative_path: Путь вида "content/testimonials/before_after/media/msg_71_photo.jpg"

        Returns:
            Абсолютный путь к файлу
        """
        if relative_path.startswith('content/'):
            return self.project_root / relative_path
        else:
            # Если путь уже абсолютный или другого формата
            path = Path(relative_path)
            if path.is_absolute():
                return path
            # Пробуем найти в base_dir
            return self.base_dir / relative_path

    def get_media_files(self, testimonial: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Получает список медиа-файлов из testimonial с абсолютными путями.

        Args:
            testimonial: Данные testimonial

        Returns:
            Список файлов с абсолютными путями
        """
        files = []
        for file_info in testimonial.get('files', []):
            local_path = file_info.get('local_path')
            if local_path:
                abs_path = self.get_absolute_path(local_path)
                files.append({
                    'path': abs_path,
                    'type': file_info.get('type', 'photo'),
                    'width': file_info.get('width'),
                    'height': file_info.get('height'),
                    'exists': abs_path.exists()
                })
        return files

    def format_testimonial(self, testimonial: Dict[str, Any]) -> str:
        """
        Форматирует testimonial для вставки в сообщение бота.

        Args:
            testimonial: Данные testimonial

        Returns:
            Отформатированный текст
        """
        text = testimonial.get('full_text', testimonial.get('text', ''))
        author = testimonial.get('from', 'Партнёр NL')
        date = testimonial.get('date', '')

        # Обрезаем дату до даты (без времени)
        if date and 'T' in date:
            date = date.split('T')[0]

        # Обрезаем текст, если слишком длинный
        max_length = 800
        if len(text) > max_length:
            text = text[:max_length] + '...'

        result = f"📝 *История от {author}*"
        if date:
            result += f" ({date})"
        result += f"\n\n{text}"

        return result

    def get_text_only(
        self,
        category: TestimonialCategory,
        count: int = 1
    ) -> List[str]:
        """
        Получить только текст testimonials (без метаданных).
        Удобно для вставки в промпты AI.

        Args:
            category: Категория
            count: Количество

        Returns:
            Список текстов
        """
        testimonials = self.get_random(category, count)
        return [t.get('full_text', t.get('text', '')) for t in testimonials]

    def get_by_media_type(
        self,
        media_type: str,
        category: Optional[TestimonialCategory] = None,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Получить testimonials по типу медиа.

        Args:
            media_type: Тип медиа ('photo', 'video', 'video_message', 'voice', 'audio')
            category: Искать в конкретной категории (или во всех)
            count: Максимальное количество результатов

        Returns:
            Список testimonials с указанным типом медиа
        """
        results = []
        categories = [category] if category else list(TestimonialCategory)

        for cat in categories:
            messages = self._load_category(cat)
            for msg in messages:
                if len(results) >= count:
                    break

                media_types = msg.get('media_types', [])
                if media_type in media_types:
                    results.append(msg)

        return results

    def get_videos(
        self,
        category: Optional[TestimonialCategory] = None,
        include_video_messages: bool = True,
        max_duration: Optional[int] = None,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Получить видео testimonials с фильтрацией.

        Args:
            category: Категория (или все)
            include_video_messages: Включать кружочки (video_message)
            max_duration: Максимальная длительность видео в секундах
            count: Количество результатов

        Returns:
            Список видео testimonials
        """
        video_types = ['video']
        if include_video_messages:
            video_types.append('video_message')

        results = []
        categories = [category] if category else list(TestimonialCategory)

        for cat in categories:
            messages = self._load_category(cat)
            for msg in messages:
                if len(results) >= count:
                    break

                media_types = msg.get('media_types', [])
                if any(vt in media_types for vt in video_types):
                    # Фильтр по длительности
                    if max_duration:
                        duration = msg.get('video_duration', 0)
                        if duration > max_duration:
                            continue

                    results.append(msg)

        return results

    def get_voice_messages(
        self,
        category: Optional[TestimonialCategory] = None,
        max_duration: Optional[int] = None,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Получить голосовые сообщения.

        Args:
            category: Категория (или все)
            max_duration: Максимальная длительность в секундах
            count: Количество результатов

        Returns:
            Список голосовых сообщений
        """
        results = []
        categories = [category] if category else list(TestimonialCategory)

        for cat in categories:
            messages = self._load_category(cat)
            for msg in messages:
                if len(results) >= count:
                    break

                if msg.get('has_voice'):
                    # Фильтр по длительности
                    if max_duration:
                        duration = msg.get('audio_duration', 0)
                        if duration > max_duration:
                            continue

                    results.append(msg)

        return results

    def _load_pairs(self) -> List[Dict[str, Any]]:
        """Загружает пары ДО/ПОСЛЕ из pairs.json."""
        pairs_path = self.base_dir / "before_after" / "pairs.json"
        if not pairs_path.exists():
            return []

        with open(pairs_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('pairs', [])

    def get_pair(
        self,
        subcategory: Optional[str] = None,
        count: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Получить пары фото ДО/ПОСЛЕ.

        Args:
            subcategory: Подкатегория (collagen, drain_effect, weight_loss, etc.)
            count: Количество пар

        Returns:
            Список пар с before_file и after_file
        """
        pairs = self._load_pairs()

        if not pairs:
            return []

        # Фильтруем по подкатегории
        if subcategory:
            pairs = [p for p in pairs if p.get('subcategory') == subcategory]

        if not pairs:
            return []

        # Выбираем случайные пары
        count = min(count, len(pairs))
        return random.sample(pairs, count)

    def get_pair_files(self, pair: Dict[str, Any]) -> Tuple[Optional[Path], Optional[Path]]:
        """
        Получает абсолютные пути к файлам пары.

        Args:
            pair: Пара из get_pair()

        Returns:
            (before_path, after_path): пути к файлам ДО и ПОСЛЕ
        """
        before_path = None
        after_path = None

        if pair.get('before_file'):
            before_path = self.get_absolute_path(pair['before_file'])
        if pair.get('after_file'):
            after_path = self.get_absolute_path(pair['after_file'])

        return before_path, after_path


# Глобальный экземпляр для удобства
_global_manager: Optional[TestimonialsManager] = None


def get_testimonials_manager() -> TestimonialsManager:
    """Получить глобальный экземпляр менеджера (singleton)."""
    global _global_manager
    if _global_manager is None:
        _global_manager = TestimonialsManager()
    return _global_manager
