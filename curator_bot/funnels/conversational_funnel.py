"""
Диалоговая воронка для AI-Куратора.

Полностью текстовый режим без кнопок.
Куратор сам определяет когда предложить продукт/бизнес.
Использует паттерны из скриптов продаж.

ВАЖНО: Контекст воронки теперь хранится в БД (не в RAM)!
При перезагрузке бота контекст сохраняется.

ВАЖНО: При SOLUTION и CLOSING этапах — автоматически вставляет реферальные ссылки!
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Импорт реферальных ссылок
from curator_bot.funnels.referral_links import (
    get_product_recommendation,
    get_registration_link,
    get_business_link,
    get_link_for_pain,
    PRODUCT_RECOMMENDATIONS,
)
from shared.database.base import AsyncSessionLocal


class ConversationStage(Enum):
    """Этапы диалоговой воронки"""
    GREETING = "greeting"           # Приветствие, знакомство
    DISCOVERY = "discovery"         # Выявление болей и потребностей
    DEEPENING = "deepening"         # Углубление в проблему
    SOLUTION_HINT = "solution_hint" # Намёк на решение
    SOLUTION = "solution"           # Предложение продукта/бизнеса
    OBJECTION = "objection"         # Работа с возражениями
    CLOSING = "closing"             # Закрытие (CTA)
    FOLLOW_UP = "follow_up"         # Сопровождение


class UserIntent(Enum):
    """Намерение пользователя"""
    PRODUCT = "product"       # Интересуется продуктами
    BUSINESS = "business"     # Интересуется бизнесом
    SKEPTIC = "skeptic"       # Сомневается, скептик
    CURIOUS = "curious"       # Просто любопытен
    SUPPORT = "support"       # Нужна поддержка/помощь
    UNKNOWN = "unknown"       # Не определено


class LeadTemperature(Enum):
    """
    Температура лида — определяет скорость воронки.

    HOT: Знает NL, сам спрашивает про конкретный продукт/бизнес → сразу ссылки
    WARM: Интересуется, но не конкретен → стандартный прогрев (3 сообщения)
    COLD: Скептик, пришёл поспорить → длинный прогрев (5+ сообщений)
    """
    HOT = "hot"      # MIN_MESSAGES = 1
    WARM = "warm"    # MIN_MESSAGES = 3
    COLD = "cold"    # MIN_MESSAGES = 5


@dataclass
class FunnelContext:
    """
    Контекст диалога с пользователем.

    Используется как промежуточное представление между БД и логикой.
    """
    user_id: int
    stage: ConversationStage = ConversationStage.GREETING
    intent: UserIntent = UserIntent.UNKNOWN
    temperature: LeadTemperature = LeadTemperature.WARM  # Температура лида

    # Выявленные боли и потребности
    pains: List[str] = field(default_factory=list)
    needs: List[str] = field(default_factory=list)
    objections: List[str] = field(default_factory=list)

    # Счётчики для определения готовности
    engagement_score: int = 0      # Насколько вовлечён
    trust_score: int = 0           # Насколько доверяет
    objection_count: int = 0       # Сколько возражений
    messages_count: int = 0        # Сколько сообщений обменялись

    # Предложенные решения
    suggested_products: List[str] = field(default_factory=list)
    suggested_business: bool = False

    # Флаг немедленной выдачи ссылки (через промпт)
    link_provided: bool = False

    # Таймстемпы
    last_message_at: Optional[datetime] = None
    conversation_started_at: Optional[datetime] = None


class ConversationalFunnel:
    """
    Диалоговая воронка — ведёт пользователя естественным разговором.

    Принципы:
    1. Сначала слушаем и задаём вопросы
    2. Выявляем боли органично
    3. Не предлагаем решение слишком рано
    4. Персонализируем под контекст

    ВАЖНО: Контекст хранится в БД (таблица conversation_contexts).
    """

    # Минимум сообщений до предложения решения (по температуре лида)
    MIN_MESSAGES_BY_TEMPERATURE = {
        LeadTemperature.HOT: 1,   # Горячий → сразу
        LeadTemperature.WARM: 3,  # Тёплый → стандартный прогрев
        LeadTemperature.COLD: 5,  # Холодный → длинный прогрев
    }

    # Порог доверия для предложения (по температуре)
    TRUST_THRESHOLD_BY_TEMPERATURE = {
        LeadTemperature.HOT: 0,   # Горячий → не ждём доверия
        LeadTemperature.WARM: 2,  # Тёплый → базовое доверие
        LeadTemperature.COLD: 4,  # Холодный → высокое доверие
    }

    # Маркеры ГОРЯЧЕГО лида (знает NL, конкретный запрос)
    HOT_LEAD_MARKERS = [
        "nl international", "nl store", "nlstore", "энерджи диет", "energy diet",
        "ed smart", "greenflash", "грин флеш", "3d slim", "metaboost",
        "draineffect", "где купить", "как заказать", "хочу заказать",
        "сколько стоит", "дайте ссылку", "скинь ссылку", "как зарегистрироваться",
        "хочу стать партнёром", "как стать партнёром", "nl партнёр"
    ]

    # Маркеры для определения intent
    PRODUCT_MARKERS = [
        "устал", "энергия", "похудеть", "здоровье", "витамины", "кожа",
        "волосы", "сон", "иммунитет", "детокс", "спорт", "фитнес",
        "болит", "проблема", "хочу", "нужно", "посоветуй", "что лучше"
    ]

    BUSINESS_MARKERS = [
        "заработать", "дополнительный доход", "удалённо", "из дома",
        "бизнес", "подработка", "пассивный доход", "команда", "сетевой",
        "партнёр", "сколько можно заработать", "как начать"
    ]

    SKEPTIC_MARKERS = [
        "развод", "пирамида", "не верю", "обман", "дорого", "не работает",
        "млм", "сетевой маркетинг", "зачем", "почему", "бесполезно",
        "втюхивают", "навязывают", "секта"
    ]

    PAIN_MARKERS = {
        "energy": ["устаю", "нет сил", "энергии", "разбитый", "вялый", "сонный"],
        "weight": ["похудеть", "лишний вес", "жир", "живот", "фигура", "диета"],
        "skin": ["кожа", "прыщи", "морщины", "сухая", "проблемная", "возраст"],
        "immunity": ["болею", "простуда", "иммунитет", "слабый", "витамины"],
        "sleep": ["сон", "бессонница", "не высыпаюсь", "ночью", "утром тяжело"],
        "sport": ["спорт", "тренировки", "мышцы", "восстановление", "протеин"],
        "kids": ["ребёнок", "дети", "детский", "для детей", "малыш"],
        "money": ["заработок", "деньги", "доход", "финансы", "кредит", "ипотека",
                  "заработать", "удалённо", "подработка", "бизнес", "партнёр", "как начать"]
    }

    # Паттерны вопросов для углубления
    DEEPENING_QUESTIONS = {
        "energy": [
            "Давно тебя это беспокоит?",
            "А что обычно делаешь чтобы взбодриться?",
            "Утром тяжело или к вечеру накрывает?"
        ],
        "weight": [
            "Что уже пробовала?",
            "Какая цель — сколько хочешь сбросить?",
            "Диеты пробовала? Как результаты?"
        ],
        "money": [
            "Сколько времени готов уделять?",
            "Есть опыт в продажах или команде?",
            "Какой доход был бы комфортным для старта?"
        ]
    }

    # Переходные фразы к решению
    SOLUTION_HINTS = {
        "energy": "Знаешь, я сам через это прошёл. И нашёл один лайфхак...",
        "weight": "Понимаю. У меня многие клиенты с такой же историей. Есть один подход который реально работает...",
        "skin": "Слушай, у меня подруга с похожей проблемой была. Она нашла решение — расскажу?",
        "money": "Интересно. Я как раз работаю в NL International — это компания с 25-летней историей, свой завод. Можно стартовать бесплатно и расти постепенно...",
        "business": "Слушай, я понимаю. Сам искал удалённую работу. Нашёл систему где платят за результат, не за время. Расскажу?"
    }

    def __init__(self):
        """Инициализация"""
        logger.info("ConversationalFunnel initialized (DB-backed)")

    async def get_context(self, user_id: int) -> FunnelContext:
        """
        Получает контекст из БД или создаёт новый.

        Args:
            user_id: Telegram ID пользователя

        Returns:
            FunnelContext с данными из БД
        """
        from curator_bot.database.models import User, ConversationContext

        async with AsyncSessionLocal() as session:
            # Ищем пользователя
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                # Пользователь не найден — возвращаем пустой контекст
                logger.warning(f"User {user_id} not found, returning empty context")
                return FunnelContext(user_id=user_id)

            # Ищем контекст
            ctx_result = await session.execute(
                select(ConversationContext).where(ConversationContext.user_id == user.id)
            )
            db_ctx = ctx_result.scalar_one_or_none()

            if not db_ctx:
                # Создаём новый контекст
                db_ctx = ConversationContext(
                    user_id=user.id,
                    funnel_stage="greeting",
                    funnel_intent="unknown",
                    pains=[],
                    needs=[],
                    objections=[],
                    engagement_score=0,
                    trust_score=0,
                    objection_count=0,
                    messages_count=0,
                    suggested_products=[],
                    suggested_business=False,
                    link_provided=False,
                    conversation_started_at=datetime.now()
                )
                session.add(db_ctx)
                await session.commit()
                await session.refresh(db_ctx)
                logger.info(f"Created new funnel context for user {user_id}")

            # Конвертируем в FunnelContext
            return FunnelContext(
                user_id=user_id,
                stage=ConversationStage(db_ctx.funnel_stage or "greeting"),
                intent=UserIntent(db_ctx.funnel_intent or "unknown"),
                temperature=LeadTemperature(db_ctx.lead_temperature or "warm"),
                pains=db_ctx.pains or [],
                needs=db_ctx.needs or [],
                objections=db_ctx.objections or [],
                engagement_score=db_ctx.engagement_score or 0,
                trust_score=db_ctx.trust_score or 0,
                objection_count=db_ctx.objection_count or 0,
                messages_count=db_ctx.messages_count or 0,
                suggested_products=db_ctx.suggested_products or [],
                suggested_business=db_ctx.suggested_business or False,
                link_provided=db_ctx.link_provided or False,
                conversation_started_at=db_ctx.conversation_started_at,
                last_message_at=db_ctx.last_funnel_activity
            )

    async def save_context(self, ctx: FunnelContext):
        """
        Сохраняет контекст в БД.

        Args:
            ctx: FunnelContext для сохранения
        """
        from curator_bot.database.models import User, ConversationContext

        async with AsyncSessionLocal() as session:
            # Ищем пользователя
            result = await session.execute(
                select(User).where(User.telegram_id == ctx.user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"Cannot save context: user {ctx.user_id} not found")
                return

            # Ищем или создаём контекст
            ctx_result = await session.execute(
                select(ConversationContext).where(ConversationContext.user_id == user.id)
            )
            db_ctx = ctx_result.scalar_one_or_none()

            if not db_ctx:
                db_ctx = ConversationContext(user_id=user.id)
                session.add(db_ctx)

            # Обновляем поля
            db_ctx.funnel_stage = ctx.stage.value
            db_ctx.funnel_intent = ctx.intent.value
            db_ctx.lead_temperature = ctx.temperature.value
            db_ctx.pains = ctx.pains
            db_ctx.needs = ctx.needs
            db_ctx.objections = ctx.objections
            db_ctx.engagement_score = ctx.engagement_score
            db_ctx.trust_score = ctx.trust_score
            db_ctx.objection_count = ctx.objection_count
            db_ctx.messages_count = ctx.messages_count
            db_ctx.suggested_products = ctx.suggested_products
            db_ctx.suggested_business = ctx.suggested_business
            db_ctx.link_provided = ctx.link_provided
            db_ctx.conversation_started_at = ctx.conversation_started_at
            db_ctx.last_funnel_activity = datetime.now()

            await session.commit()
            logger.debug(f"Saved funnel context for user {ctx.user_id}")

    async def analyze_message(self, user_id: int, message: str) -> Dict[str, Any]:
        """
        Анализирует сообщение и обновляет контекст.

        Returns:
            Dict с рекомендациями для AI:
            - stage: текущий этап
            - intent: намерение пользователя
            - pains: выявленные боли
            - should_offer: готов ли к предложению
            - question_to_ask: вопрос для углубления
            - solution_hint: подводка к решению
        """
        ctx = await self.get_context(user_id)
        message_lower = message.lower()

        # Обновляем счётчики
        ctx.messages_count += 1
        ctx.last_message_at = datetime.now()

        # Определяем intent если ещё не определён
        if ctx.intent == UserIntent.UNKNOWN:
            ctx.intent = self._detect_intent(message_lower)

        # Определяем температуру лида (на первом сообщении, потом не пересматриваем)
        if ctx.messages_count == 1:
            ctx.temperature = self._detect_lead_temperature(message_lower, ctx.intent)
            logger.info(f"Lead temperature for {user_id}: {ctx.temperature.value}")

        # Выявляем боли
        detected_pains = self._detect_pains(message_lower)
        for pain in detected_pains:
            if pain not in ctx.pains:
                ctx.pains.append(pain)

        # Определяем возражения
        if self._is_objection(message_lower):
            ctx.objection_count += 1
            objection = self._extract_objection(message_lower)
            if objection and objection not in ctx.objections:
                ctx.objections.append(objection)

        # Обновляем engagement/trust
        ctx.engagement_score += self._calc_engagement_delta(message)
        ctx.trust_score += self._calc_trust_delta(message)

        # Определяем этап воронки
        ctx.stage = self._determine_stage(ctx)

        # Сохраняем контекст в БД
        await self.save_context(ctx)

        # Формируем рекомендации для AI
        result = {
            "stage": ctx.stage.value,
            "intent": ctx.intent.value,
            "temperature": ctx.temperature.value,  # HOT/WARM/COLD
            "pains": ctx.pains,
            "objections": ctx.objections,
            "messages_count": ctx.messages_count,
            "engagement": ctx.engagement_score,
            "trust": ctx.trust_score,
            "should_offer": self._should_offer_solution(ctx),
            "question_to_ask": None,
            "solution_hint": None,
            "objection_response": None
        }

        # Добавляем рекомендации по этапу
        if ctx.stage == ConversationStage.DISCOVERY and ctx.pains:
            # Задаём углубляющий вопрос
            pain = ctx.pains[-1]
            questions = self.DEEPENING_QUESTIONS.get(pain, [])
            if questions:
                import random
                result["question_to_ask"] = random.choice(questions)

        elif ctx.stage == ConversationStage.SOLUTION_HINT and ctx.pains:
            # Готовим подводку к решению
            pain = ctx.pains[0]
            result["solution_hint"] = self.SOLUTION_HINTS.get(pain)

        elif ctx.stage == ConversationStage.OBJECTION and ctx.objections:
            # Нужно отработать возражение
            result["objection_response"] = self._get_objection_script(ctx.objections[-1])

        logger.info(f"Conversation analysis for {user_id}: stage={ctx.stage.value}, intent={ctx.intent.value}")
        return result

    def _detect_intent(self, message: str) -> UserIntent:
        """Определяет намерение по сообщению"""
        if any(word in message for word in self.SKEPTIC_MARKERS):
            return UserIntent.SKEPTIC
        if any(word in message for word in self.BUSINESS_MARKERS):
            return UserIntent.BUSINESS
        if any(word in message for word in self.PRODUCT_MARKERS):
            return UserIntent.PRODUCT
        return UserIntent.CURIOUS

    def _detect_lead_temperature(self, message: str, intent: UserIntent) -> LeadTemperature:
        """
        Определяет температуру лида.

        HOT: Знает NL, спрашивает конкретный продукт/бизнес, хочет ссылку
        WARM: Интересуется темой, но без конкретики
        COLD: Скептик, пришёл поспорить

        Args:
            message: Текст сообщения (lowercase)
            intent: Определённое намерение

        Returns:
            LeadTemperature
        """
        # Скептик → холодный
        if intent == UserIntent.SKEPTIC:
            return LeadTemperature.COLD

        # Проверяем маркеры горячего лида
        if any(marker in message for marker in self.HOT_LEAD_MARKERS):
            logger.info(f"Detected HOT lead by markers")
            return LeadTemperature.HOT

        # Конкретные вопросы про цену/заказ → горячий
        hot_patterns = [
            "сколько стоит", "какая цена", "где купить", "как заказать",
            "хочу попробовать", "хочу заказать", "давай попробую"
        ]
        if any(pattern in message for pattern in hot_patterns):
            logger.info(f"Detected HOT lead by price/order question")
            return LeadTemperature.HOT

        # По умолчанию — тёплый
        return LeadTemperature.WARM

    def _detect_pains(self, message: str) -> List[str]:
        """Определяет боли из сообщения"""
        pains = []
        for pain_type, markers in self.PAIN_MARKERS.items():
            if any(word in message for word in markers):
                pains.append(pain_type)
        return pains

    def _is_objection(self, message: str) -> bool:
        """Проверяет, содержит ли сообщение возражение"""
        objection_markers = [
            "дорого", "не верю", "не работает", "развод", "пирамида",
            "нет времени", "подумаю", "не знаю", "сомневаюсь", "не уверен"
        ]
        return any(word in message for word in objection_markers)

    def _extract_objection(self, message: str) -> Optional[str]:
        """Извлекает тип возражения"""
        if any(word in message for word in ["дорого", "цена", "стоит"]):
            return "price"
        if any(word in message for word in ["не верю", "развод", "пирамида", "обман"]):
            return "trust"
        if any(word in message for word in ["нет времени", "занят"]):
            return "time"
        if any(word in message for word in ["подумаю", "потом"]):
            return "delay"
        return None

    def _calc_engagement_delta(self, message: str) -> int:
        """Считает изменение вовлечённости"""
        score = 0
        # Длинные сообщения = больше вовлечённости
        if len(message) > 100:
            score += 2
        elif len(message) > 50:
            score += 1
        # Вопросы = интерес
        if "?" in message:
            score += 1
        # Эмодзи = эмоциональная включённость
        if any(c for c in message if ord(c) > 127000):
            score += 1
        return score

    def _calc_trust_delta(self, message: str) -> int:
        """Считает изменение доверия"""
        score = 0
        message_lower = message.lower()

        # Позитивные маркеры
        if any(word in message_lower for word in ["спасибо", "интересно", "расскажи", "хочу"]):
            score += 1
        # Негативные маркеры
        if any(word in message_lower for word in ["не верю", "развод", "обман"]):
            score -= 1
        return score

    def _determine_stage(self, ctx: FunnelContext) -> ConversationStage:
        """
        Определяет текущий этап воронки.

        Использует пороги по температуре лида:
        - HOT: сразу к SOLUTION (1 сообщение)
        - WARM: стандартный прогрев (3 сообщения)
        - COLD: длинный прогрев (5 сообщений)
        """
        min_messages = self.MIN_MESSAGES_BY_TEMPERATURE.get(ctx.temperature, 3)

        if ctx.messages_count <= 1:
            # Горячий лид → сразу к SOLUTION если есть боль
            if ctx.temperature == LeadTemperature.HOT and ctx.pains:
                return ConversationStage.SOLUTION
            return ConversationStage.GREETING

        if ctx.objection_count > 0 and ctx.objections:
            return ConversationStage.OBJECTION

        if not ctx.pains:
            return ConversationStage.DISCOVERY

        if ctx.messages_count < min_messages:
            return ConversationStage.DEEPENING

        if self._should_offer_solution(ctx):
            if ctx.suggested_products or ctx.suggested_business:
                return ConversationStage.CLOSING
            return ConversationStage.SOLUTION

        return ConversationStage.SOLUTION_HINT

    def _should_offer_solution(self, ctx: FunnelContext) -> bool:
        """
        Определяет, готов ли пользователь к предложению через воронку.

        Использует пороги по температуре лида:
        - HOT: сразу предлагаем (без ожидания доверия)
        - WARM: стандартные пороги
        - COLD: повышенные пороги

        Учитывает: была ли уже дана ссылка через промпт (немедленная выдача).
        Если ссылка уже дана AI, воронка не дублирует предложение.
        """
        # Если ссылка уже дана AI, воронка не дублирует
        if ctx.link_provided:
            return False

        # Пороги по температуре
        min_messages = self.MIN_MESSAGES_BY_TEMPERATURE.get(ctx.temperature, 3)
        trust_threshold = self.TRUST_THRESHOLD_BY_TEMPERATURE.get(ctx.temperature, 2)

        # Нужно минимум сообщений (зависит от температуры)
        if ctx.messages_count < min_messages:
            return False

        # Нужен минимальный уровень доверия (зависит от температуры)
        if ctx.trust_score < trust_threshold:
            return False

        # Должны быть выявлены боли
        if not ctx.pains:
            return False

        # Не предлагаем если много возражений (для холодных — строже)
        max_objections = 2 if ctx.temperature == LeadTemperature.COLD else 3
        if ctx.objection_count >= max_objections:
            return False

        return True

    async def mark_link_provided(self, user_id: int):
        """
        Помечает что пользователю уже дана ссылка (чтобы воронка не дублировала).

        Вызывается когда AI дал ссылку через промпт (немедленная выдача).
        """
        ctx = await self.get_context(user_id)
        ctx.link_provided = True
        await self.save_context(ctx)
        logger.info(f"Marked link_provided=True for user {user_id}")

    async def has_link_been_provided(self, user_id: int) -> bool:
        """
        Проверяет давалась ли уже ссылка пользователю.
        """
        ctx = await self.get_context(user_id)
        return ctx.link_provided

    def _get_objection_script(self, objection_type: str) -> str:
        """Возвращает скрипт для отработки возражения с реальными ценами"""
        scripts = {
            "price": (
                "Понимаю. Давай посчитаем: ED Smart стоит 2 790₽ за 15 порций — это 186₽ за одну. "
                "Меньше чашки кофе в кафе! А держит сытость 3-4 часа. Выгоднее обычной еды."
            ),
            "trust": (
                "Слушай, я сам так думал сначала. Компании NL 25 лет, свой завод в Новосибирске, "
                "продукты сертифицированы. Не призываю верить словам — попробуй один продукт и посмотри."
            ),
            "time": (
                "На самом деле это занимает 5 минут в день. "
                "Размешал порошок — выпил. Проще чем завтрак готовить!"
            ),
            "delay": (
                "Конечно, подумай. Только вот что: пока думаем — время идёт, проблема остаётся. "
                "Может, попробуешь просто один продукт для эксперимента?"
            )
        }
        return scripts.get(objection_type, "")

    async def get_ai_instructions(self, user_id: int, message: str) -> str:
        """
        Генерирует инструкции для AI на основе контекста.

        Вставляется в промпт перед генерацией ответа.
        """
        analysis = await self.analyze_message(user_id, message)
        ctx = await self.get_context(user_id)

        # Описание температуры лида
        temp_descriptions = {
            "hot": "🔥 ГОРЯЧИЙ (знает NL, хочет ссылку → давай СРАЗУ!)",
            "warm": "🌤️ ТЁПЛЫЙ (интересуется → стандартный прогрев)",
            "cold": "❄️ ХОЛОДНЫЙ (скептик → длинный прогрев, сначала доверие)",
        }
        temp_desc = temp_descriptions.get(analysis['temperature'], "🌤️ ТЁПЛЫЙ")

        instructions = f"""
=== ДИАЛОГОВАЯ ВОРОНКА ===

ТЕКУЩИЙ ЭТАП: {analysis['stage']}
ТЕМПЕРАТУРА ЛИДА: {temp_desc}
НАМЕРЕНИЕ ПОЛЬЗОВАТЕЛЯ: {analysis['intent']}
ВЫЯВЛЕННЫЕ БОЛИ: {', '.join(analysis['pains']) or 'ещё не выявлены'}
СООБЩЕНИЙ В ДИАЛОГЕ: {analysis['messages_count']}
УРОВЕНЬ ДОВЕРИЯ: {analysis['trust']}/5

"""

        # Специальные инструкции по температуре
        if analysis['temperature'] == 'hot':
            instructions += """
⚡ ГОРЯЧИЙ ЛИД — ДЕЙСТВУЙ БЫСТРО!
Этот человек УЖЕ знает что хочет. Не тяни — давай ссылку СРАЗУ!
Не нужно 10 вопросов, не нужно "выявлять боли" — он сам сказал.
"""
        elif analysis['temperature'] == 'cold':
            instructions += """
❄️ ХОЛОДНЫЙ ЛИД — ТЕРПЕНИЕ!
Скептик пришёл поспорить. НЕ давай ссылки пока не заработаешь доверие.
Сначала выслушай, признай его сомнения, покажи экспертизу.
Только когда доверие есть — можно предлагать.
"""

        # Инструкции по этапу
        if analysis['stage'] == 'greeting':
            if analysis['temperature'] == 'hot':
                instructions += """
ТВОЯ ЗАДАЧА НА ЭТОМ ЭТАПЕ:
- Поприветствуй коротко
- Уточни что именно нужно (какой продукт? какая цель?)
- СРАЗУ давай информацию и ссылку
"""
            else:
                instructions += """
ТВОЯ ЗАДАЧА НА ЭТОМ ЭТАПЕ:
- Поприветствуй тепло и неформально
- Спроси как дела / что привело
- НЕ предлагай ничего, только слушай
"""

        elif analysis['stage'] == 'discovery':
            instructions += """
ТВОЯ ЗАДАЧА НА ЭТОМ ЭТАПЕ:
- Задавай открытые вопросы
- Выявляй боли и потребности
- Показывай что понимаешь
- НЕ спеши с решением
"""
            if analysis.get('question_to_ask'):
                instructions += f"\nМОЖЕШЬ СПРОСИТЬ: \"{analysis['question_to_ask']}\"\n"

        elif analysis['stage'] == 'deepening':
            instructions += """
ТВОЯ ЗАДАЧА НА ЭТОМ ЭТАПЕ:
- Углубляйся в проблему
- Проявляй эмпатию
- Дели личным опытом если уместно
- Готовь почву для решения
"""

        elif analysis['stage'] == 'solution_hint':
            instructions += """
ТВОЯ ЗАДАЧА НА ЭТОМ ЭТАПЕ:
- Плавно подводи к решению
- Не впаривай — заинтересовывай
- Расскажи свою историю / историю клиента
"""
            if analysis.get('solution_hint'):
                instructions += f"\nИСПОЛЬЗУЙ ПОДВОДКУ: \"{analysis['solution_hint']}\"\n"

        elif analysis['stage'] == 'solution':
            # Разные инструкции для продуктов и бизнеса
            if analysis['intent'] == 'business':
                # Бизнес-интент: предлагаем партнёрство
                reg_link = get_registration_link()
                business_link = get_business_link()
                instructions += f"""
ТВОЯ ЗАДАЧА НА ЭТОМ ЭТАПЕ:
- ТЕПЕРЬ можно предложить бизнес!
- Клиент хочет: заработать / дополнительный доход / удалённую работу

💼 ПРЕДЛОЖЕНИЕ ПАРТНЁРСТВА:
- Регистрация БЕСПЛАТНАЯ, без обязательств
- Ссылка на регистрацию: {reg_link}
- Подробнее о бизнесе: {business_link}

ПЛАН ВОЗНАГРАЖДЕНИЯ (расскажи кратко):
- M1 (750 PV) — от 1 300 ₽/мес
- M2 (1 500 PV) — от 5 000 ₽/мес
- M3 (3 000 PV) — от 25 000 ₽/мес
- И выше (B1, B2, B3, TOP)

ЧТО ПОЛУЧАЕТ СРАЗУ:
- Партнёрские цены (на 20-25% ниже)
- Личный кабинет
- Бесплатное обучение
- Реферальную ссылку для заработка

ВАЖНО:
- Не дави — предлагай
- Объясни что старт бесплатный
- Ссылка на регистрацию: {reg_link}
"""
            else:
                # Продуктовый интент: предлагаем продукт
                pain_point = analysis['pains'][0] if analysis['pains'] else 'weight'
                product_rec = get_product_recommendation(pain_point)
                product_link = get_link_for_pain(pain_point)

                instructions += f"""
ТВОЯ ЗАДАЧА НА ЭТОМ ЭТАПЕ:
- ТЕПЕРЬ можно предложить решение!
- Боль клиента: {analysis['pains']}

🎯 РЕКОМЕНДУЕМЫЙ ПРОДУКТ:
Название: {product_rec['name']}
Цена: {product_rec['price']} ₽ за {product_rec.get('portions', 1)} порций ({product_rec.get('price_per_portion', product_rec['price'])}₽ за одну)
Ссылка на заказ: {product_rec['link']}

ВКУСНАЯ ПРЕЗЕНТАЦИЯ (используй этот стиль):
{product_rec['tasty_description']}

ВАЖНО:
- Покажи конкретный ВКУС (не "коктейль", а "Шоколадный брауни")
- Объясни КАК это поможет ИМЕННО ЕМУ
- В конце дай ССЫЛКУ на заказ: {product_link}
- НЕ говори "скидка" — у нас фиксированные цены
"""

        elif analysis['stage'] == 'objection':
            instructions += """
ТВОЯ ЗАДАЧА НА ЭТОМ ЭТАПЕ:
- Отработай возражение мягко
- Не спорь, а понимай
- Приведи факт или историю
- Предложи попробовать без обязательств
"""
            if analysis.get('objection_response'):
                instructions += f"\nСКРИПТ: {analysis['objection_response']}\n"

        elif analysis['stage'] == 'closing':
            # Ссылки для CTA
            pain_point = analysis['pains'][0] if analysis['pains'] else 'weight'
            product_link = get_link_for_pain(pain_point)
            reg_link = get_registration_link()
            business_link = get_business_link()

            instructions += f"""
ТВОЯ ЗАДАЧА НА ЭТОМ ЭТАПЕ:
- Подведи к действию!
- Сними последние сомнения
- Дай КОНКРЕТНЫЙ CTA

🛒 ССЫЛКИ ДЛЯ CTA:
"""
            if analysis['intent'] == 'business':
                instructions += f"""
- "Готов попробовать? Регистрация бесплатная": {reg_link}
- Подробнее о бизнесе: {business_link}
"""
            else:
                instructions += f"""
- "Попробуй и сам увидишь результат": {product_link}
- Если решит стать партнёром: {reg_link}
"""
            instructions += """
ВАЖНО: Дай только ОДНУ ссылку — не перегружай!
"""

        instructions += """
=== КОНЕЦ ИНСТРУКЦИЙ ===

ВАЖНО: Веди диалог ЕСТЕСТВЕННО. Не перескакивай этапы!
"""

        return instructions

    async def reset_context(self, user_id: int):
        """Сбрасывает контекст пользователя"""
        from curator_bot.database.models import User, ConversationContext

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()

            if user:
                ctx_result = await session.execute(
                    select(ConversationContext).where(ConversationContext.user_id == user.id)
                )
                db_ctx = ctx_result.scalar_one_or_none()

                if db_ctx:
                    await session.delete(db_ctx)
                    await session.commit()
                    logger.info(f"Reset conversation context for user {user_id}")


# Глобальный экземпляр воронки
_funnel_instance: Optional[ConversationalFunnel] = None


def get_conversational_funnel() -> ConversationalFunnel:
    """Получает глобальный экземпляр воронки"""
    global _funnel_instance
    if _funnel_instance is None:
        _funnel_instance = ConversationalFunnel()
    return _funnel_instance
