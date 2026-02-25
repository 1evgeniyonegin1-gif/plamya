"""
Mock Conversational Funnel для нагрузочного тестирования

Упрощённая логика воронки без БД:
- Определение intent по ключевым словам
- Определение temperature (HOT/WARM/COLD)
- Переходы между этапами воронки
- Хранение контекста в памяти
"""

from typing import Dict, Any, Optional
from enum import Enum


class FunnelStage(str, Enum):
    """Этапы воронки"""
    GREETING = "GREETING"
    DISCOVERY = "DISCOVERY"
    DEEPENING = "DEEPENING"
    SOLUTION = "SOLUTION"
    CLOSING = "CLOSING"
    FOLLOW_UP = "FOLLOW_UP"


class Intent(str, Enum):
    """Намерения пользователя"""
    PRODUCT = "PRODUCT"
    BUSINESS = "BUSINESS"
    SKEPTIC = "SKEPTIC"
    CURIOUS = "CURIOUS"
    GOAL_SETTING = "GOAL_SETTING"


class Temperature(str, Enum):
    """Температура лида"""
    HOT = "HOT"  # Готов покупать/регистрироваться
    WARM = "WARM"  # Интересуется, изучает
    COLD = "COLD"  # Скептик, сомневается


class MockConversationalFunnel:
    """
    Упрощённая логика воронки для тестов

    Не использует БД, хранит контекст в памяти
    """

    def __init__(self):
        self.contexts = {}  # user_id -> context
        self.processed_messages = 0

    async def process_message(
        self,
        user_id: int,
        message: str,
        session=None  # Игнорируем БД
    ) -> Dict[str, Any]:
        """
        Обрабатывает сообщение пользователя

        Args:
            user_id: ID пользователя
            message: Текст сообщения
            session: Сессия БД (игнорируется в mock)

        Returns:
            Контекст воронки: stage, intent, temperature
        """
        self.processed_messages += 1

        # Создаём контекст если первое сообщение
        if user_id not in self.contexts:
            self.contexts[user_id] = {
                "stage": FunnelStage.GREETING,
                "intent": Intent.CURIOUS,
                "temperature": Temperature.WARM,
                "messages_count": 0,
                "history": [],
            }

        context = self.contexts[user_id]
        context["messages_count"] += 1
        context["history"].append(message)

        # Определяем intent
        intent = self._detect_intent(message)
        context["intent"] = intent

        # Определяем temperature
        temperature = self._determine_temperature(message, context)
        context["temperature"] = temperature

        # Логика перехода между этапами
        context["stage"] = self._next_stage(context)

        return {
            "stage": context["stage"],
            "intent": context["intent"],
            "temperature": context["temperature"],
            "messages_count": context["messages_count"],
        }

    def _detect_intent(self, message: str) -> Intent:
        """Определяет intent по ключевым словам"""
        message_lower = message.lower()

        # Продукты
        if any(word in message_lower for word in [
            "продукт", "купить", "заказать", "energy diet", "коллаген",
            "похудеть", "вес", "коктейль", "витамин", "протеин"
        ]):
            return Intent.PRODUCT

        # Бизнес
        if any(word in message_lower for word in [
            "заработать", "бизнес", "доход", "деньги", "сколько",
            "маркетинг", "партнёр", "команда", "квалификация"
        ]):
            return Intent.BUSINESS

        # Скептик
        if any(word in message_lower for word in [
            "пирамида", "развод", "обман", "не верю", "сомнева",
            "мошенн", "лохотрон"
        ]):
            return Intent.SKEPTIC

        # Цели
        if any(word in message_lower for word in [
            "цель", "хочу", "планирую", "мечта", "goal"
        ]):
            return Intent.GOAL_SETTING

        return Intent.CURIOUS

    def _determine_temperature(self, message: str, context: Dict) -> Temperature:
        """Определяет температуру лида"""
        message_lower = message.lower()

        # HOT: явное намерение купить/начать
        if any(word in message_lower for word in [
            "хочу купить", "хочу заказать", "хочу начать",
            "готов начать", "где купить", "как заказать",
            "когда начнём", "что делать дальше"
        ]):
            return Temperature.HOT

        # COLD: скептицизм
        if context["intent"] == Intent.SKEPTIC:
            return Temperature.COLD

        if any(word in message_lower for word in [
            "не верю", "не уверен", "сомневаюсь", "не знаю"
        ]):
            return Temperature.COLD

        # WARM: изучает, задаёт вопросы
        return Temperature.WARM

    def _next_stage(self, context: Dict) -> FunnelStage:
        """Определяет следующий этап воронки"""
        current_stage = context["stage"]
        messages_count = context["messages_count"]
        temperature = context["temperature"]

        # Логика переходов (упрощённая)
        transitions = {
            FunnelStage.GREETING: FunnelStage.DISCOVERY,
            FunnelStage.DISCOVERY: FunnelStage.DEEPENING,
            FunnelStage.DEEPENING: FunnelStage.SOLUTION,
            FunnelStage.SOLUTION: FunnelStage.CLOSING,
            FunnelStage.CLOSING: FunnelStage.FOLLOW_UP,
        }

        # Переходим на следующий этап каждые 3 сообщения
        if messages_count % 3 == 0:
            return transitions.get(current_stage, FunnelStage.FOLLOW_UP)

        # Если HOT temperature — быстрый переход к CLOSING
        if temperature == Temperature.HOT and current_stage not in [
            FunnelStage.CLOSING, FunnelStage.FOLLOW_UP
        ]:
            return FunnelStage.SOLUTION

        return current_stage

    def get_context(self, user_id: int) -> Optional[Dict]:
        """Возвращает контекст пользователя"""
        return self.contexts.get(user_id)

    def get_metrics(self) -> Dict:
        """Возвращает метрики воронки"""
        # Подсчитываем распределение по stages
        stage_distribution = {}
        intent_distribution = {}
        temperature_distribution = {}

        for context in self.contexts.values():
            stage = context["stage"]
            intent = context["intent"]
            temperature = context["temperature"]

            stage_distribution[stage] = stage_distribution.get(stage, 0) + 1
            intent_distribution[intent] = intent_distribution.get(intent, 0) + 1
            temperature_distribution[temperature] = temperature_distribution.get(temperature, 0) + 1

        return {
            "processed_messages": self.processed_messages,
            "active_users": len(self.contexts),
            "stage_distribution": stage_distribution,
            "intent_distribution": intent_distribution,
            "temperature_distribution": temperature_distribution,
        }

    def reset_metrics(self):
        """Сбрасывает метрики и контексты"""
        self.contexts = {}
        self.processed_messages = 0
