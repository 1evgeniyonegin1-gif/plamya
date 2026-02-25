"""
Клиент для работы с GigaChat API (Сбер)
"""
from typing import List, Dict, Optional
import httpx
from loguru import logger

from shared.config.settings import settings


class GigaChatClient:
    """Клиент для работы с GigaChat API"""

    def __init__(self, auth_token: Optional[str] = None, model: Optional[str] = None):
        """
        Инициализация клиента

        Args:
            auth_token: Authorization токен (base64)
            model: Модель для использования
        """
        self.auth_token = auth_token or settings.gigachat_auth_token
        self.model = model or "GigaChat"
        self.base_url = "https://gigachat.devices.sberbank.ru/api/v1"
        self.access_token = None
        logger.info(f"GigaChat client initialized with model: {self.model}")

    async def _get_access_token(self, force_refresh: bool = False) -> str:
        """
        Получение access токена через OAuth

        Args:
            force_refresh: Принудительно обновить токен (при 401 ошибке)
        """
        if self.access_token and not force_refresh:
            return self.access_token

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers={
                    "Authorization": f"Basic {self.auth_token}",
                    "RqUID": "6f0b1291-c7f3-43c6-bb2e-9f3efb2dc98e",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data={"scope": "GIGACHAT_API_PERS"}
            )
            response.raise_for_status()
            self.access_token = response.json()["access_token"]
            logger.info("GigaChat access token obtained" + (" (refreshed)" if force_refresh else ""))
            return self.access_token

    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        Генерирует ответ с использованием GigaChat

        Args:
            system_prompt: Системный промпт
            user_message: Сообщение от пользователя
            context: История диалога
            temperature: Креативность ответа (0.0 - 1.0)
            max_tokens: Максимальная длина ответа

        Returns:
            str: Ответ от AI
        """
        # Retry при истечении токена
        for attempt in range(2):
            try:
                access_token = await self._get_access_token(force_refresh=(attempt > 0))

                messages = []

                # Добавляем системный промпт
                messages.append({"role": "system", "content": system_prompt})

                # Добавляем историю диалога
                if context:
                    messages.extend(context)

                # Добавляем текущее сообщение
                messages.append({"role": "user", "content": user_message})

                logger.debug(f"Sending request to GigaChat with {len(messages)} messages")

                async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.model,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        }
                    )

                    # Если 401 - токен истёк, пробуем обновить
                    if response.status_code == 401 and attempt == 0:
                        logger.warning("GigaChat token expired, refreshing...")
                        self.access_token = None  # Сбрасываем токен
                        continue

                    response.raise_for_status()
                    result = response.json()

                answer = result["choices"][0]["message"]["content"]
                logger.info(f"Response generated successfully from GigaChat")

                return answer

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401 and attempt == 0:
                    logger.warning("GigaChat token expired (HTTPStatusError), refreshing...")
                    self.access_token = None
                    continue
                logger.error(f"Error calling GigaChat API: {e}")
                raise

            except Exception as e:
                logger.error(f"Error calling GigaChat API: {e}")
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
