"""
Клиент для работы с OpenAI API
"""
from typing import List, Dict, Optional
from openai import AsyncOpenAI
from loguru import logger

from shared.config.settings import settings


class OpenAIClient:
    """Клиент для работы с OpenAI API"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Инициализация клиента

        Args:
            api_key: API ключ OpenAI (если None - берется из настроек)
            model: Модель для использования (если None - берется из настроек)
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.curator_ai_model
        self.client = AsyncOpenAI(api_key=self.api_key)
        logger.info(f"OpenAI client initialized with model: {self.model}")

    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Генерирует ответ с использованием OpenAI

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
            messages = [{"role": "system", "content": system_prompt}]

            # Добавляем историю диалога
            if context:
                messages.extend(context)

            # Добавляем текущее сообщение
            messages.append({"role": "user", "content": user_message})

            logger.debug(f"Sending request to OpenAI with {len(messages)} messages")

            # Отправляем запрос
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            answer = response.choices[0].message.content
            logger.info(f"Response generated successfully (tokens: {response.usage.total_tokens})")

            return answer

        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
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
