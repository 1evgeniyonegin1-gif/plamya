"""Example action: read Telegram channel with Input Guard protection."""

import logging

from shared.ai_client_cli import claude_call

logger = logging.getLogger(__name__)


async def read_channel():
    """Read messages from a Telegram channel and analyze with AI.

    Key security pattern: channel messages are UNTRUSTED data.
    They go through Input Guard before reaching the LLM.
    """
    # In a real agent, you'd use Telethon to fetch messages
    # messages = await client.get_messages(channel, limit=10)

    # Example: analyzing an external message
    external_message = "Example channel post about health products"

    analysis = claude_call(
        prompt="Analyze this channel post. What topics does it cover? What's the tone?",
        agent="chappie",
        # Input Guard wraps this as UNTRUSTED DATA before sending to LLM
        untrusted_data=external_message,
        untrusted_source="telegram_channel",
    )

    logger.info(f"Channel analysis: {analysis[:100]}...")
