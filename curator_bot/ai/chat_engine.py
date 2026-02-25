"""
Основной AI движок для Куратора с интегрированной системой персон.
Интегрирована диалоговая воронка для естественного ведения разговора.
"""
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

from shared.persona import PersonaManager, PERSONA_CHARACTERISTICS
from shared.persona.hook_templates import HOOK_TEMPLATES
from shared.ai_clients.yandexgpt_client import YandexGPTClient
from curator_bot.ai.prompts import get_curator_system_prompt, get_rag_instruction, get_onboarding_context, SIGNATURE_PHRASES
from curator_bot.ai.segment_styles import extract_segment_from_source, should_filter_swear
from curator_bot.database.models import User, ConversationMessage
from curator_bot.funnels.conversational_funnel import get_conversational_funnel, ConversationalFunnel


class CuratorChatEngine:
    """
    Движок для генерации ответов куратора с использованием AI и RAG.
    Интегрирована система персон для адаптации стиля общения.
    Интегрирована диалоговая воронка для естественного ведения разговора.
    """

    def __init__(self, ai_client):
        """
        Инициализация движка

        Args:
            ai_client: Клиент для работы с AI (Gemini или OpenAI)
        """
        self.ai_client = ai_client

        # Система персон для адаптации стиля
        self.persona_manager = PersonaManager()
        self.use_persona_system = True  # ВКЛЮЧЕНО - адаптация стиля под настроение клиента

        # Диалоговая воронка для естественного ведения разговора
        self.conversational_funnel = get_conversational_funnel()
        self.use_conversational_mode = True  # Включить диалоговый режим

        logger.info("Curator chat engine initialized with PersonaManager and ConversationalFunnel")

    async def generate_response(
        self,
        user: User,
        user_message: str,
        conversation_history: List[ConversationMessage],
        knowledge_fragments: Optional[List[str]] = None,
        max_history: int = 10,
        use_persona: bool = True
    ) -> str:
        """
        Генерирует ответ куратора

        Args:
            user: Объект пользователя
            user_message: Сообщение от пользователя
            conversation_history: История диалога
            knowledge_fragments: Релевантные фрагменты из базы знаний
            max_history: Максимальное количество сообщений из истории
            use_persona: Использовать систему персон для адаптации стиля

        Returns:
            str: Ответ куратора
        """
        try:
            # Определяем сегмент из источника трафика
            user_segment = extract_segment_from_source(
                getattr(user, "traffic_source", None)
            )

            # Получаем системный промпт (с учётом сегмента)
            system_prompt = get_curator_system_prompt(
                user_name=user.first_name or "Партнер",
                qualification=user.qualification,
                lessons_completed=user.lessons_completed,
                current_goal=user.current_goal,
                segment=user_segment,
            )

            # Определяем температуру по умолчанию
            temperature = 0.7

            # Добавляем инструкции диалоговой воронки (теперь асинхронно, БД-backed)
            if self.use_conversational_mode:
                funnel_instructions = await self.conversational_funnel.get_ai_instructions(
                    user_id=user.telegram_id,
                    message=user_message
                )
                system_prompt = system_prompt + "\n\n" + funnel_instructions
                logger.info(f"Added conversational funnel instructions for user {user.telegram_id}")

            # Добавляем контекст онбординга (если активен)
            onboarding_context = await self._get_onboarding_context(user.telegram_id)
            if onboarding_context:
                system_prompt = system_prompt + "\n\n" + onboarding_context
                logger.info(f"Added onboarding context for user {user.telegram_id}")

            # Добавляем контекст дневника (только для админов)
            if user.telegram_id in settings.admin_ids_list:
                diary_context = await self._get_diary_context()
                if diary_context:
                    system_prompt = system_prompt + "\n\n" + diary_context
                    logger.info(f"Added diary context for admin {user.telegram_id}")

            # Добавляем контекст персоны если включена система
            if use_persona and self.use_persona_system:
                # Анализируем настроение сообщения пользователя и адаптируем персону
                persona_context = self._get_adaptive_persona(user_message)

                if persona_context:
                    # Добавляем информацию о персоне в промпт
                    persona_enhancement = self.persona_manager.get_prompt_enhancement(persona_context)
                    system_prompt = system_prompt + "\n\n" + persona_enhancement

                    # Добавляем примеры hooks для этой персоны
                    hook_examples = self._get_hook_examples(persona_context.persona_name)
                    if hook_examples:
                        system_prompt = system_prompt + "\n\n" + hook_examples

                    # Используем температуру персоны
                    temperature = persona_context.temperature

                    logger.info(
                        f"Using persona {persona_context.persona_name} for user {user.telegram_id}"
                    )

            # Формируем контекст из истории диалога
            context = self._prepare_context(conversation_history, max_history)

            # Генерируем ответ
            if knowledge_fragments:
                # Используем RAG если есть фрагменты базы знаний
                logger.info(f"Generating RAG response for user {user.telegram_id}")
                response = await self.ai_client.generate_with_rag(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    knowledge_fragments=knowledge_fragments,
                    context=context,
                    temperature=temperature
                )
            else:
                # Обычный ответ без базы знаний
                logger.info(f"Generating standard response for user {user.telegram_id}")
                response = await self.ai_client.generate_response(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    context=context,
                    temperature=temperature
                )

            # POST-PROCESSING: убираем markdown, эмодзи, AI-слова, обрезаем
            response = self._clean_curator_response(response)

            # Фильтр мата для mama-сегмента
            if user_segment and should_filter_swear(user_segment):
                response = self._filter_swear_words(response)

            # Валидация (логирование, не блокировка)
            self._validate_response(response)

            logger.info(f"Response generated successfully for user {user.telegram_id}")
            return response

        except Exception as e:
            logger.error(f"Error generating response with primary AI: {e}")

            # Runtime fallback на YandexGPT
            try:
                logger.warning("Trying YandexGPT as fallback...")
                fallback_client = YandexGPTClient()

                if knowledge_fragments:
                    response = await fallback_client.generate_with_rag(
                        system_prompt=system_prompt,
                        user_message=user_message,
                        knowledge_fragments=knowledge_fragments,
                        context=context,
                        temperature=temperature
                    )
                else:
                    response = await fallback_client.generate_response(
                        system_prompt=system_prompt,
                        user_message=user_message,
                        context=context,
                        temperature=temperature
                    )

                response = self._clean_curator_response(response)
                self._validate_response(response)
                logger.info(f"YandexGPT fallback successful for user {user.telegram_id}")
                return response

            except Exception as fallback_error:
                logger.error(f"YandexGPT fallback also failed: {fallback_error}")
                return self._get_fallback_response()

    def _clean_curator_response(self, response: str) -> str:
        """
        Очищает ответ куратора от markdown, эмодзи и лишнего.

        V3: Агрессивная чистка — ноль эмодзи, замена AI-слов, обрезка длины.
        """
        import re
        from curator_bot.ai.curator_style import replace_ai_words

        # 1. Убираем заголовки markdown (# ## ### ####)
        response = re.sub(r'^#{1,4}\s+(.+)$', r'\1', response, flags=re.MULTILINE)

        # 2. Убираем **жирный** → жирный
        response = re.sub(r'\*\*([^*]+)\*\*', r'\1', response)

        # 3. Убираем *курсив* → курсив
        response = re.sub(r'\*([^*]+)\*', r'\1', response)

        # 4. Убираем ВСЕ эмодзи (железное правило — ноль)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # смайлы
            "\U0001F300-\U0001F5FF"  # символы и пиктограммы
            "\U0001F680-\U0001F6FF"  # транспорт
            "\U0001F1E0-\U0001F1FF"  # флаги
            "\U00002702-\U000027B0"  # разное
            "\U000024C2-\U0001F251"  # enclosed
            "\U0001F900-\U0001F9FF"  # supplemental
            "\U0001FA00-\U0001FA6F"  # chess
            "\U0001FA70-\U0001FAFF"  # symbols extended
            "\U00002600-\U000026FF"  # misc symbols
            "\U0000FE00-\U0000FE0F"  # variation selectors
            "\U0000200D"             # zero width joiner
            "\U00000023\U0000FE0F\U000020E3"  # keycap
            "\U0000002A\U0000FE0F\U000020E3"
            "\U00000030-\U00000039\U0000FE0F\U000020E3"
            "]+",
            flags=re.UNICODE
        )
        response = emoji_pattern.sub('', response)

        # 5. Убираем списки с тире/буллетами в начале строк
        response = re.sub(r'^[-•]\s+', '', response, flags=re.MULTILINE)

        # 6. Убираем нумерованные списки (1. 2. 3.)
        response = re.sub(r'^\d+\.\s+', '', response, flags=re.MULTILINE)

        # 7. Убираем лишние пустые строки (больше 2 подряд)
        response = re.sub(r'\n{3,}', '\n\n', response)

        # 8. Убираем заголовки типа "Что важно:", "Как действовать:"
        response = re.sub(r'^[А-Яа-яA-Za-z\s]+:\s*$', '', response, flags=re.MULTILINE)

        # 9. Заменяем AI-слова на живые аналоги
        response = replace_ai_words(response)

        # 10. Обрезка длины: максимум 500 символов
        response = response.strip()
        if len(response) > 500:
            # Ищем последнюю точку или вопросительный знак в пределах 500 символов
            cut_pos = max(
                response.rfind('.', 0, 500),
                response.rfind('?', 0, 500),
                response.rfind('!', 0, 500),
            )
            if cut_pos > 100:  # Нашли разумное место для обрезки
                response = response[:cut_pos + 1]
            else:
                response = response[:500]

        # 11. Убираем двойные пробелы (после замен AI-слов)
        response = re.sub(r'  +', ' ', response)

        return response.strip()

    @staticmethod
    def _filter_swear_words(text: str) -> str:
        """Замена мата на мягкие аналоги (для mama-сегмента)."""
        import re
        replacements = {
            "блять": "блин", "бля": "блин", "бл*н": "блин",
            "пиздец": "ужас", "ппц": "кошмар", "пздц": "кошмар",
            "нахуй": "нафиг", "нахуя": "зачем", "хуй": "фиг",
            "хуйня": "ерунда", "хуйню": "ерунду",
            "сука": "жесть", "ёбаный": "жуткий", "ебаный": "жуткий",
            "ёб": "блин", "еб": "блин",
            "пизд": "фиг", "залуп": "фиг",
        }
        for swear, replacement in replacements.items():
            text = re.sub(re.escape(swear), replacement, text, flags=re.IGNORECASE)
        return text

    def _validate_response(self, response: str) -> None:
        """
        Валидация ответа — логирует проблемы (не блокирует).
        Аналог validate_post() из content manager.
        """
        from content_manager_bot.ai.style_dna import check_anti_ai_words

        ai_words = check_anti_ai_words(response)
        if ai_words:
            logger.warning(f"AI words in curator response (post-cleanup): {ai_words}")

    def _get_hook_examples(self, persona_name: str) -> str:
        """
        Возвращает примеры hooks для конкретной персоны.

        Args:
            persona_name: Название персоны (expert, friend, rebel и т.д.)

        Returns:
            str: Примеры hooks для промпта
        """
        import random

        hooks = HOOK_TEMPLATES.get(persona_name, [])
        if not hooks:
            return ""

        # Берём 5-7 случайных hooks как примеры
        sample_size = min(7, len(hooks))
        sampled_hooks = random.sample(hooks, sample_size)

        hook_examples = """
═══════════════════════════════════════════
🎣 ПРИМЕРЫ HOOKS ДЛЯ ТВОЕГО СТИЛЯ
═══════════════════════════════════════════

Используй эти фразы чтобы начать ответ цепляюще:

"""
        for hook in sampled_hooks:
            template = hook["template"]
            # Заменяем переменные на примеры
            if "{topic}" in template:
                template = template.replace("{topic}", "коллаген")
            if "{product}" in template:
                template = template.replace("{product}", "ED Smart")
            if "{myth}" in template:
                template = template.replace("{myth}", "'все БАДы одинаковые'")
            if "{percentage}" in template:
                template = template.replace("{percentage}", "80")

            hook_examples += f"• {template}\n"

        hook_examples += "\n⚡ ВАЖНО: Hooks используй ЕСТЕСТВЕННО, когда они уместны!"

        return hook_examples

    def _get_adaptive_persona(self, user_message: str):
        """
        Выбирает персону на основе контекста сообщения пользователя.

        Адаптирует стиль ответа под:
        - Эмоциональное состояние пользователя
        - Тип вопроса
        - Контекст разговора

        Args:
            user_message: Сообщение пользователя

        Returns:
            PersonaContext или None
        """
        message_lower = user_message.lower()

        # Определяем контекст по ключевым словам
        # Пользователь расстроен/устал -> tired или friend
        sad_keywords = ["устал", "не получается", "сложно", "трудно", "бросить", "не могу", "тяжело", "плохо"]
        if any(word in message_lower for word in sad_keywords):
            self.persona_manager.generate_mood(force_category="sadness", force_intensity="medium")
            return self.persona_manager.get_persona_context(post_type="personal")

        # Пользователь задаёт вопросы о продуктах -> expert
        product_keywords = ["продукт", "состав", "как принимать", "дозировка", "витамин", "коллаген", "energy diet"]
        if any(word in message_lower for word in product_keywords):
            self.persona_manager.generate_mood(force_category="interest", force_intensity="medium")
            return self.persona_manager.get_persona_context(post_type="product")

        # Пользователь скептик или сомневается -> expert или rebel
        skeptic_keywords = ["развод", "пирамида", "не верю", "зачем", "смысл", "почему так дорого", "обман"]
        if any(word in message_lower for word in skeptic_keywords):
            self.persona_manager.generate_mood(force_category="anger", force_intensity="light")
            return self.persona_manager.get_persona_context(post_type="myth_busting")

        # Пользователь радуется/делится успехом -> friend или crazy
        happy_keywords = ["получилось", "ура", "круто", "супер", "спасибо", "вау", "класс", "результат"]
        if any(word in message_lower for word in happy_keywords):
            self.persona_manager.generate_mood(force_category="joy", force_intensity="strong")
            return self.persona_manager.get_persona_context(post_type="celebration")

        # Пользователь спрашивает о бизнесе -> expert или friend
        business_keywords = ["заработать", "бизнес", "команда", "партнёр", "квалификация", "бонус", "доход"]
        if any(word in message_lower for word in business_keywords):
            self.persona_manager.generate_mood(force_category="trust", force_intensity="medium")
            return self.persona_manager.get_persona_context(post_type="business")

        # По умолчанию - дружелюбный стиль
        self.persona_manager.generate_mood(force_category="trust", force_intensity="light")
        return self.persona_manager.get_persona_context(post_type="tips")

    def _prepare_context(
        self,
        messages: List[ConversationMessage],
        max_messages: int
    ) -> List[Dict[str, str]]:
        """
        Подготавливает контекст из истории сообщений

        Args:
            messages: Список сообщений
            max_messages: Максимальное количество сообщений

        Returns:
            List[Dict]: Контекст в формате [{"role": "user", "content": "..."}]
        """
        # Берем последние N сообщений
        recent_messages = sorted(messages, key=lambda x: x.timestamp)[-max_messages:]

        context = []
        for msg in recent_messages:
            context.append({
                "role": "user" if msg.sender == "user" else "assistant",
                "content": msg.message_text
            })

        return context

    def _get_fallback_response(self) -> str:
        """Возвращает запасной ответ при ошибке"""
        return """Бля, у меня тут технические проблемы. Попробуй через пару минут или напиши руководителю."""

    async def analyze_user_intent(self, user_message: str) -> Dict[str, any]:
        """
        Анализирует намерение пользователя

        Args:
            user_message: Сообщение пользователя

        Returns:
            Dict: Информация о намерении (type, category, urgency)
        """
        # Простая категоризация на основе ключевых слов
        message_lower = user_message.lower()

        intent = {
            "type": "general",
            "category": "other",
            "urgency": "normal",
            "keywords": []
        }

        # Определяем категорию вопроса
        # PRODUCTS - продукты NL International
        product_keywords = [
            "продукт", "energy diet", "коктейль", "крем", "витамин",
            "коллаген", "collagen", "бад", "адаптоген", "slim", "похуден",
            "косметик", "уход за кож", "сыворотк", "маск", "шампун",
            "гель", "лосьон", "тоник", "пилинг", "скраб", "капсул",
            "спрей", "напиток", "батончик", "чай", "кофе",
            # 3D Slim продукты:
            "metaboost", "метабуст", "метабуст", "жиросжигат", "l-карнитин", "карнитин",
            "draineffect", "дрейн", "дрейнэффект", "детокс", "дренаж", "отеки", "лишняя вода",
            "white tea", "белый чай", "вайт ти", "аппетит", "тяга к сладком", "сладкое",
            "антицеллюлит", "целлюлит", "гель hot", "гель cold", "хот", "колд",
            "растяжки", "стрии", "shaping", "шейпинг", "моделирующ", "lifting", "лифтинг",
            "3d slim", "3д слим", "slimdo"
        ]
        if any(word in message_lower for word in product_keywords):
            intent["category"] = "products"
            intent["keywords"].append("products")

        # BUSINESS - маркетинг-план, заработок, партнёрство
        elif any(word in message_lower for word in [
            "заработ", "дохо", "товарообор", "проце", "бону", "квалифик",
            "маркетинг", "план вознаг", "карьер", "менеджер", "директор",
            "реферал", "пригласи", "ссылк", "промокод", "скидк", "регистр"
        ]):
            intent["category"] = "business"
            intent["keywords"].append("marketing_plan")

        # SALES - продажи и работа с возражениями
        elif any(word in message_lower for word in [
            "как продать", "клиент", "возражен", "продаж", "сетевой",
            "пирамид", "развод", "дорого", "не работает", "отказ"
        ]):
            intent["category"] = "sales"
            intent["keywords"].append("sales_scripts")

        # TRAINING - обучение, советы, соцсети
        elif any(word in message_lower for word in [
            "обучен", "урок", "курс", "мастер", "совет", "новичок",
            "начать", "первы шаг", "соцсет", "инстаграм", "telegram",
            "контент", "пост", "сторис", "reels", "видео"
        ]):
            intent["category"] = "training"
            intent["keywords"].append("training")

        # FAQ - заказы, доставка, оплата
        elif any(word in message_lower for word in [
            "заказ", "оформи", "доставк", "оплат", "получи", "посылк",
            "трек", "адрес", "пункт выдач", "почт", "курьер", "стоимость"
        ]):
            intent["category"] = "faq"
            intent["keywords"].append("faq")

        # COMPANY - о компании NL International
        elif any(word in message_lower for word in [
            "о компании", "nl international", "история", "основател",
            "когда создан", "сколько лет", "головной офис", "страны"
        ]):
            intent["category"] = "company"
            intent["keywords"].append("company")

        # TEAM_BUILDING - команда и структура
        elif any(word in message_lower for word in [
            "команд", "партнер", "структур", "лидер", "наставник", "спонсор"
        ]):
            intent["category"] = "team_building"
            intent["keywords"].append("team_building")

        # Определяем срочность
        if any(word in message_lower for word in ["срочно", "быстро", "важно", "помоги", "проблем"]):
            intent["urgency"] = "high"

        logger.debug(f"Intent analysis: {intent}")
        return intent

    def should_use_rag(self, intent: Dict[str, any]) -> bool:
        """
        Определяет, нужно ли использовать базу знаний для ответа

        Args:
            intent: Результат анализа намерения

        Returns:
            bool: True если нужно использовать RAG
        """
        # Используем RAG для всех категорий, связанных с NL International
        rag_categories = [
            "products",      # Продукты
            "business",      # Маркетинг-план, заработок
            "sales",         # Продажи, возражения
            "training",      # Обучение, соцсети
            "faq",           # Заказы, доставка
            "company",       # О компании
            "team_building"  # Команда (может быть в training)
        ]
        return intent["category"] in rag_categories

    async def _get_diary_context(self, limit: int = 3) -> Optional[str]:
        """
        Загружает последние записи дневника для контекста куратора.
        Куратор использует их чтобы «помнить» о событиях из жизни.
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
                    return None

                block = (
                    "═══════════════════════════════════════════\n"
                    "📓 ДНЕВНИК ДАНИЛА (недавние записи)\n"
                    "═══════════════════════════════════════════\n\n"
                    "Используй как контекст — ты «знаешь» это. НЕ цитируй дословно.\n\n"
                )
                for entry_text, created_at in rows:
                    date_str = created_at.strftime("%d.%m")
                    preview = entry_text[:300].replace("\n", " ").strip()
                    if len(entry_text) > 300:
                        preview += "..."
                    block += f"[{date_str}] {preview}\n\n"

                logger.info(f"[DIARY] Loaded {len(rows)} diary entries for curator context")
                return block

        except Exception as e:
            logger.warning(f"[DIARY] Failed to load diary context: {e}")
            return None

    async def _get_onboarding_context(self, telegram_id: int) -> Optional[str]:
        """
        Получает контекст онбординга для пользователя из БД.

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            str: Контекст онбординга или None если онбординг не активен
        """
        try:
            from sqlalchemy import select
            from shared.database.base import AsyncSessionLocal
            from curator_bot.database.models import User, UserOnboardingProgress

            async with AsyncSessionLocal() as session:
                # Получаем пользователя
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = result.scalar_one_or_none()

                if not user:
                    return None

                # Получаем прогресс онбординга
                progress_result = await session.execute(
                    select(UserOnboardingProgress).where(
                        UserOnboardingProgress.user_id == user.id
                    )
                )
                progress = progress_result.scalar_one_or_none()

                if not progress:
                    return None

                # Возвращаем контекст
                return get_onboarding_context(
                    current_day=progress.current_day,
                    completed_tasks=list(progress.completed_tasks or []),
                    is_completed=progress.is_completed
                )

        except Exception as e:
            logger.error(f"Error getting onboarding context: {e}")
            return None
