"""
Клиент для работы с Anthropic Claude API
"""
from typing import List, Dict, Optional
from anthropic import AsyncAnthropic
from loguru import logger

from shared.config.settings import settings


class AnthropicClient:
    """Клиент для работы с Anthropic Claude API"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Инициализация клиента

        Args:
            api_key: API ключ Anthropic (если None - берется из настроек)
            model: Модель для использования (если None - берется из настроек)
        """
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.curator_ai_model

        # Используем прокси если указан (для обхода блокировки с российских IP)
        base_url = settings.anthropic_base_url if settings.anthropic_base_url else None
        if base_url:
            self.client = AsyncAnthropic(api_key=self.api_key, base_url=base_url)
            logger.info(f"Anthropic client initialized with proxy: {base_url}")
        else:
            self.client = AsyncAnthropic(api_key=self.api_key)
        logger.info(f"Anthropic client initialized with model: {self.model}")

    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Генерирует ответ с использованием Claude

        Args:
            system_prompt: Системный промпт
            user_message: Сообщение от пользователя
            context: История диалога [{"role": "user/assistant", "content": "..."}]
            temperature: Креативность ответа (0.0 - 1.0)
            max_tokens: Максимальная длина ответа

        Returns:
            str: Ответ от AI
        """
        try:
            messages = []

            # Добавляем историю диалога
            if context:
                messages.extend(context)

            # Добавляем текущее сообщение
            messages.append({"role": "user", "content": user_message})

            logger.debug(f"Sending request to Claude with {len(messages)} messages")

            # Отправляем запрос
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=messages
            )

            answer = response.content[0].text
            logger.info(f"Response generated successfully (tokens: input={response.usage.input_tokens}, output={response.usage.output_tokens})")

            return answer

        except Exception as e:
            logger.error(f"Error calling Anthropic API: {e}")
            raise

    async def generate_with_rag(
        self,
        system_prompt: str,
        user_message: str,
        knowledge_fragments: List[str],
        context: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500
    ) -> str:
        """
        Генерирует ответ с использованием базы знаний (RAG)

        Args:
            system_prompt: Системный промпт
            user_message: Сообщение от пользователя
            knowledge_fragments: Релевантные фрагменты из базы знаний
            context: История диалога
            temperature: Креативность ответа
            max_tokens: Максимальная длина ответа

        Returns:
            str: Ответ от AI с учетом базы знаний
        """
        # Формируем промпт с базой знаний
        rag_context = "\n\n".join([
            "БАЗА ЗНАНИЙ NL INTERNATIONAL:",
            "=" * 50,
            *knowledge_fragments,
            "=" * 50,
            "",
            "Используй эту информацию для ответа на вопрос пользователя."
        ])

        # Объединяем системный промпт и контекст базы знаний
        enhanced_system_prompt = f"{system_prompt}\n\n{rag_context}"

        logger.info(f"Generating RAG response with {len(knowledge_fragments)} knowledge fragments")

        return await self.generate_response(
            system_prompt=enhanced_system_prompt,
            user_message=user_message,
            context=context,
            temperature=temperature,
            max_tokens=max_tokens
        )
