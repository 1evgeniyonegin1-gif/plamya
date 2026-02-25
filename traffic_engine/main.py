#!/usr/bin/env python
"""
Traffic Engine - Main entry point.

Запускает систему автоматизированного трафика.
Использует Telethon для работы с Telegram API.
"""

import asyncio
import signal
import sys
from typing import Dict, Optional

from loguru import logger

from traffic_engine.config import settings
from traffic_engine.database import init_db, get_session
from traffic_engine.database.models import Tenant
from traffic_engine.core import AccountManager
from traffic_engine.channels.auto_comments import ChannelMonitor
from traffic_engine.channels.story_viewer import StoryMonitor
from traffic_engine.channels.chat_inviter import InviteMonitor
from traffic_engine.channels.reply_checker import ReplyChecker
from traffic_engine.channels.own_channels import OwnChannelMonitor
from traffic_engine.channels.story_poster import StoryPoster
from traffic_engine.posting import AutoPoster
from traffic_engine.core import StrategySelector
from traffic_engine.notifications import TelegramNotifier
from discipline_bot.scheduler import DisciplineScheduler


class TrafficEngine:
    """
    Main Traffic Engine class.

    Управляет всеми компонентами системы:
    - Account Manager
    - Channel Monitor (автокомментирование)
    - Story Monitor (просмотр сторис ЦА)
    - Invite Monitor (инвайты в группы-мероприятия)
    """

    def __init__(self):
        """Initialize Traffic Engine."""
        self.monitors: Dict[int, ChannelMonitor] = {}  # tenant_id -> monitor
        self.story_monitors: Dict[int, StoryMonitor] = {}  # tenant_id -> story monitor
        self.invite_monitors: Dict[int, InviteMonitor] = {}  # tenant_id -> invite monitor
        self.reply_checkers: Dict[int, ReplyChecker] = {}  # tenant_id -> reply checker
        self.auto_posters: Dict[int, AutoPoster] = {}  # tenant_id -> auto poster
        self.own_channel_monitors: Dict[int, OwnChannelMonitor] = {}  # tenant_id -> own channel monitor
        self.story_posters: Dict[int, StoryPoster] = {}  # tenant_id -> story poster
        self.discipline_schedulers: Dict[int, DisciplineScheduler] = {}  # tenant_id -> discipline
        self.account_managers: Dict[int, AccountManager] = {}
        self.strategy_selector = StrategySelector()
        self.notifier: Optional[TelegramNotifier] = None
        self._running = False

    async def start(self, tenant_names: Optional[list] = None) -> None:
        """
        Start Traffic Engine for specified tenants.

        Args:
            tenant_names: List of tenant names to start (None = all active)
        """
        logger.info("=== Starting Traffic Engine ===")

        # Initialize database
        await init_db()
        logger.info("Database initialized")

        # Initialize Telegram notifier for alerts
        if settings.alert_bot_token and settings.alerts_enabled:
            self.notifier = TelegramNotifier(
                bot_token=settings.alert_bot_token,
                admin_id=settings.alert_admin_id,
                enabled=True,
                notify_success=settings.notify_success,
            )
            logger.info(f"Telegram notifier initialized (success_notify={'ON' if settings.notify_success else 'OFF'})")

        # Load tenants
        async with get_session() as session:
            from sqlalchemy import select
            query = select(Tenant).where(Tenant.is_active == True)

            if tenant_names:
                query = query.where(Tenant.name.in_(tenant_names))

            result = await session.execute(query)
            tenants = result.scalars().all()

            if not tenants:
                logger.error("No active tenants found!")
                return

            logger.info(f"Found {len(tenants)} active tenant(s)")

            # Start monitor for each tenant
            for tenant in tenants:
                await self._start_tenant(tenant)

        self._running = True

        # Keep running
        logger.info("Traffic Engine is running. Press Ctrl+C to stop.")

        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

        await self.stop()

    async def _start_tenant(self, tenant: Tenant) -> None:
        """Start monitoring for a tenant."""
        logger.info(f"Starting tenant: {tenant.display_name}")

        # Create account manager
        account_manager = AccountManager(tenant.id)
        await account_manager.initialize()
        self.account_managers[tenant.id] = account_manager

        # Create channel monitor with notifier
        monitor = ChannelMonitor(
            tenant_id=tenant.id,
            account_manager=account_manager,
            notifier=self.notifier,
        )
        # Share strategy selector with channel monitor for MAB
        monitor.strategy_selector = self.strategy_selector
        await monitor.initialize(tenant_name=tenant.name)
        self.monitors[tenant.id] = monitor

        # Start monitoring in background
        asyncio.create_task(monitor.start())

        # Create story monitor for viewing stories of target audience
        story_monitor = StoryMonitor(
            tenant_id=tenant.id,
            account_manager=account_manager,
            notifier=self.notifier,
        )
        await story_monitor.initialize()
        self.story_monitors[tenant.id] = story_monitor

        # Start story monitoring in background
        asyncio.create_task(story_monitor.start())

        # Create invite monitor for inviting target audience to event groups
        invite_monitor = InviteMonitor(
            tenant_id=tenant.id,
            account_manager=account_manager,
            notifier=self.notifier,
        )
        await invite_monitor.initialize()
        self.invite_monitors[tenant.id] = invite_monitor

        # Start invite monitoring in background
        asyncio.create_task(invite_monitor.start())

        # Create reply checker for tracking comment responses
        reply_checker = ReplyChecker(
            account_manager=account_manager,
            strategy_selector=self.strategy_selector,
            notifier=self.notifier,
            check_interval=3600,  # Каждый час
            lookback_hours=4,
        )
        self.reply_checkers[tenant.id] = reply_checker

        # Start reply checker in background
        asyncio.create_task(reply_checker.start())

        # Create auto poster for thematic channels
        auto_poster = AutoPoster(
            tenant_id=tenant.id,
            account_manager=account_manager,
            notifier=self.notifier,
        )
        self.auto_posters[tenant.id] = auto_poster
        asyncio.create_task(auto_poster.start())

        # Create own channel monitor (replies to comments in own channels)
        own_channel_monitor = OwnChannelMonitor(
            tenant_id=tenant.id,
            account_manager=account_manager,
            notifier=self.notifier,
        )
        self.own_channel_monitors[tenant.id] = own_channel_monitor
        asyncio.create_task(own_channel_monitor.start())

        # Create story poster (publishes stories from bot accounts)
        story_poster = StoryPoster(
            tenant_id=tenant.id,
            account_manager=account_manager,
            notifier=self.notifier,
        )
        self.story_posters[tenant.id] = story_poster
        asyncio.create_task(story_poster.start())

        # Create discipline scheduler (Sergeant — writes to admin DM)
        discipline_scheduler = DisciplineScheduler(
            account_manager=account_manager,
            notifier=self.notifier,
        )
        self.discipline_schedulers[tenant.id] = discipline_scheduler
        asyncio.create_task(discipline_scheduler.start())

        logger.info(
            f"Tenant {tenant.name} started "
            f"(comments + stories + invites + replies + posting + own_channels + story_poster + discipline)"
        )

        # Send start notification
        if self.notifier:
            accounts_count = len(account_manager._clients) if hasattr(account_manager, '_clients') else 0
            channels_count = len(monitor._channels) if hasattr(monitor, '_channels') else 0
            await self.notifier.notify_system_start(accounts_count, channels_count)
            # Note: Story monitor also started but using same accounts

    async def stop(self) -> None:
        """Stop Traffic Engine."""
        logger.info("Stopping Traffic Engine...")
        self._running = False

        # Send stop notification
        if self.notifier:
            await self.notifier.notify_system_stop("Manual shutdown")
            await self.notifier.close()

        # Stop all monitors
        for tenant_id, monitor in self.monitors.items():
            await monitor.stop()

        # Stop all story monitors
        for tenant_id, story_monitor in self.story_monitors.items():
            await story_monitor.stop()

        # Stop all invite monitors
        for tenant_id, invite_monitor in self.invite_monitors.items():
            await invite_monitor.stop()

        # Stop all reply checkers
        for tenant_id, checker in self.reply_checkers.items():
            await checker.stop()

        # Stop all auto posters
        for tenant_id, poster in self.auto_posters.items():
            await poster.stop()

        # Stop all own channel monitors
        for tenant_id, ocm in self.own_channel_monitors.items():
            await ocm.stop()

        # Stop all story posters
        for tenant_id, sp in self.story_posters.items():
            await sp.stop()

        # Stop all discipline schedulers
        for tenant_id, ds in self.discipline_schedulers.items():
            await ds.stop()

        # Close all account managers
        for tenant_id, manager in self.account_managers.items():
            await manager.close()

        logger.info("Traffic Engine stopped")


async def main():
    """Main entry point."""
    # Configure logging
    logger.add(
        "logs/traffic_engine_{time}.log",
        rotation="1 day",
        retention="7 days",
        level=settings.log_level,
    )

    engine = TrafficEngine()

    # Handle shutdown signals (use get_running_loop inside async context)
    loop = asyncio.get_running_loop()

    def signal_handler():
        logger.info("Shutdown signal received")
        asyncio.create_task(engine.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    # Start engine
    await engine.start()


def run():
    """Entry point that creates event loop explicitly for Python 3.14+."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")


if __name__ == "__main__":
    run()
