"""Telethon клиент для личного аккаунта Данила."""

import asyncio
import logging

from telethon import TelegramClient
from telethon.sessions import StringSession

from chappie_engine.config import SESSION_STRING, API_ID, API_HASH

logger = logging.getLogger("chappie.client")


class PersonalAccountClient:
    """Управление одним личным Telegram аккаунтом.

    В отличие от AccountManager (Traffic Engine), который управляет пулом
    ботовских аккаунтов из БД, этот класс работает с ОДНИМ личным аккаунтом
    из config файла. Более строгие лимиты, потому что бан = катастрофа.
    """

    def __init__(self):
        if not SESSION_STRING:
            raise ValueError(
                "Session string не настроен! "
                "Добавь его в ~/.openclaw/shared/chappie_config.json"
            )
        if not API_ID or not API_HASH:
            raise ValueError(
                "API_ID и API_HASH не настроены! "
                "Добавь их в ~/.openclaw/shared/chappie_config.json"
            )

        self._client = TelegramClient(
            StringSession(SESSION_STRING),
            API_ID,
            API_HASH,
            device_model="Samsung Galaxy S24",
            system_version="Android 14",
            app_version="10.8.1",
            lang_code="ru",
            system_lang_code="ru",
        )
        self._connected = False
        self._me = None

    async def connect(self):
        """Подключиться к Telegram."""
        if self._connected:
            return

        await self._client.connect()

        if not await self._client.is_user_authorized():
            raise ValueError(
                "Session string невалиден или аккаунт разлогинен! "
                "Нужно перегенерировать session string."
            )

        self._me = await self._client.get_me()
        self._connected = True
        logger.info(f"Подключён как {self._me.first_name} (@{self._me.username})")

    async def disconnect(self):
        """Отключиться от Telegram."""
        if self._connected:
            await self._client.disconnect()
            self._connected = False
            logger.info("Отключён от Telegram")

    @property
    def client(self) -> TelegramClient:
        """Telethon клиент для прямых вызовов API."""
        if not self._connected:
            raise RuntimeError("Клиент не подключён! Вызови connect() сначала.")
        return self._client

    @property
    def me(self):
        """Информация о текущем аккаунте."""
        return self._me

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.disconnect()
