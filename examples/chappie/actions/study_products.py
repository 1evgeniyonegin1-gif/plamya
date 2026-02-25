"""Example action: study products from knowledge base using AI."""

import logging
from pathlib import Path

from shared.ai_client_cli import claude_call

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).parent.parent.parent.parent / "content" / "knowledge_base"


async def study_products():
    """Read product files and generate summaries using AI."""
    if not KNOWLEDGE_DIR.exists():
        logger.info("No knowledge base found, skipping")
        return

    for product_file in KNOWLEDGE_DIR.glob("*.md"):
        text = product_file.read_text(encoding="utf-8")

        # AI call with all guards built in
        summary = claude_call(
            prompt=f"Summarize this product in 2-3 sentences for a social media post:\n\n{text}",
            agent="chappie",
        )

        logger.info(f"Studied: {product_file.name} -> {summary[:100]}...")
