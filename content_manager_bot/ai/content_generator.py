"""
Генератор контента V3 — трёхступенчатый пайплайн

ФИЛОСОФИЯ: Документируем, а не создаём.
- Реальная персона Данила (из интервью)
- Трёхступенчатая генерация: Планировщик → Писатель → Критик
- Без фейка, без впаривания, без AI-слов
- Валидация на шаблоны, ботовость, выдуманные сцены

Поддерживает: Deepseek (основной), Claude, YandexGPT, GigaChat
"""
import random
import re
from typing import Optional, Tuple, List
from datetime import datetime
from loguru import logger

from shared.ai_clients.gigachat_client import GigaChatClient
from shared.ai_clients.yandexgpt_client import YandexGPTClient
# YandexART удалён — используем готовые фото из базы unified_products/
from shared.ai_clients.anthropic_client import AnthropicClient
from shared.ai_clients.deepseek_client import DeepseekClient
from shared.config.settings import settings
from shared.style_monitor import get_style_service
from shared.rag import get_rag_engine, RAGEngine
# V2: Новая система промптов — трёхступенчатый пайплайн
from content_manager_bot.ai.prompts_v2 import (
    get_system_prompt,
    get_post_prompt,
    get_planner_prompt,
    get_writer_prompt,
    get_critic_prompt,
    validate_post,
    POST_TYPES,
    ALL_POST_TYPES
)
from content_manager_bot.database.models import ImportedPost
from content_manager_bot.utils.product_reference import ProductReferenceManager
from shared.media import media_library  # НОВОЕ: индексированная медиа-библиотека
from shared.testimonials import get_testimonials_manager, TestimonialCategory  # Testimonials (до/после, чеки)
from content_manager_bot.ai.series_manager import get_series_manager, SeriesManager  # Серийный контент (03.02.2026)


# V2: Premium типы убраны — все посты генерируются одинаково основным клиентом


class ContentGenerator:
    """Генератор контента для Telegram канала (гибридный: GigaChat/YandexGPT + GPT-4)"""

    def __init__(self):
        """Инициализация генератора"""
        # V2: Промпты берутся из prompts_v2 напрямую (функции get_system_prompt, get_post_prompt)

        # Определяем основную модель из настроек
        main_model = settings.content_manager_ai_model.lower()

        # Инициализируем клиенты
        self.gigachat_client = None
        self.yandexgpt_client = None
        self.openai_client = None
        self.anthropic_client = None
        self.deepseek_client = None
        # YandexART удалён
        self.main_client = None
        self.main_model_name = "unknown"

        # Deepseek (приоритет — дёшево и качественно)
        if settings.deepseek_api_key:
            try:
                self.deepseek_client = DeepseekClient()
                self.main_client = self.deepseek_client
                self.main_model_name = "deepseek"
                logger.info(f"ContentGenerator initialized with Deepseek: {settings.deepseek_model}")
            except Exception as e:
                logger.warning(f"Deepseek init failed: {e}, trying next provider")

        # Claude (если Deepseek не настроен)
        if not self.main_client and "claude" in main_model and settings.anthropic_api_key:
            try:
                self.anthropic_client = AnthropicClient()
                self.main_client = self.anthropic_client
                self.main_model_name = "claude"
                logger.info(f"ContentGenerator initialized with Claude as main model: {settings.content_manager_ai_model}")
            except Exception as e:
                logger.warning(f"Claude init failed: {e}, falling back to other models")

        # YandexGPT (если настроен)
        if not self.main_client and (main_model.startswith("yandex") or "yandex" in main_model):
            if settings.yandex_folder_id and settings.yandex_private_key:
                self.yandexgpt_client = YandexGPTClient()
                self.main_client = self.yandexgpt_client
                self.main_model_name = "yandexgpt"
                logger.info("ContentGenerator initialized with YandexGPT as main model")
            else:
                logger.warning("YandexGPT selected but credentials missing, falling back to GigaChat")

        # GigaChat (бесплатный, запасной вариант)
        if not self.main_client and settings.gigachat_auth_token:
            self.gigachat_client = GigaChatClient(
                auth_token=settings.gigachat_auth_token,
                model="GigaChat"
            )
            self.main_client = self.gigachat_client
            self.main_model_name = "gigachat"
            logger.info("ContentGenerator initialized with GigaChat as main model")

        # NOTE: OpenAI отключён - заблокирован в России (403 unsupported_country_region_territory)
        # Все типы постов используют основной клиент (Claude или YandexGPT)

        # YandexART удалён — используем только готовые фото из базы

        # Менеджер референсных изображений продуктов (старый, для совместимости)
        self.product_reference = ProductReferenceManager()

        # НОВОЕ: индексированная медиа-библиотека (< 20ms поиск)
        self.media_library = media_library

        # НОВОЕ: менеджер testimonials (до/после, чеки)
        self.testimonials_manager = get_testimonials_manager()
        logger.info("TestimonialsManager initialized for content generation")

        if not self.main_client:
            raise ValueError("No AI client configured! Check .env settings")

        # V2: Персоны убраны — один стиль (дерзкий, 21 год)
        # Образцы стиля из внешних каналов отключены
        self.use_style_samples = False

        # RAG система для использования базы знаний
        self._rag_engine: Optional[RAGEngine] = None
        self.use_knowledge_base = True  # Использовать примеры из базы знаний
        logger.info("RAG knowledge base integration enabled")

        # Система серийного контента (cliffhangers)
        self.series_manager: SeriesManager = get_series_manager()
        logger.info("SeriesManager initialized for serial content")

    async def _get_rag_engine(self) -> RAGEngine:
        """Получить RAG engine (ленивая инициализация)."""
        if self._rag_engine is None:
            self._rag_engine = await get_rag_engine()
        return self._rag_engine

    def _get_testimonials_context(self, post_type: str, count: int = 2) -> str:
        """
        Получает реальные testimonials как примеры для промпта.

        Для success_story и transformation использует реальные истории
        из базы before_after, чтобы AI генерировал контент на основе
        настоящих примеров, а не выдумывал.

        Args:
            post_type: Тип поста
            count: Количество примеров

        Returns:
            str: Отформатированный блок с примерами testimonials
        """
        # Типы постов, для которых нужны testimonials
        testimonial_types = ["success_story", "transformation", "motivation"]

        if post_type not in testimonial_types:
            return ""

        try:
            testimonials_manager = get_testimonials_manager()

            # Выбираем категорию в зависимости от типа поста
            if post_type in ["success_story", "transformation"]:
                category = TestimonialCategory.BEFORE_AFTER
            else:
                category = TestimonialCategory.SUCCESS_STORIES

            # Получаем тексты реальных историй
            texts = testimonials_manager.get_text_only(category, count=count)

            if not texts:
                return ""

            # Форматируем примеры
            examples = []
            for i, text in enumerate(texts, 1):
                # Обрезаем слишком длинные тексты
                if len(text) > 500:
                    text = text[:500] + "..."
                if text.strip():
                    examples.append(f"РЕАЛЬНАЯ ИСТОРИЯ {i}:\n«{text.strip()}»")

            if not examples:
                return ""

            context_block = """

═══════════════════════════════════════════
📖 РЕАЛЬНЫЕ ИСТОРИИ ПАРТНЁРОВ (ОБЯЗАТЕЛЬНО ИСПОЛЬЗУЙ!)
═══════════════════════════════════════════

{}

⚠️ ИНСТРУКЦИЯ:
• Возьми ОДНУ из этих историй как основу
• Перескажи её от лица recurring character (Маша, Валентина Петровна, Артём)
• НЕ ВЫДУМЫВАЙ новые факты — используй только то, что есть в примерах
• Добавь свою реакцию/комментарий как Данил
""".format("\n\n---\n\n".join(examples))

            logger.info(f"Added {len(examples)} real testimonials for {post_type}")
            return context_block

        except Exception as e:
            logger.warning(f"Could not get testimonials context: {e}")
            return ""

    async def _get_knowledge_context(
        self,
        post_type: str,
        custom_topic: Optional[str] = None,
        limit: int = 3
    ) -> str:
        """
        Получает релевантный контекст из базы знаний для генерации поста.

        Args:
            post_type: Тип поста
            custom_topic: Дополнительная тема
            limit: Максимум документов

        Returns:
            str: Отформатированный контекст из базы знаний
        """
        if not self.use_knowledge_base:
            return ""

        # Маппинг типов постов на категории RAG
        type_to_category = {
            "product": "products",
            "product_deep_dive": "products",
            "product_comparison": "products",
            "motivation": "motivation",
            "success_story": "success_stories",
            "transformation": "success_stories",
            "business_lifestyle": "business",
            "business": "business",
            "business_myths": "business",
            "tips": "training",
            "news": "news",
            "promo": "promo_examples",
            "myth_busting": "faq",
            "faq": "faq"
        }

        category = type_to_category.get(post_type, None)

        # Формируем поисковый запрос
        search_query = f"пост {post_type}"
        if custom_topic:
            search_query = f"{custom_topic} {post_type}"

        try:
            rag_engine = await self._get_rag_engine()
            results = await rag_engine.retrieve(
                query=search_query,
                category=category,
                top_k=limit,
                min_similarity=0.3  # Низкий порог для большего покрытия
            )

            if not results:
                # Пробуем без категории
                results = await rag_engine.retrieve(
                    query=search_query,
                    category=None,
                    top_k=limit,
                    min_similarity=0.25
                )

            if not results:
                return ""

            # Форматируем примеры
            examples = []
            for i, doc in enumerate(results, 1):
                # Берём только первые 600 символов для краткости
                content = doc.content[:600]
                if len(doc.content) > 600:
                    content += "..."
                examples.append(f"ПРИМЕР {i} (источник: {doc.source or 'база знаний'}):\n{content}")

            context_block = """

### ПРИМЕРЫ ИЗ БАЗЫ ЗНАНИЙ (используй как образец стиля и информации):

{}

### ВАЖНО:
- Используй факты и стиль из примеров
- НЕ копируй дословно, создавай уникальный контент
- Адаптируй под текущую тему и персону
""".format("\n\n---\n\n".join(examples))

            logger.info(f"Added {len(results)} knowledge base examples for {post_type}")
            return context_block

        except Exception as e:
            logger.warning(f"Could not get knowledge context: {e}")
            return ""

    async def _get_inspiration_topic(
        self,
        post_type: str
    ) -> Optional[Tuple[str, int]]:
        """
        Получает неиспользованный импортированный пост как тему/вдохновение.

        Args:
            post_type: Тип поста для маппинга на категорию

        Returns:
            Tuple[str, int]: (текст темы, id импортированного поста) или None
        """
        # Маппинг типов постов на категории импорта
        category_map = {
            "product": "product",
            "motivation": "motivation",
            "success_story": "success",
            "transformation": "success",
            "business_lifestyle": "lifestyle",
            "business": "business",
            "business_myths": "business",
            "tips": "tips",
            "news": "news",
            "promo": "news",
            "myth_busting": "motivation",
            "faq": "tips"
        }
        category = category_map.get(post_type, "motivation")

        try:
            from sqlalchemy import select
            from shared.database.base import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                # Получаем неиспользованный пост с наибольшим quality_score
                result = await session.execute(
                    select(ImportedPost)
                    .where(ImportedPost.category == category)
                    .where(ImportedPost.is_used == False)
                    .order_by(ImportedPost.quality_score.desc())
                    .limit(1)
                )
                post = result.scalar_one_or_none()

                if post:
                    # Берём первые 500 символов как тему
                    topic_text = post.text[:500]
                    if len(post.text) > 500:
                        topic_text += "..."
                    logger.info(f"Found inspiration topic from '{post.source_channel}' (id={post.id}, category={category})")
                    return (topic_text, post.id)

                # Fallback: пробуем любую категорию
                result = await session.execute(
                    select(ImportedPost)
                    .where(ImportedPost.is_used == False)
                    .order_by(ImportedPost.quality_score.desc())
                    .limit(1)
                )
                post = result.scalar_one_or_none()

                if post:
                    topic_text = post.text[:500]
                    if len(post.text) > 500:
                        topic_text += "..."
                    logger.info(f"Found fallback inspiration topic (id={post.id}, category={post.category})")
                    return (topic_text, post.id)

            logger.info(f"No unused inspiration topics found for {post_type}")
            return None

        except Exception as e:
            logger.warning(f"Could not get inspiration topic: {e}")
            return None

    async def _mark_inspiration_used(self, imported_post_id: int, generated_post_id: Optional[int] = None):
        """
        Отмечает импортированный пост как использованный.

        Args:
            imported_post_id: ID импортированного поста
            generated_post_id: ID сгенерированного поста (опционально)
        """
        try:
            from sqlalchemy import update
            from shared.database.base import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(ImportedPost)
                    .where(ImportedPost.id == imported_post_id)
                    .values(
                        is_used=True,
                        used_at=datetime.utcnow(),
                        used_for_post_id=generated_post_id
                    )
                )
                await session.commit()
                logger.info(f"Marked inspiration topic {imported_post_id} as used")

        except Exception as e:
            logger.error(f"Could not mark inspiration as used: {e}")

    def _get_content_style_guide(self) -> str:
        """
        Читает примеры из CONTENT_STYLE_GUIDE.md для обучения стилю.

        Returns:
            str: Отформатированные примеры из гайда или пустая строка
        """
        try:
            from pathlib import Path

            # Путь к файлу относительно content_manager_bot/ai/
            style_guide_path = Path(__file__).parent.parent.parent / "docs" / "CONTENT_STYLE_GUIDE.md"

            if not style_guide_path.exists():
                logger.warning(f"CONTENT_STYLE_GUIDE.md not found at {style_guide_path}")
                return ""

            content = style_guide_path.read_text(encoding="utf-8")

            # Извлекаем примеры из секции "Примеры живых постов"
            import re
            examples_section = re.search(
                r"## Примеры живых постов.*?(?=##|\Z)",
                content,
                re.DOTALL
            )

            if examples_section:
                examples_text = examples_section.group(0)
                return f"""

### 📚 ПРИМЕРЫ СТИЛЯ (ОБЯЗАТЕЛЬНО СЛЕДУЙ ЭТОМУ ФОРМАТУ):

{examples_text}

### ⚠️ ВАЖНО:
- Используй ТОТ ЖЕ живой стиль написания
- Короткие абзацы (1-2 предложения)
- HTML-теги: <blockquote>, <b>, <i>, <tg-spoiler>
- Разговорный язык, как в примерах
- Вопрос или CTA в конце
"""

            logger.info("Loaded style examples from CONTENT_STYLE_GUIDE.md")
            return ""

        except Exception as e:
            logger.warning(f"Could not load CONTENT_STYLE_GUIDE.md: {e}")
            return ""

    async def _get_style_samples(
        self,
        post_type: str,
        limit: int = 3
    ) -> List[str]:
        """
        Получает образцы постов из каналов-образцов для обучения стилю.

        ВРЕМЕННО ОТКЛЮЧЕНО: Telethon API keys не настроены, вызов тормозит.
        Включить когда будут настроены TELETHON_API_ID и TELETHON_API_HASH.

        Args:
            post_type: Тип поста для маппинга на категорию стиля
            limit: Максимум образцов

        Returns:
            List[str]: Список текстов образцов (пустой пока отключено)
        """
        # ВРЕМЕННО ОТКЛЮЧЕНО — Telethon тормозит без API keys
        # TODO: Включить когда будут настроены TELETHON_API_ID и TELETHON_API_HASH
        return []

        # Оригинальный код закомментирован:
        # if not self.use_style_samples:
        #     return []
        #
        # type_to_category = {
        #     "product": "product",
        #     "motivation": "motivation",
        #     "success_story": "motivation",
        #     "transformation": "motivation",
        #     "business_lifestyle": "lifestyle",
        #     "business": "business",
        #     "business_myths": "business",
        #     "tips": "general",
        #     "news": "general",
        #     "promo": "general",
        #     "myth_busting": "general",
        #     "faq": "general"
        # }
        #
        # style_category = type_to_category.get(post_type, "general")
        #
        # try:
        #     style_service = get_style_service()
        #     samples = await style_service.get_style_samples(
        #         style_category=style_category,
        #         limit=limit,
        #         min_quality=7
        #     )
        #
        #     if not samples:
        #         samples = await style_service.get_style_samples(
        #             style_category=None,
        #             limit=limit,
        #             min_quality=None
        #         )
        #
        #     return [s.text for s in samples if s.text]
        #
        # except Exception as e:
        #     logger.debug(f"Could not get style samples: {e}")
        #     return []

    def _format_style_examples(self, samples: List[str]) -> str:
        """
        Форматирует образцы стиля для добавления в промпт.

        Args:
            samples: Список текстов образцов

        Returns:
            str: Отформатированный блок с образцами
        """
        if not samples:
            return ""

        examples_text = "\n\n---\n\n".join([
            f"ПРИМЕР {i+1}:\n{sample[:500]}{'...' if len(sample) > 500 else ''}"
            for i, sample in enumerate(samples)
        ])

        return f"""

### ОБРАЗЦЫ СТИЛЯ (ориентируйся на эти примеры):

{examples_text}

### ВАЖНО:
- Используй похожий тон и структуру
- Сохраняй свою уникальность, но учись у примеров
- НЕ копируй дословно, создавай оригинальный контент
"""

    async def _get_diary_entries(self, limit: int = 5) -> str:
        """
        Получает последние записи дневника админа для контекста генерации.
        Возвращает отформатированный текстовый блок.
        """
        try:
            from sqlalchemy import select
            from shared.database.base import AsyncSessionLocal
            from content_manager_bot.database.models import DiaryEntry

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(DiaryEntry.entry_text, DiaryEntry.created_at)
                    .order_by(DiaryEntry.created_at.desc())
                    .limit(limit)
                )
                rows = result.all()

                if not rows:
                    return ""

                entries_block = "\n\n📓 ДНЕВНИК АВТОРА (реальные события и мысли — используй как контекст):\n"
                for entry_text, created_at in rows:
                    date_str = created_at.strftime("%d.%m")
                    preview = entry_text[:200].replace("\n", " ").strip()
                    if len(entry_text) > 200:
                        preview += "..."
                    entries_block += f"• [{date_str}] {preview}\n"
                entries_block += "\nИспользуй эти записи как вдохновение для НАСТОЯЩИХ тем. НЕ цитируй дословно.\n"

                logger.info(f"[MEMORY] Loaded {len(rows)} diary entries for context")
                return entries_block

        except Exception as e:
            logger.warning(f"[MEMORY] Failed to load diary entries: {e}")
            return ""

    async def _get_director_context(self, segment: str) -> str:
        """
        Собирает контекст от AI Director для промпта планировщика.
        Включает: channel memory, competitor insights, reflection rules, trends.

        Args:
            segment: Сегмент канала

        Returns:
            str: Отформатированный блок контекста (~200 токенов)
        """
        parts = []

        try:
            from content_manager_bot.director import (
                get_channel_memory,
                get_trend_detector,
            )

            # 1. Channel Memory (structured state)
            memory = get_channel_memory()
            memory_context = await memory.get_context_for_prompt(segment)
            if memory_context:
                parts.append(memory_context)

            # 2. Trend context
            detector = get_trend_detector()
            trend_context = await detector.get_trend_context(segment)
            if trend_context:
                parts.append(trend_context)

        except Exception as e:
            logger.warning(f"[DIRECTOR] Failed to get director context: {e}")

        if not parts:
            return ""

        return "\n".join(parts)

    async def _get_recent_published(self, limit: int = 15, segment: str = None) -> list:
        """
        Получает последние опубликованные посты для памяти.
        Возвращает [(preview, post_type, ending), ...] — превью + тип + концовка.

        Args:
            limit: Макс. кол-во постов
            segment: Если указан — фильтрует только посты этого сегмента
        """
        try:
            from sqlalchemy import select, and_
            from shared.database.base import AsyncSessionLocal
            from content_manager_bot.database.models import Post

            async with AsyncSessionLocal() as session:
                query = (
                    select(Post.content, Post.post_type)
                    .where(Post.status == "published")
                )

                if segment:
                    query = query.where(Post.segment == segment)

                query = query.order_by(Post.published_at.desc().nullslast()).limit(limit)

                result = await session.execute(query)
                rows = result.all()

                recent = []
                for content, post_type in rows:
                    preview = content[:200].replace("\n", " ").strip()
                    if len(content) > 200:
                        preview += "..."

                    ending = content[-100:].replace("\n", " ").strip() if len(content) > 100 else content.replace("\n", " ").strip()

                    recent.append((preview, post_type or "unknown", ending))

                if recent:
                    logger.info(f"[MEMORY] Loaded {len(recent)} recent published posts" +
                               (f" (segment={segment})" if segment else ""))
                return recent

        except Exception as e:
            logger.warning(f"[MEMORY] Failed to load recent posts: {e}")
            return []

    def _get_client_for_post_type(self, post_type: str):
        """
        Выбирает AI клиент в зависимости от типа поста

        Args:
            post_type: Тип поста

        Returns:
            AI клиент (основной клиент для всех типов, OpenAI отключён из-за блокировки в РФ)
        """
        # NOTE: OpenAI отключён - заблокирован в России (403 unsupported_country_region_territory)
        # V2: Все типы постов используют основной клиент (Deepseek/Claude/YandexGPT)
        logger.info(f"Using {self.main_model_name} for post type: {post_type}")

        return self.main_client, self.main_model_name

    async def generate_post(
        self,
        post_type: str,
        custom_topic: Optional[str] = None,
        temperature: Optional[float] = None,
        segment: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Генерирует пост для Telegram канала.

        Трёхступенчатый пайплайн:
        1. ПЛАНИРОВЩИК (temperature=0.95) — придумывает план поста
        2. ПИСАТЕЛЬ (temperature=0.9) — пишет текст по плану
        3. КРИТИК (temperature=0.7) — проверяет и исправляет "ботовость"

        Fallback: одноступенчатая генерация если пайплайн падает.

        Args:
            post_type: Тип поста (observation, question, thought, journey, honesty, absurd, self_irony)
            custom_topic: Дополнительная тема для уточнения
            temperature: Базовая креативность (корректируется для каждого шага)
            segment: Сегмент канала (zozh, business и т.д.) — адаптирует стиль и темы

        Returns:
            Tuple[str, str]: (текст поста, использованный промпт)
        """
        system_prompt = get_system_prompt(segment=segment)
        ai_client, model_name = self._get_client_for_post_type(post_type)

        logger.info(f"Generating {post_type} post with 3-stage pipeline ({model_name})" +
                   (f" about '{custom_topic}'" if custom_topic else "") +
                   (f" [segment={segment}]" if segment else ""))

        try:
            # ═══════════════════════════════════════════════════
            # ПАМЯТЬ: загружаем историю опубликованных постов
            # ═══════════════════════════════════════════════════
            recent_posts = await self._get_recent_published(limit=15, segment=segment)

            # ═══════════════════════════════════════════════════
            # ДНЕВНИК: загружаем записи админа для контекста
            # ═══════════════════════════════════════════════════
            diary_context = await self._get_diary_entries(limit=5)

            # ═══════════════════════════════════════════════════
            # AI DIRECTOR: собираем контекст (channel memory + insights + trends)
            # ═══════════════════════════════════════════════════
            director_context = ""
            if segment:
                director_context = await self._get_director_context(segment)

            # ═══════════════════════════════════════════════════
            # ШАГ 1: ПЛАНИРОВЩИК — придумывает план, НЕ текст
            # ═══════════════════════════════════════════════════
            planner_prompt = get_planner_prompt(post_type, custom_topic, recent_posts=recent_posts, diary_entries=diary_context, segment=segment, director_context=director_context)

            plan = await ai_client.generate_response(
                system_prompt=system_prompt,
                user_message=planner_prompt,
                temperature=0.95,  # Высокая креативность для разнообразия планов
                max_tokens=500
            )

            logger.info(f"[PIPELINE] Step 1/3 PLANNER done: {len(plan)} chars")

            # ═══════════════════════════════════════════════════
            # ШАГ 2: ПИСАТЕЛЬ — пишет текст по плану
            # ═══════════════════════════════════════════════════
            writer_prompt = get_writer_prompt(plan, post_type)

            draft = await ai_client.generate_response(
                system_prompt=system_prompt,
                user_message=writer_prompt,
                temperature=temperature or 0.9,
                max_tokens=800
            )

            logger.info(f"[PIPELINE] Step 2/3 WRITER done: {len(draft)} chars")

            # ═══════════════════════════════════════════════════
            # ШАГ 3: КРИТИК — проверяет и исправляет
            # ═══════════════════════════════════════════════════
            critic_prompt = get_critic_prompt(draft)

            content = await ai_client.generate_response(
                system_prompt=system_prompt,
                user_message=critic_prompt,
                temperature=0.7,  # Низкая — критик должен быть точным
                max_tokens=800
            )

            logger.info(f"[PIPELINE] Step 3/3 CRITIC done: {len(content)} chars")

            # Очищаем контент от возможных артефактов
            content = self._clean_content(content)

            # ═══════════════════════════════════════════════════
            # ПОСТ-КРИТИК: проверка уникальности концовки (только для тематических)
            # ═══════════════════════════════════════════════════
            if segment and recent_posts:
                recent_endings = [item[2] for item in recent_posts[:3] if len(item) == 3]
                current_ending = content[-80:] if len(content) > 80 else content

                for prev_ending in recent_endings:
                    current_words = set(current_ending.lower().split())
                    prev_words = set(prev_ending.lower().split())
                    if current_words and prev_words:
                        overlap = len(current_words & prev_words) / min(len(current_words), len(prev_words))
                        if overlap > 0.4:
                            logger.warning(f"[PIPELINE] Ending too similar to recent post (overlap={overlap:.0%}), rewriting")
                            rewrite_prompt = (
                                f"Вот пост:\n\n---\n{content}\n---\n\n"
                                "Проблема: концовка слишком похожа на предыдущий пост.\n"
                                "Перепиши ТОЛЬКО КОНЦОВКУ (последние 1-2 предложения). Сделай её уникальной.\n"
                                "Варианты: вопрос, обрыв мысли, панч, самоирония, тишина.\n\n"
                                "Выдай ПОЛНЫЙ текст поста с новой концовкой."
                            )
                            content = await ai_client.generate_response(
                                system_prompt=system_prompt,
                                user_message=rewrite_prompt,
                                temperature=0.85,
                                max_tokens=800
                            )
                            content = self._clean_content(content)
                            logger.info("[PIPELINE] Ending rewritten for uniqueness")
                            break

            # Валидация поста — проверяем на фейк, AI-слова, шаблоны
            validation_errors = validate_post(content)
            if validation_errors:
                logger.warning(f"Post validation issues: {validation_errors}")
                # Пробуем перегенерировать через критика с фидбэком
                feedback = ", ".join(validation_errors)
                fix_prompt = get_critic_prompt(content) + f"\n\n⚠️ ДОПОЛНИТЕЛЬНЫЕ ПРОБЛЕМЫ: {feedback}\nИсправь ВСЕ эти проблемы."

                content = await ai_client.generate_response(
                    system_prompt=system_prompt,
                    user_message=fix_prompt,
                    temperature=0.7,
                    max_tokens=800
                )
                content = self._clean_content(content)
                logger.info("[PIPELINE] Re-critiqued post after validation")

            # Собираем промпт для логирования (план + черновик)
            used_prompt = f"[PLAN]\n{plan}\n\n[DRAFT]\n{draft}"

            logger.info(f"[PIPELINE] Post generated successfully: {len(content)} chars")
            return content, used_prompt

        except Exception as e:
            logger.error(f"3-stage pipeline failed: {e}")

            # Fallback 1: одноступенчатая генерация через тот же клиент
            try:
                logger.warning("Falling back to single-stage generation...")
                user_prompt = get_post_prompt(post_type, custom_topic)

                content = await ai_client.generate_response(
                    system_prompt=system_prompt,
                    user_message=user_prompt,
                    temperature=temperature or 0.9,
                    max_tokens=800
                )
                content = self._clean_content(content)
                logger.info(f"Single-stage fallback successful: {len(content)} chars")
                return content, user_prompt

            except Exception as fallback1_error:
                logger.error(f"Single-stage fallback failed: {fallback1_error}")

            # Fallback 2: YandexGPT
            try:
                logger.warning("Trying YandexGPT as last resort...")
                fallback_client = YandexGPTClient()
                user_prompt = get_post_prompt(post_type, custom_topic)

                content = await fallback_client.generate_response(
                    system_prompt=system_prompt,
                    user_message=user_prompt,
                    temperature=temperature or 0.9,
                    max_tokens=800
                )
                content = self._clean_content(content)
                logger.info(f"YandexGPT fallback successful: {len(content)} chars")
                return content, user_prompt

            except Exception as fallback2_error:
                logger.error(f"YandexGPT fallback also failed: {fallback2_error}")
                raise

    async def regenerate_post(
        self,
        original_post: str,
        feedback: str,
        post_type: Optional[str] = None,
        temperature: float = 0.9
    ) -> str:
        """
        Перегенерирует пост с учётом обратной связи (V2)

        Args:
            original_post: Оригинальный пост
            feedback: Комментарий от админа
            post_type: Тип поста (для выбора модели)
            temperature: Креативность

        Returns:
            str: Новый текст поста
        """
        try:
            # V2: Простой промпт для перегенерации
            prompt = f"""
Вот пост который нужно переписать:

---
{original_post}
---

Фидбэк: {feedback}

Перепиши пост с учётом фидбэка. Сохраняй стиль — дерзкий, с юмором, короткий.
Выдай ТОЛЬКО текст нового поста.
"""

            # Выбираем клиент
            if post_type:
                ai_client, model_name = self._get_client_for_post_type(post_type)
            else:
                ai_client, model_name = self.main_client, self.main_model_name

            content = await ai_client.generate_response(
                system_prompt=get_system_prompt(),
                user_message=prompt,
                temperature=temperature,
                max_tokens=800
            )

            content = self._clean_content(content)
            logger.info(f"Post regenerated successfully with {model_name}: {len(content)} chars")

            return content

        except Exception as e:
            logger.error(f"Error regenerating post with primary AI: {e}")

            # Runtime fallback на YandexGPT
            try:
                logger.warning("Trying YandexGPT as fallback for regeneration...")
                fallback_client = YandexGPTClient()

                content = await fallback_client.generate_response(
                    system_prompt=get_system_prompt(),
                    user_message=prompt,
                    temperature=temperature,
                    max_tokens=800
                )

                content = self._clean_content(content)
                logger.info(f"YandexGPT fallback successful for regeneration: {len(content)} chars")
                return content

            except Exception as fallback_error:
                logger.error(f"YandexGPT fallback also failed: {fallback_error}")
                raise

    async def edit_post(
        self,
        original_post: str,
        edit_instructions: str,
        post_type: Optional[str] = None
    ) -> str:
        """
        Редактирует пост согласно инструкциям (V2)

        Args:
            original_post: Оригинальный пост
            edit_instructions: Инструкции по редактированию
            post_type: Тип поста (для выбора модели)

        Returns:
            str: Отредактированный текст
        """
        try:
            # V2: Простой промпт для редактирования
            prompt = f"""
Вот пост:

---
{original_post}
---

Инструкции: {edit_instructions}

Отредактируй пост согласно инструкциям. Сохраняй стиль.
Выдай ТОЛЬКО текст отредактированного поста.
"""

            # Выбираем клиент
            if post_type:
                ai_client, model_name = self._get_client_for_post_type(post_type)
            else:
                ai_client, model_name = self.main_client, self.main_model_name

            content = await ai_client.generate_response(
                system_prompt=get_system_prompt(),
                user_message=prompt,
                temperature=0.6,  # Меньше креативности для редактирования
                max_tokens=800
            )

            content = self._clean_content(content)
            logger.info(f"Post edited successfully with {model_name}: {len(content)} chars")

            return content

        except Exception as e:
            logger.error(f"Error editing post with primary AI: {e}")

            # Runtime fallback на YandexGPT
            try:
                logger.warning("Trying YandexGPT as fallback for editing...")
                fallback_client = YandexGPTClient()

                content = await fallback_client.generate_response(
                    system_prompt=get_system_prompt(),
                    user_message=prompt,
                    temperature=0.6,
                    max_tokens=800
                )

                content = self._clean_content(content)
                logger.info(f"YandexGPT fallback successful for editing: {len(content)} chars")
                return content

            except Exception as fallback_error:
                logger.error(f"YandexGPT fallback also failed: {fallback_error}")
                raise

    def _get_topic_for_post_type(self, post_type: str) -> str:
        """
        Возвращает тему для типа поста (V2 — для логирования).

        Args:
            post_type: Тип поста

        Returns:
            str: Описание типа поста
        """
        # V2: Просто возвращаем название типа из POST_TYPES
        if post_type in POST_TYPES:
            return POST_TYPES[post_type]["name"]
        return post_type

    def _convert_markdown_to_html(self, content: str) -> str:
        """
        Конвертирует markdown-форматирование в Telegram HTML.

        Преобразования:
        - **bold** → <b>bold</b>
        - *italic* → <i>italic</i>  (но не ** которое bold)
        - __underline__ → <u>underline</u>
        - ~~strike~~ → <s>strike</s>
        - `code` → <code>code</code>

        Args:
            content: Текст с возможным markdown

        Returns:
            str: Текст с HTML-тегами
        """
        # Bold: **text** → <b>text</b>
        content = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', content, flags=re.DOTALL)

        # Italic: *text* → <i>text</i> (но не ** которое bold)
        # Используем negative lookbehind/lookahead чтобы не затронуть уже преобразованное
        content = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', content)

        # Underline: __text__ → <u>text</u>
        content = re.sub(r'__(.+?)__', r'<u>\1</u>', content, flags=re.DOTALL)

        # Strikethrough: ~~text~~ → <s>text</s>
        content = re.sub(r'~~(.+?)~~', r'<s>\1</s>', content, flags=re.DOTALL)

        # Inline code: `text` → <code>text</code>
        content = re.sub(r'`([^`]+)`', r'<code>\1</code>', content)

        return content

    def _clean_content(self, content: str) -> str:
        """
        Очищает сгенерированный контент от артефактов

        Args:
            content: Сырой контент от AI

        Returns:
            str: Очищенный контент
        """
        # Убираем возможные обрамления
        content = content.strip()

        # Убираем маркеры кода если есть
        if content.startswith("```"):
            lines = content.split("\n")
            if len(lines) > 2:
                content = "\n".join(lines[1:-1])

        # Убираем кавычки в начале и конце
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]

        # ВАЖНО: Конвертируем markdown в HTML
        content = self._convert_markdown_to_html(content)

        # Убираем лишние переносы строк
        while "\n\n\n" in content:
            content = content.replace("\n\n\n", "\n\n")

        return content.strip()

    # V2: _apply_post_processing и _count_emojis убраны — персоны не используются

    @staticmethod
    def get_available_post_types() -> dict:
        """
        Возвращает доступные типы постов (V2)

        Returns:
            dict: {type_code: description}
        """
        # V2: Типы из prompts_v2
        return {
            post_type: config["name"]
            for post_type, config in POST_TYPES.items()
        }

    @staticmethod
    def get_premium_post_types() -> list:
        """
        V2: Premium типы убраны — все посты генерируются одинаково.
        Метод оставлен для совместимости.

        Returns:
            list: пустой список
        """
        return []

    # === Методы для работы с сериями ===

    async def generate_series_post(
        self,
        series_id: Optional[int] = None,
        create_new: bool = False,
        series_title: Optional[str] = None,
        series_topic: Optional[str] = None,
        character: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Tuple[str, str, dict]:
        """
        Генерирует пост как часть серии (с cliffhanger).

        Args:
            series_id: ID существующей серии (если None — ищем активную или создаём новую)
            create_new: Создать новую серию даже если есть активная
            series_title: Название новой серии
            series_topic: Тема новой серии
            character: Персонаж серии (recurring character)
            temperature: Креативность

        Returns:
            Tuple[str, str, dict]: (текст поста, промпт, метаданные серии)
        """
        try:
            series = None

            # 1. Если указан ID — используем эту серию
            if series_id:
                context = await self.series_manager.get_series_context(series_id)
                if not context:
                    raise ValueError(f"Серия {series_id} не найдена")
                series_id = context["series_id"]

            # 2. Если не указан ID и не создаём новую — ищем активную
            elif not create_new:
                active_series = await self.series_manager.get_active_series()
                if active_series:
                    series_id = active_series.id
                    context = await self.series_manager.get_series_context(series_id)

            # 3. Если нет активной серии или нужна новая — создаём
            if not series_id or create_new:
                new_series = await self.series_manager.create_series(
                    title=series_title,
                    topic=series_topic,
                    character=character
                )
                await self.series_manager.start_series(new_series.id)
                series_id = new_series.id
                context = await self.series_manager.get_series_context(series_id)

            # 4. Определяем тип поста
            post_type = context.get("post_type", "series_intro")

            # 5. Генерируем пост с контекстом серии
            series_prompt_addition = self.series_manager.build_series_prompt_addition(context)

            # Используем обычный generate_post с дополнением промпта
            content, prompt = await self.generate_post(
                post_type=post_type,
                custom_topic=series_prompt_addition,
                temperature=temperature or 0.85
            )

            # 6. Извлекаем cliffhanger из контента (если есть)
            cliffhanger = self._extract_cliffhanger(content)

            # 7. Возвращаем метаданные для последующего advance_series
            metadata = {
                "series_id": series_id,
                "post_type": post_type,
                "part": context.get("current_part", 1),
                "total_parts": context.get("total_parts", 3),
                "character": context.get("character"),
                "cliffhanger": cliffhanger,
                "is_finale": context.get("is_finale", False)
            }

            logger.info(f"[SERIES] Сгенерирован пост серии: {post_type} (часть {metadata['part']}/{metadata['total_parts']})")

            return content, prompt, metadata

        except Exception as e:
            logger.error(f"[SERIES] Ошибка генерации поста серии: {e}")
            raise

    def _extract_cliffhanger(self, content: str) -> Optional[str]:
        """
        Извлекает cliffhanger из сгенерированного поста.

        Args:
            content: Текст поста

        Returns:
            str или None
        """
        import re

        # Ищем типичные паттерны cliffhanger в конце поста
        patterns = [
            r"продолжение[\s—–-]*завтра[.!?…]*",
            r"что.*дальше\?",
            r"завтра расскаж[уе]",
            r"но это.*не всё",
            r"а вот что.*случилось",
            r"to be continued",
        ]

        last_lines = content.split("\n")[-5:]  # Последние 5 строк
        last_text = " ".join(last_lines).lower()

        for pattern in patterns:
            match = re.search(pattern, last_text, re.IGNORECASE)
            if match:
                # Возвращаем последнее предложение как cliffhanger
                sentences = re.split(r'[.!?]', content)
                if sentences:
                    return sentences[-2].strip() if len(sentences) > 1 else sentences[-1].strip()

        return None

    async def complete_series_post(
        self,
        series_id: int,
        post_id: int,
        cliffhanger: Optional[str] = None,
        context_summary: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Завершает часть серии после публикации поста.

        Args:
            series_id: ID серии
            post_id: ID опубликованного поста
            cliffhanger: Cliffhanger для следующей части
            context_summary: Краткое описание что произошло в этой части

        Returns:
            Tuple[bool, str]: (серия завершена?, тип следующего поста или "completed")
        """
        try:
            series, next_type = await self.series_manager.advance_series(
                series_id=series_id,
                post_id=post_id,
                cliffhanger=cliffhanger,
                context_update=context_summary
            )

            is_complete = next_type == "completed"

            if is_complete:
                logger.info(f"[SERIES] Серия {series_id} завершена!")
            else:
                logger.info(f"[SERIES] Следующий пост серии: {next_type}")

            return is_complete, next_type

        except Exception as e:
            logger.error(f"[SERIES] Ошибка завершения части серии: {e}")
            raise

    async def get_active_series_info(self) -> Optional[dict]:
        """
        Получает информацию об активной серии.

        Returns:
            dict с информацией о серии или None
        """
        active = await self.series_manager.get_active_series()
        if not active:
            return None

        return {
            "id": active.id,
            "title": active.title,
            "topic": active.topic,
            "character": active.character,
            "current_part": active.current_part,
            "total_parts": active.total_parts,
            "status": active.status,
            "next_post_type": active.next_post_type()
        }

    # === V2: Персоны убраны — один стиль ===
    # Методы get_available_personas, get_persona_info, get_current_mood,
    # trigger_mood_change, generate_new_mood — удалены в V2

    # === Методы для работы с изображениями ===

    def is_image_generation_available(self) -> bool:
        """Проверяет, доступен ли поиск фото продуктов"""
        # Всегда доступен — используем базу готовых фото
        return True

    def get_testimonial_photo(
        self,
        category: str = "before_after",
        subcategory: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Получает фото из базы testimonials (до/после, чеки и т.д.)

        Args:
            category: Категория testimonials ("before_after", "checks", "products", "success_stories")
            subcategory: Подкатегория (например "weight_loss", "collagen")

        Returns:
            Tuple[Optional[str], Optional[str], Optional[str]]:
                (base64 изображения, путь к файлу, описание)
        """
        import base64
        from pathlib import Path

        try:
            # Маппинг строк на enum
            category_map = {
                "before_after": TestimonialCategory.BEFORE_AFTER,
                "checks": TestimonialCategory.CHECKS,
                "products": TestimonialCategory.PRODUCTS,
                "success_stories": TestimonialCategory.SUCCESS_STORIES
            }
            cat_enum = category_map.get(category, TestimonialCategory.BEFORE_AFTER)

            # Получаем testimonial
            if subcategory:
                testimonials = self.testimonials_manager.get_by_subcategory(
                    cat_enum, subcategory, count=1, with_photos_only=True
                )
            else:
                testimonials = self.testimonials_manager.get_random(
                    cat_enum, count=1, with_photos_only=True
                )

            if not testimonials:
                logger.info(f"[TESTIMONIALS] Нет фото в категории {category}/{subcategory}")
                return None, None, None

            testimonial = testimonials[0]

            # Получаем файлы с абсолютными путями
            media_files = self.testimonials_manager.get_media_files(testimonial)
            if not media_files:
                return None, None, None

            # Берём первый существующий файл
            for file_info in media_files:
                if file_info.get('exists') and file_info.get('type') == 'photo':
                    photo_path = Path(file_info['path'])
                    with open(photo_path, 'rb') as f:
                        image_base64 = base64.b64encode(f.read()).decode('utf-8')

                    # Формируем описание
                    author = testimonial.get('from', 'Партнёр NL')
                    topic = testimonial.get('topic', category)
                    description = f"Testimonial: {topic} от {author}"

                    logger.info(f"[TESTIMONIALS] ✅ Найдено фото: {photo_path.name}")
                    return image_base64, str(photo_path), description

            return None, None, None

        except Exception as e:
            logger.error(f"[TESTIMONIALS] Ошибка получения фото: {e}")
            return None, None, None

    async def generate_image(
        self,
        post_type: str,
        post_content: str,
        custom_prompt: Optional[str] = None,
        style: Optional[str] = None,
        use_product_reference: bool = True
    ) -> Tuple[Optional[str], str]:
        """
        Генерирует изображение для поста.

        ПРИОРИТЕТ:
        1. Для success_story/transformation → фото до/после из testimonials
        2. Готовое фото из unified_products/ (если это пост о продукте)
        3. Для business постов → чеки партнёров из testimonials

        Args:
            post_type: Тип поста
            post_content: Текст поста
            custom_prompt: Пользовательский промпт (опционально)
            style: Визуальный стиль изображения (ImageStyle enum)
            use_product_reference: Использовать готовые фото продуктов

        Returns:
            Tuple[Optional[str], str]: (base64 изображения или путь к файлу, описание)
        """
        try:
            import time
            import base64
            from pathlib import Path

            # === 1. ДЛЯ ПОСТОВ С ИСТОРИЯМИ УСПЕХА → ФОТО ДО/ПОСЛЕ ===
            if post_type in ["success_story", "transformation"]:
                # Определяем подкатегорию по КОНКРЕТНЫМ ключевым словам
                # Используем точные совпадения слов, а не подстроки
                text_lower = post_content.lower()
                subcategory = None

                # Словарь подкатегорий с ТОЧНЫМИ ключевыми словами
                # Приоритет: более специфичные слова проверяются первыми
                subcategory_keywords = {
                    "weight_loss": [
                        "похудел", "похудела", "похудение", "сбросил", "сбросила",
                        "минус кг", "килограмм", " кг ", "energy diet", "ed smart",
                        "3d slim", "стройност", "лишний вес", "снизил вес"
                    ],
                    "collagen": [
                        "коллаген", "collagen", "морщин", "упругость кожи",
                        "эластичность", "подтянул лицо", "подтянула лицо"
                    ],
                    "drain_effect": [
                        "драйн", "draineffect", "drain effect", "отёк", "отек",
                        "отечност", "мешки под глазами", "припухлост"
                    ],
                    "hair": [
                        "волосы", "выпадение волос", "рост волос", "укрепление волос"
                    ],
                    "cellulite": [
                        "целлюлит", "апельсиновая корка"
                    ],
                    "adaptogens": [
                        "адаптоген", "стресс", "нервы", "сон", "энергия", "бодрость"
                    ],
                    "detox": [
                        "детокс", "очищение", "вывод токсинов"
                    ],
                }

                # Считаем совпадения для каждой подкатегории
                matches = {}
                for subcat, keywords in subcategory_keywords.items():
                    count = sum(1 for kw in keywords if kw in text_lower)
                    if count > 0:
                        matches[subcat] = count

                # Выбираем подкатегорию с максимальным числом совпадений
                if matches:
                    subcategory = max(matches, key=matches.get)
                    logger.info(f"[ФОТО] Определена подкатегория: {subcategory} (совпадений: {matches})")
                else:
                    # Если ничего не найдено — берём weight_loss как самую большую категорию
                    subcategory = "weight_loss"
                    logger.info(f"[ФОТО] Подкатегория не определена, используем default: {subcategory}")

                image_base64, photo_path, description = self.get_testimonial_photo(
                    category="before_after",
                    subcategory=subcategory
                )

                if image_base64:
                    logger.info(f"[ФОТО] ✅ Testimonial до/после для {post_type}: {description}")
                    return image_base64, description

            # === 2. ДЛЯ БИЗНЕС-ПОСТОВ → ЧЕКИ ПАРТНЁРОВ (50% шанс) ===
            if post_type in ["business", "business_lifestyle", "business_myths"]:
                if random.random() < 0.5:  # 50% шанс показать чек
                    image_base64, photo_path, description = self.get_testimonial_photo(
                        category="checks"
                    )

                    if image_base64:
                        logger.info(f"[ФОТО] ✅ Чек партнёра для {post_type}: {description}")
                        return image_base64, description

            # === 3. ФОТО ПРОДУКТОВ (через MediaLibrary) ===
            # Ищем фото для ЛЮБОГО типа поста, если в тексте упоминается продукт
            if use_product_reference:
                start_time = time.time()

                # НОВОЕ: используем индексированный поиск через MediaLibrary
                try:
                    asset = await self.media_library.find_in_text(post_content, asset_type="product")
                    search_time_ms = (time.time() - start_time) * 1000

                    if asset and asset.file_path:
                        photo_path = Path(asset.file_path)

                        if photo_path.exists():
                            with open(photo_path, 'rb') as f:
                                image_base64 = base64.b64encode(f.read()).decode('utf-8')

                            product_name = asset.nl_products[0] if asset.nl_products else "unknown"
                            logger.info(f"[ФОТО] ✅ MediaLibrary: найдено фото {product_name} за {search_time_ms:.1f}ms")
                            return image_base64, f"готовое фото: {product_name} ({photo_path.name})"
                        else:
                            logger.warning(f"[ФОТО] ❌ Файл не существует: {photo_path}")
                    else:
                        logger.info(f"[ФОТО] MediaLibrary: продукт не найден за {search_time_ms:.1f}ms")

                except Exception as e:
                    logger.error(f"[ФОТО] Ошибка MediaLibrary: {e}, fallback на старый метод")

                # FALLBACK: старый метод через ProductReferenceManager
                product_result = self.product_reference.extract_product_from_content(post_content)
                if product_result:
                    keyword, folder_path, photo_path = product_result
                    logger.info(f"[ФОТО] Fallback: найден продукт '{keyword}' → {folder_path}")
                    if photo_path and photo_path.exists():
                        with open(photo_path, 'rb') as f:
                            image_base64 = base64.b64encode(f.read()).decode('utf-8')
                        logger.info(f"[ФОТО] ✅ Fallback: используем фото {photo_path}")
                        return image_base64, f"готовое фото: {keyword} ({photo_path.name})"

            # === 4. FALLBACK: СЛУЧАЙНОЕ ФОТО ИЗ TESTIMONIALS ===
            # Если ничего не найдено — берём случайное фото до/после (для визуала)
            if post_type in ["motivation", "tips"]:
                image_base64, photo_path, description = self.get_testimonial_photo(
                    category="before_after"  # Случайное фото результатов
                )
                if image_base64:
                    logger.info(f"[ФОТО] ✅ Fallback testimonial для {post_type}: {description}")
                    return image_base64, description

            # Фото не найдено — возвращаем None (YandexART удалён)
            logger.info("[ФОТО] Фото не найдено, пост будет без изображения")
            return None, ""

        except Exception as e:
            logger.error(f"Error generating image: {e}")
            return None, ""

    async def regenerate_image(
        self,
        post_type: str,
        post_content: str,
        feedback: Optional[str] = None,
        style: Optional[str] = None
    ) -> Tuple[Optional[str], str]:
        """
        Повторно ищет фото продукта для поста.

        YandexART удалён — просто повторный поиск готового фото.

        Args:
            post_type: Тип поста
            post_content: Текст поста
            feedback: Не используется (оставлен для совместимости)
            style: Не используется (оставлен для совместимости)

        Returns:
            Tuple[Optional[str], str]: (base64 изображения или None, описание)
        """
        return await self.generate_image(post_type, post_content)

    @staticmethod
    def get_available_image_styles() -> dict:
        """
        Возвращает пустой словарь — стили не используются (YandexART удалён)
        Оставлен для совместимости с интерфейсом.
        """
        return {}
