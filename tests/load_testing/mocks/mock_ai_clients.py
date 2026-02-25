"""
Mock AI Clients для нагрузочного тестирования

Smart Mock с:
- Intent detection (анализ сообщений)
- Персонализация ответов
- Эмуляция задержки API
- Сбор метрик
"""

import asyncio
import random
from typing import List, Dict, Optional, Any


# Шаблоны ответов для AI-Куратора
CURATOR_RESPONSE_TEMPLATES = {
    "greeting": [
        "Привет! Рад знакомству! Чем могу помочь?",
        "Здорово! Давай знакомиться. Что тебя интересует?",
        "Привет! Я твой AI-куратор. С чего начнём?",
        "Хей! Слушай, давай по-честному: что привело тебя сюда?",
    ],
    "product": [
        "Понял! Интересуешься продуктами NL. Давай разберёмся что внутри...",
        "Окей, продукты. Честно? Я сам сначала не верил, но состав реально классный.",
        "Слушай, по продуктам у нас реально крутая линейка. Что конкретно интересует?",
        "Energy Diet, коллаген, витамины... Что хочешь узнать?",
    ],
    "business": [
        "Бизнес с NL — это не про «быстрые деньги». Готов работать?",
        "Окей, про заработок. Сколько готов уделять времени в неделю?",
        "Честно? Первые месяцы будет сложно. Но потом система работает сама.",
        "Слушай, бизнес тут реально работает. Но нужно системно подходить.",
    ],
    "skeptic": [
        "Понимаю твои сомнения. Я сам думал «пирамида» в начале. Давай разберём.",
        "Окей, ты не веришь. Нормально. Что конкретно смущает?",
        "Слушай, скептицизм — это здраво. Задавай вопросы, разберём всё по полочкам.",
        "Честно? Многие так думают сначала. Потом изучают документы и меняют мнение.",
    ],
    "curious": [
        "Хороший вопрос! Давай подробнее разберём.",
        "Окей, интересная тема. Что конкретно хочешь узнать?",
        "Понял тебя. Слушай, тут много нюансов. С чего начнём?",
        "Отличный вопрос! Честно, многие об этом не задумываются.",
    ],
    "goal": [
        "Супер, что ставишь цели! Какая главная задача на ближайший месяц?",
        "Окей, цель — это важно. Давай распишем конкретный план.",
        "Классно! Цель есть — половина успеха. Теперь разберём как её достичь.",
        "Отлично! Хорошая цель мотивирует. Что нужно для её достижения?",
    ],
    "support": [
        "Всё ок? Бывают сложности, это нормально. Расскажи что случилось.",
        "Понимаю, иногда бывает tough. Давай разберём как решить.",
        "Слушай, не переживай. Вместе найдём решение. В чём проблема?",
        "Окей, слушаю. Расскажи подробнее, чем могу помочь.",
    ],
}


# Шаблоны ответов для Контент-Менеджера
CONTENT_MANAGER_RESPONSE_TEMPLATES = {
    "product": [
        "Energy Diet Smart — это 200 ккал полноценного питания.\n\n✅ 15г белка\n✅ 12 витаминов\n✅ Вкусно и удобно\n\nПопробуй — не пожалеешь!",
        "Greenflash Collagen — это красота изнутри.\n\n✨ Упругая кожа\n✨ Крепкие ногти\n✨ Здоровые суставы\n\nРеальный результат за 30 дней!",
        "VLED — система для быстрого результата.\n\n🔥 -5 кг за месяц\n🔥 Простая схема\n🔥 Без срывов\n\nГотов попробовать?",
    ],
    "motivation": [
        "Твой успех начинается с первого шага.\n\nНе жди понедельника. Начни сегодня! 💪",
        "Маленькие шаги каждый день = большие результаты через месяц.\n\nКак твой прогресс?",
        "Честно? Первый месяц — самый сложный. Зато потом видишь результат и уже не остановишься!",
    ],
    "news": [
        "Новость недели: NL запустила новую линейку спортивного питания!\n\n🏋️‍♂️ Протеин\n🏋️‍♂️ BCAA\n🏋️‍♂️ Витамины\n\nВсё для твоих результатов!",
        "Важно: NL получила международную сертификацию качества ISO 22000!\n\n✅ Высшие стандарты\n✅ Безопасность\n✅ Качество\n\nГордимся!",
    ],
    "tips": [
        "Совет дня: начинай утро со стакана воды.\n\n💧 Запускает метаболизм\n💧 Даёт энергию\n💧 Улучшает кожу\n\nПростой шаг — большой эффект!",
        "Секрет стройности: 80% питание, 20% тренировки.\n\nПравильное питание — основа твоего результата!",
    ],
    "success_story": [
        "История Марии: -12 кг за 3 месяца!\n\n«Я не верила что у меня получится. Но Energy Diet + поддержка куратора = вот мой результат!»\n\n💪 Результат реален для каждого!",
        "История Игоря: с M1 до M3 за полгода!\n\n«Бросил офис, начал с NL. Сейчас команда 50 человек и доход 200к/мес. Лучшее решение в жизни!»",
    ],
}


class MockAnthropicClient:
    """
    Эмулирует Claude Sonnet 3.5 без реальных API вызовов

    Features:
    - Smart Intent Detection
    - Персонализированные ответы
    - Эмуляция задержки API (500ms по умолчанию)
    - Метрики calls/latency
    """

    def __init__(
        self,
        response_templates: Dict[str, List[str]] = None,
        latency_ms: int = 500,
        latency_variance_ms: int = 200
    ):
        self.response_templates = response_templates or CURATOR_RESPONSE_TEMPLATES
        self.latency_ms = latency_ms
        self.latency_variance_ms = latency_variance_ms

        # Метрики
        self.calls_count = 0
        self.total_latency_ms = 0
        self.intent_distribution = {}

    def _detect_intent(self, user_message: str) -> str:
        """Определяет intent пользователя по ключевым словам"""
        message_lower = user_message.lower()

        # Приветствие
        if any(word in message_lower for word in ["привет", "здравствуй", "hi", "hello", "хай", "старт", "/start"]):
            return "greeting"

        # Продукты
        if any(word in message_lower for word in [
            "продукт", "купить", "заказать", "energy diet", "коллаген", "greenflash",
            "витамин", "протеин", "vled", "коктейль", "похудеть", "сбросить вес"
        ]):
            return "product"

        # Бизнес
        if any(word in message_lower for word in [
            "заработать", "бизнес", "доход", "деньги", "сколько можно",
            "маркетинг", "команда", "партнёр", "квалификация", "m1", "b1"
        ]):
            return "business"

        # Скептик
        if any(word in message_lower for word in [
            "пирамида", "развод", "не верю", "обман", "мошенн", "сомнева"
        ]):
            return "skeptic"

        # Цели
        if any(word in message_lower for word in [
            "цель", "goal", "хочу", "планирую", "мечта"
        ]):
            return "goal"

        # Поддержка
        if any(word in message_lower for word in [
            "проблем", "не получается", "сложно", "трудно", "помоги"
        ]):
            return "support"

        # По умолчанию — curious
        return "curious"

    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Генерирует ответ на основе user message"""

        # Эмулируем задержку API (с вариативностью)
        actual_latency = self.latency_ms + random.randint(
            -self.latency_variance_ms, self.latency_variance_ms
        )
        actual_latency = max(100, actual_latency)  # Минимум 100ms
        await asyncio.sleep(actual_latency / 1000)

        # Обновляем метрики
        self.calls_count += 1
        self.total_latency_ms += actual_latency

        # Определяем intent
        intent = self._detect_intent(user_message)

        # Обновляем распределение intents
        self.intent_distribution[intent] = self.intent_distribution.get(intent, 0) + 1

        # Выбираем случайный ответ из шаблонов
        templates = self.response_templates.get(intent, self.response_templates.get("curious", []))

        if not templates:
            return "Интересный вопрос! Расскажи подробнее."

        response = random.choice(templates)

        # Персонализируем ответ (подставляем фрагмент сообщения)
        if "{user_message}" in response:
            user_snippet = user_message[:50]
            response = response.replace("{user_message}", user_snippet)

        return response

    async def generate_with_rag(
        self,
        system_prompt: str,
        user_message: str,
        knowledge_fragments: List[str],
        context: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Генерирует ответ с использованием RAG контекста"""

        # Аналогично generate_response, но добавляем RAG контекст
        actual_latency = self.latency_ms + random.randint(
            -self.latency_variance_ms, self.latency_variance_ms
        )
        actual_latency = max(100, actual_latency)
        await asyncio.sleep(actual_latency / 1000)

        self.calls_count += 1
        self.total_latency_ms += actual_latency

        intent = self._detect_intent(user_message)
        self.intent_distribution[intent] = self.intent_distribution.get(intent, 0) + 1

        templates = self.response_templates.get(intent, self.response_templates.get("curious", []))
        response = random.choice(templates) if templates else "Интересный вопрос!"

        # Добавляем фрагмент из RAG (если есть)
        if knowledge_fragments:
            rag_snippet = knowledge_fragments[0][:100]
            response += f"\n\n(Из базы знаний: {rag_snippet}...)"

        return response

    def get_metrics(self) -> Dict[str, Any]:
        """Возвращает метрики Mock AI"""
        return {
            "calls_count": self.calls_count,
            "avg_latency_ms": self.total_latency_ms / self.calls_count if self.calls_count > 0 else 0,
            "total_latency_ms": self.total_latency_ms,
            "intent_distribution": self.intent_distribution,
        }

    def reset_metrics(self):
        """Сбрасывает метрики"""
        self.calls_count = 0
        self.total_latency_ms = 0
        self.intent_distribution = {}


class MockYandexGPTClient:
    """
    Резервный Mock для YandexGPT (на случай fallback)

    Аналогичная реализация, но с другими шаблонами ответов
    """

    def __init__(
        self,
        response_templates: Dict[str, List[str]] = None,
        latency_ms: int = 600,  # YandexGPT медленнее
        latency_variance_ms: int = 300
    ):
        self.response_templates = response_templates or CURATOR_RESPONSE_TEMPLATES
        self.latency_ms = latency_ms
        self.latency_variance_ms = latency_variance_ms

        self.calls_count = 0
        self.total_latency_ms = 0

    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Генерирует ответ (упрощённая версия)"""

        actual_latency = self.latency_ms + random.randint(
            -self.latency_variance_ms, self.latency_variance_ms
        )
        actual_latency = max(100, actual_latency)
        await asyncio.sleep(actual_latency / 1000)

        self.calls_count += 1
        self.total_latency_ms += actual_latency

        # Простой выбор ответа
        all_templates = []
        for templates in self.response_templates.values():
            all_templates.extend(templates)

        return random.choice(all_templates) if all_templates else "Понял вас."

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "calls_count": self.calls_count,
            "avg_latency_ms": self.total_latency_ms / self.calls_count if self.calls_count > 0 else 0,
        }


class MockContentGenerator:
    """
    Mock для генерации контента (Content Manager)

    Используется для тестирования AI-Контент-Менеджера
    """

    def __init__(
        self,
        post_templates: Dict[str, List[str]] = None,
        latency_ms: int = 800,  # Генерация контента медленнее
        latency_variance_ms: int = 300
    ):
        self.post_templates = post_templates or CONTENT_MANAGER_RESPONSE_TEMPLATES
        self.latency_ms = latency_ms
        self.latency_variance_ms = latency_variance_ms

        self.generations_count = 0
        self.total_latency_ms = 0
        self.post_type_distribution = {}

    async def generate_content(
        self,
        post_type: str,
        mood: Optional[Dict] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Генерирует пост заданного типа"""

        # Эмулируем задержку генерации
        actual_latency = self.latency_ms + random.randint(
            -self.latency_variance_ms, self.latency_variance_ms
        )
        actual_latency = max(200, actual_latency)
        await asyncio.sleep(actual_latency / 1000)

        self.generations_count += 1
        self.total_latency_ms += actual_latency

        # Обновляем распределение по типам
        self.post_type_distribution[post_type] = self.post_type_distribution.get(post_type, 0) + 1

        # Выбираем шаблон
        templates = self.post_templates.get(post_type, ["Пост на тему: {post_type}"])
        text = random.choice(templates)

        # Добавляем hook (если есть mood)
        if mood and mood.get("hook"):
            text = f"{mood['hook']}\n\n{text}"

        return {
            "text": text,
            "image_description": f"Image for {post_type} post",
            "image_style": "realistic",
            "post_type": post_type,
        }

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "generations_count": self.generations_count,
            "avg_latency_ms": self.total_latency_ms / self.generations_count if self.generations_count > 0 else 0,
            "post_type_distribution": self.post_type_distribution,
        }
