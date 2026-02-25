"""
User Simulator для нагрузочного тестирования

Эмулирует поведение реальных пользователей:
- Виртуальные пользователи с профилями
- Генерация сообщений на основе intent/segment
- Измерение response time
- Сбор метрик и ошибок
"""

import time
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional
from unittest.mock import MagicMock, AsyncMock


@dataclass
class VirtualUser:
    """
    Виртуальный пользователь для тестирования

    Представляет собой профиль пользователя с определённым поведением
    """

    # Профиль
    user_id: int
    telegram_id: int
    name: str
    age: int
    city: str
    segment: str  # A|B|C|D|E (по типу аудитории)
    intent: str  # business|product|curious|skeptic
    pain_point: str  # weight|energy|immunity|beauty|money
    behavior: str  # active|passive|skeptic

    # Тестовые сценарии
    test_messages: List[str] = field(default_factory=list)
    expected_keywords: List[str] = field(default_factory=list)

    # Метрики
    messages_sent: int = 0
    responses_received: int = 0
    total_response_time_ms: float = 0
    errors: List[str] = field(default_factory=list)

    def generate_test_messages(self) -> List[str]:
        """
        Генерирует сообщения на основе профиля

        Returns:
            Список тестовых сообщений
        """

        # Шаблоны по intent
        message_templates = {
            "business": [
                "Привет! Хочу узнать про бизнес с NL",
                "Сколько можно заработать?",
                "Как начать зарабатывать?",
                "Это правда работает или развод?",
                "А сколько времени нужно?",
                "Какие квалификации есть?",
                "Расскажи про маркетинг-план",
            ],
            "product": [
                "Привет!",
                "Хочу похудеть",
                "Какие продукты есть для снижения веса?",
                "Сколько стоит Energy Diet?",
                "Где можно заказать?",
                "Какой состав у коктейлей?",
                "Есть ли противопоказания?",
            ],
            "curious": [
                "Привет!",
                "Что это за компания такая?",
                "Расскажи подробнее про NL",
                "Не очень понял как это работает",
                "А сколько партнёров уже в России?",
                "Какая история компании?",
            ],
            "skeptic": [
                "Привет",
                "Это не пирамида?",
                "Докажи что это не развод",
                "Почему я должен вам верить?",
                "Покажите документы",
                "А есть ли реальные результаты?",
            ],
        }

        base_messages = message_templates.get(
            self.intent,
            message_templates["curious"]
        )

        # Добавляем специфичные сообщения по pain_point
        pain_messages = {
            "weight": [
                "Хочу сбросить 5-10 кг",
                "Как быстро можно похудеть?",
                "Что эффективнее всего?",
            ],
            "energy": [
                "Постоянно устаю",
                "Нужна энергия на весь день",
                "Что даёт бодрость?",
            ],
            "immunity": [
                "Часто болею",
                "Как укрепить иммунитет?",
                "Что принимать для защиты?",
            ],
            "beauty": [
                "Проблемы с кожей",
                "Хочу выглядеть моложе",
                "Что улучшает состояние волос?",
            ],
            "money": [
                "Нужен дополнительный доход",
                "Сколько реально заработать?",
                "Когда будут первые деньги?",
            ],
        }

        if self.pain_point in pain_messages:
            base_messages.extend(pain_messages[self.pain_point])

        # Ограничиваем количество сообщений (5-10 на пользователя)
        import random
        num_messages = random.randint(5, 10)

        return base_messages[:num_messages]

    async def send_message_to_bot(
        self,
        bot_handler: Callable,
        message_text: str,
        delay_before: float = 0
    ) -> Dict[str, Any]:
        """
        Отправляет сообщение боту и замеряет время ответа

        Args:
            bot_handler: Handler бота (функция обработки сообщений)
            message_text: Текст сообщения
            delay_before: Задержка перед отправкой (сек)

        Returns:
            Результат: success, response, response_time_ms, error
        """

        if delay_before > 0:
            await asyncio.sleep(delay_before)

        start_time = time.time()

        try:
            # Эмулируем Telegram Message объект
            mock_message = MagicMock()
            mock_message.from_user.id = self.telegram_id
            mock_message.from_user.username = f"user_{self.user_id}"
            mock_message.text = message_text
            mock_message.answer = AsyncMock()

            # Вызываем handler
            await bot_handler(mock_message)

            # Получаем ответ из mock
            if mock_message.answer.called:
                response = mock_message.answer.call_args[0][0] if mock_message.answer.call_args else "OK"
            else:
                response = "No response"

            response_time_ms = (time.time() - start_time) * 1000

            self.messages_sent += 1
            self.responses_received += 1
            self.total_response_time_ms += response_time_ms

            return {
                "success": True,
                "response": response,
                "response_time_ms": response_time_ms,
            }

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)

            self.errors.append(error_msg)
            self.messages_sent += 1

            return {
                "success": False,
                "error": error_msg,
                "response_time_ms": response_time_ms,
            }

    def get_metrics(self) -> Dict:
        """Возвращает метрики пользователя"""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "segment": self.segment,
            "intent": self.intent,
            "pain_point": self.pain_point,
            "behavior": self.behavior,
            "messages_sent": self.messages_sent,
            "responses_received": self.responses_received,
            "avg_response_time_ms": (
                self.total_response_time_ms / self.responses_received
                if self.responses_received > 0 else 0
            ),
            "error_rate": (
                len(self.errors) / self.messages_sent
                if self.messages_sent > 0 else 0
            ),
            "errors": self.errors,
        }


@dataclass
class VirtualAdmin:
    """
    Виртуальный админ для тестирования Content Manager

    Генерирует посты разных типов
    """

    admin_id: int
    telegram_id: int
    name: str

    # Типы постов для генерации
    post_types: List[str] = field(default_factory=list)

    # Метрики
    posts_generated: int = 0
    total_generation_time_ms: float = 0
    errors: List[str] = field(default_factory=list)

    async def generate_post(
        self,
        post_type: str,
        generate_callback: Callable
    ) -> Dict[str, Any]:
        """
        Генерирует пост заданного типа

        Args:
            post_type: Тип поста (product, motivation, etc.)
            generate_callback: Callback для генерации

        Returns:
            Результат генерации
        """
        start_time = time.time()

        try:
            result = await generate_callback(
                admin_id=self.telegram_id,
                post_type=post_type
            )

            generation_time_ms = (time.time() - start_time) * 1000

            self.posts_generated += 1
            self.total_generation_time_ms += generation_time_ms

            return {
                "success": True,
                "post_type": post_type,
                "result": result,
                "generation_time_ms": generation_time_ms,
            }

        except Exception as e:
            generation_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)

            self.errors.append(error_msg)

            return {
                "success": False,
                "post_type": post_type,
                "error": error_msg,
                "generation_time_ms": generation_time_ms,
            }

    def get_metrics(self) -> Dict:
        """Возвращает метрики админа"""
        return {
            "admin_id": self.admin_id,
            "name": self.name,
            "posts_generated": self.posts_generated,
            "avg_generation_time_ms": (
                self.total_generation_time_ms / self.posts_generated
                if self.posts_generated > 0 else 0
            ),
            "error_rate": (
                len(self.errors) / self.posts_generated
                if self.posts_generated > 0 else 0
            ),
            "errors": self.errors,
        }
