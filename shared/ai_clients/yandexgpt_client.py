"""
Клиент для работы с YandexGPT API
"""
from typing import List, Dict, Optional
import httpx
import jwt
import time
from loguru import logger

from shared.config.settings import settings


class YandexGPTClient:
    """Клиент для работы с YandexGPT API"""

    def __init__(
        self,
        service_account_id: Optional[str] = None,
        key_id: Optional[str] = None,
        private_key: Optional[str] = None,
        folder_id: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Инициализация клиента

        Args:
            service_account_id: ID сервисного аккаунта
            key_id: ID ключа (из комментария в private_key)
            private_key: Приватный ключ (содержимое PEM файла)
            folder_id: ID каталога в Yandex Cloud
            model: Модель для использования (lite или pro)
        """
        self.service_account_id = service_account_id or settings.yandex_service_account_id
        self.key_id = key_id or settings.yandex_key_id

        # Обрабатываем приватный ключ: заменяем \n на реальные переносы строк
        raw_key = private_key or settings.yandex_private_key
        self.private_key = raw_key.replace('\\n', '\n') if raw_key else None

        self.folder_id = folder_id or settings.yandex_folder_id
        self.model = model or settings.yandex_model or "yandexgpt-lite"
        self.base_url = "https://llm.api.cloud.yandex.net/foundationModels/v1"
        self.iam_token = None
        self.token_expires_at = 0
        logger.info(f"YandexGPT client initialized with model: {self.model}")

    def _create_jwt_token(self) -> str:
        """
        Создание JWT токена для получения IAM токена

        Returns:
            str: JWT токен
        """
        now = int(time.time())
        payload = {
            'aud': 'https://iam.api.cloud.yandex.net/iam/v1/tokens',
            'iss': self.service_account_id,
            'iat': now,
            'exp': now + 3600  # Токен действует 1 час
        }

        # Создаём JWT токен
        encoded_token = jwt.encode(
            payload,
            self.private_key,
            algorithm='PS256',
            headers={'kid': self.key_id}
        )

        return encoded_token

    async def _get_iam_token(self, force_refresh: bool = False) -> str:
        """
        Получение IAM токена через JWT

        Args:
            force_refresh: Принудительно обновить токен

        Returns:
            str: IAM токен
        """
        # Проверяем, не истёк ли текущий токен
        if self.iam_token and not force_refresh and time.time() < self.token_expires_at:
            return self.iam_token

        try:
            # Создаём JWT токен
            jwt_token = self._create_jwt_token()

            # Обмениваем JWT на IAM токен
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'https://iam.api.cloud.yandex.net/iam/v1/tokens',
                    json={'jwt': jwt_token}
                )
                response.raise_for_status()
                result = response.json()

                self.iam_token = result['iamToken']
                # Токен действует ~12 часов, но обновим за час до истечения
                self.token_expires_at = time.time() + (11 * 3600)

                logger.info("YandexGPT IAM token obtained" + (" (refreshed)" if force_refresh else ""))
                return self.iam_token

        except Exception as e:
            logger.error(f"Error obtaining IAM token: {e}")
            raise

    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.6,
        max_tokens: int = 2000
    ) -> str:
        """
        Генерирует ответ с использованием YandexGPT

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
                iam_token = await self._get_iam_token(force_refresh=(attempt > 0))

                messages = []

                # YandexGPT использует системный промпт как первое сообщение
                messages.append({"role": "system", "text": system_prompt})

                # Добавляем историю диалога
                if context:
                    for msg in context:
                        messages.append({
                            "role": msg.get("role", "user"),
                            "text": msg.get("content", "")
                        })

                # Добавляем текущее сообщение
                messages.append({"role": "user", "text": user_message})

                logger.debug(f"Sending request to YandexGPT with {len(messages)} messages")

                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.base_url}/completion",
                        headers={
                            "Authorization": f"Bearer {iam_token}",
                            "Content-Type": "application/json",
                            "x-folder-id": self.folder_id
                        },
                        json={
                            "modelUri": f"gpt://{self.folder_id}/{self.model}/latest",
                            "completionOptions": {
                                "stream": False,
                                "temperature": temperature,
                                "maxTokens": str(max_tokens)
                            },
                            "messages": messages
                        }
                    )

                    # Если 401/403 - токен истёк, пробуем обновить
                    if response.status_code in [401, 403] and attempt == 0:
                        logger.warning("YandexGPT token expired, refreshing...")
                        self.iam_token = None
                        self.token_expires_at = 0
                        continue

                    response.raise_for_status()
                    result = response.json()

                answer = result["result"]["alternatives"][0]["message"]["text"]
                logger.info(f"Response generated successfully from YandexGPT")

                return answer

            except httpx.HTTPStatusError as e:
                if e.response.status_code in [401, 403] and attempt == 0:
                    logger.warning("YandexGPT token expired (HTTPStatusError), refreshing...")
                    self.iam_token = None
                    self.token_expires_at = 0
                    continue
                logger.error(f"Error calling YandexGPT API: {e}")
                logger.error(f"Response body: {e.response.text if hasattr(e, 'response') else 'N/A'}")
                raise

            except Exception as e:
                logger.error(f"Error calling YandexGPT API: {e}")
                raise

    async def generate_with_rag(
        self,
        system_prompt: str,
        user_message: str,
        knowledge_fragments: List[str],
        context: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.6,
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
