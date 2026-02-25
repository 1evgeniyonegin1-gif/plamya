"""
Auto Setup Service

Автоматическая настройка Traffic Engine для партнёра:
1. Валидация credentials (session_string, proxy)
2. Создание канала (если нужно)
3. Генерация персоны
4. Настройка автопостинга
"""
import asyncio
from typing import Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.partner import (
    Partner,
    PartnerCredentials,
    PartnerChannel,
    PartnerStatus,
    ChannelStatus,
)
from ..config import settings


class SetupStep(str, Enum):
    """Steps of the auto-setup process"""
    VALIDATING_CREDENTIALS = "validating_credentials"
    CHECKING_PROXY = "checking_proxy"
    CONNECTING_TELEGRAM = "connecting_telegram"
    CREATING_CHANNEL = "creating_channel"
    GENERATING_PERSONA = "generating_persona"
    CONFIGURING_POSTING = "configuring_posting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SetupProgress:
    """Progress of the setup process"""
    step: SetupStep
    progress: int  # 0-100
    message: str
    error: Optional[str] = None


@dataclass
class CredentialsInput:
    """Input for connecting new credentials"""
    phone: str
    session_string: str
    api_id: Optional[int] = None
    api_hash: Optional[str] = None
    proxy_type: Optional[str] = None
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None


@dataclass
class ChannelConfig:
    """Configuration for new channel"""
    title: Optional[str] = None  # Auto-generate if not provided
    username: Optional[str] = None
    segment: str = "zozh"
    referral_link: Optional[str] = None
    posts_per_day: int = 2


class AutoSetupService:
    """
    Service for automatic setup of Traffic Engine for a partner
    """

    # Personas by segment
    PERSONAS = {
        "zozh": ["Марина", "Алина", "Виктория", "Екатерина"],
        "mama": ["Анна", "Ольга", "Наталья", "Светлана"],
        "business": ["Кира", "Даша", "Елена", "Александра"],
    }

    def __init__(self, session: AsyncSession):
        self.session = session
        self._progress_callbacks: list = []

    async def setup_partner(
        self,
        partner: Partner,
        credentials: CredentialsInput,
        channel_config: ChannelConfig,
    ) -> tuple[bool, Optional[str]]:
        """
        Full setup process for a partner

        Returns:
            tuple[success: bool, error_message: Optional[str]]
        """
        try:
            # Step 1: Validate credentials format
            await self._report_progress(SetupStep.VALIDATING_CREDENTIALS, 10, "Проверяю данные...")

            if not credentials.session_string:
                return False, "Session string обязателен"

            if not credentials.phone:
                return False, "Номер телефона обязателен"

            # Step 2: Check proxy (if provided)
            if credentials.proxy_host:
                await self._report_progress(SetupStep.CHECKING_PROXY, 20, "Проверяю прокси...")
                proxy_ok = await self._check_proxy(credentials)
                if not proxy_ok:
                    return False, "Прокси недоступен или неверные данные"

            # Step 3: Connect to Telegram
            await self._report_progress(SetupStep.CONNECTING_TELEGRAM, 40, "Подключаюсь к Telegram...")
            telegram_ok, telegram_error = await self._connect_telegram(credentials)
            if not telegram_ok:
                return False, f"Ошибка подключения: {telegram_error}"

            # Save credentials to DB
            db_credentials = PartnerCredentials(
                partner_id=partner.id,
                phone=credentials.phone,
                session_string=credentials.session_string,
                api_id=credentials.api_id or settings.default_api_id,
                api_hash=credentials.api_hash or settings.default_api_hash,
                proxy_type=credentials.proxy_type,
                proxy_host=credentials.proxy_host,
                proxy_port=credentials.proxy_port,
                proxy_username=credentials.proxy_username,
                proxy_password=credentials.proxy_password,
            )
            self.session.add(db_credentials)
            await self.session.flush()

            # Step 4: Create channel
            await self._report_progress(SetupStep.CREATING_CHANNEL, 60, "Создаю канал...")
            channel_id, channel_username = await self._create_or_get_channel(
                credentials, channel_config
            )

            # Step 5: Generate persona
            await self._report_progress(SetupStep.GENERATING_PERSONA, 80, "Настраиваю персону...")
            persona_name = self._select_persona(channel_config.segment)

            # Step 6: Save channel and configure posting
            await self._report_progress(SetupStep.CONFIGURING_POSTING, 90, "Настраиваю автопостинг...")

            db_channel = PartnerChannel(
                partner_id=partner.id,
                credentials_id=db_credentials.id,
                channel_id=channel_id,
                channel_username=channel_username,
                channel_title=channel_config.title or f"Канал {persona_name}",
                segment=channel_config.segment,
                persona_name=persona_name,
                status=ChannelStatus.ACTIVE,
                posting_enabled=True,
                posts_per_day=channel_config.posts_per_day,
                posting_times={"times": ["10:00", "14:00", "18:00"][:channel_config.posts_per_day]},
                referral_link=channel_config.referral_link,
                curator_deeplink=f"https://t.me/nl_curator_bot?start=partner_{partner.telegram_id}",
            )
            self.session.add(db_channel)

            # Update partner status
            partner.status = PartnerStatus.ACTIVE
            partner.total_channels += 1
            partner.last_activity_at = datetime.utcnow()

            await self.session.commit()

            await self._report_progress(SetupStep.COMPLETED, 100, "Готово!")
            return True, None

        except Exception as e:
            await self.session.rollback()
            await self._report_progress(SetupStep.FAILED, 0, f"Ошибка: {str(e)}", str(e))
            return False, str(e)

    async def _check_proxy(self, credentials: CredentialsInput) -> bool:
        """Check if proxy is accessible"""
        # TODO: Implement real proxy check
        # For now, just return True if proxy data is provided
        if credentials.proxy_host and credentials.proxy_port:
            return True
        return True

    async def _connect_telegram(self, credentials: CredentialsInput) -> tuple[bool, Optional[str]]:
        """
        Connect to Telegram and verify the session

        Returns:
            tuple[success: bool, error_message: Optional[str]]
        """
        try:
            # TODO: Implement real Telethon connection
            # from telethon import TelegramClient
            # from telethon.sessions import StringSession
            #
            # client = TelegramClient(
            #     StringSession(credentials.session_string),
            #     credentials.api_id or settings.default_api_id,
            #     credentials.api_hash or settings.default_api_hash,
            # )
            #
            # if credentials.proxy_host:
            #     client.set_proxy(...)
            #
            # await client.connect()
            # if not await client.is_user_authorized():
            #     return False, "Session не авторизована"
            #
            # me = await client.get_me()
            # await client.disconnect()
            # return True, None

            # For now, simulate success
            await asyncio.sleep(1)  # Simulate connection delay
            return True, None

        except Exception as e:
            return False, str(e)

    async def _create_or_get_channel(
        self, credentials: CredentialsInput, config: ChannelConfig
    ) -> tuple[int, Optional[str]]:
        """
        Create a new channel or get existing one

        Returns:
            tuple[channel_id: int, channel_username: Optional[str]]
        """
        # TODO: Implement real channel creation via Telethon
        # from telethon.tl.functions.channels import CreateChannelRequest
        #
        # result = await client(CreateChannelRequest(
        #     title=config.title or f"Канал {persona_name}",
        #     about="Добро пожаловать!",
        #     megagroup=False,
        # ))
        # channel = result.chats[0]
        # return channel.id, getattr(channel, 'username', None)

        # For now, return placeholder
        import random
        fake_channel_id = random.randint(1000000000, 9999999999)
        return fake_channel_id, None

    def _select_persona(self, segment: str) -> str:
        """Select a random persona for the segment"""
        import random
        personas = self.PERSONAS.get(segment, self.PERSONAS["zozh"])
        return random.choice(personas)

    async def _report_progress(
        self,
        step: SetupStep,
        progress: int,
        message: str,
        error: Optional[str] = None
    ):
        """Report progress to all registered callbacks"""
        progress_data = SetupProgress(
            step=step,
            progress=progress,
            message=message,
            error=error,
        )
        for callback in self._progress_callbacks:
            await callback(progress_data)

    def on_progress(self, callback):
        """Register a progress callback"""
        self._progress_callbacks.append(callback)

    async def validate_session_string(self, session_string: str) -> tuple[bool, Optional[str]]:
        """
        Quick validation of session string format

        Returns:
            tuple[valid: bool, error: Optional[str]]
        """
        if not session_string:
            return False, "Session string пустой"

        if len(session_string) < 100:
            return False, "Session string слишком короткий"

        # Basic format check (Telethon session strings are base64-encoded)
        import base64
        try:
            base64.b64decode(session_string)
            return True, None
        except Exception:
            return False, "Неверный формат session string"
