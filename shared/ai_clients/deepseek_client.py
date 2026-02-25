"""
Клиент для работы с Deepseek API

Deepseek V3 — мощная модель с отличным соотношением цена/качество.
Нет цензуры на бизнес-темы, хороший русский язык.
"""
from typing import List, Dict, Optional
import httpx
from loguru import logger


class DeepseekClient:
    """Клиент для работы с Deepseek API"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "deepseek-chat"
    ):
        """
        Инициализация клиента

        Args:
            api_key: API ключ Deepseek
            model: Модель для использования (deepseek-chat или deepseek-reasoner)
        """
        from shared.config.settings import settings

        self.api_key = api_key or settings.deepseek_api_key
        self.model = model
        self.base_url = "https://api.deepseek.com/v1"

        if not self.api_key:
            raise ValueError("Deepseek API key not provided")

        logger.info(f"Deepseek client initialized with model: {self.model}")

    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Генерирует ответ с использованием Deepseek

        Args:
            system_prompt: Системный промпт
            user_message: Сообщение от пользователя
            context: История диалога
            temperature: Креативность ответа (0.0 - 2.0)
            max_tokens: Максимальная длина ответа

        Returns:
            str: Ответ от AI
        """
        try:
            messages = []

            # Системный промпт
            messages.append({"role": "system", "content": system_prompt})

            # Добавляем историю диалога
            if context:
                for msg in context:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })

            # Добавляем текущее сообщение
            messages.append({"role": "user", "content": user_message})

            logger.debug(f"Sending request to Deepseek with {len(messages)} messages")

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": False
                    }
                )

                response.raise_for_status()
                result = response.json()

            answer = result["choices"][0]["message"]["content"]

            # Логируем использование токенов
            usage = result.get("usage", {})
            logger.info(
                f"Deepseek response generated. "
                f"Tokens: {usage.get('prompt_tokens', '?')} in, "
                f"{usage.get('completion_tokens', '?')} out"
            )

            return answer

        except httpx.HTTPStatusError as e:
            logger.error(f"Deepseek API HTTP error: {e}")
            logger.error(f"Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
            raise

        except Exception as e:
            logger.error(f"Deepseek API error: {e}")
            raise

    async def generate_with_rag(
        self,
        system_prompt: str,
        user_message: str,
        knowledge_fragments: List[str],
        context: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
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
