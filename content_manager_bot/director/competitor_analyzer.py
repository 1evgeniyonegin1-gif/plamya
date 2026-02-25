"""
CompetitorAnalyzer — анализ конкурентов через Telethon.

Вдохновлено: MarketMuse (competitive analysis), Lately.ai (voice extraction).

Раз в неделю читает 30 постов из каналов конкурентов,
находит топ-10 по engagement, анализирует через Deepseek.
"""
import json
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger

from shared.ai_clients.deepseek_client import DeepseekClient
from content_manager_bot.director.channel_memory import get_channel_memory


class CompetitorAnalyzer:
    """Анализатор конкурентных каналов по сегментам."""

    # Каналы конкурентов по нишам
    # Легко расширяется: "mama": [...], "student": [...]
    COMPETITOR_CHANNELS = {
        "zozh": ["@zdorovie_ru", "@pp_recepty", "@zozh_blog"],
        "business": ["@business_ru", "@dengi_tips", "@mlm_success"],
    }

    def __init__(self):
        self._ai_client: Optional[DeepseekClient] = None

    def _get_ai(self) -> DeepseekClient:
        if self._ai_client is None:
            self._ai_client = DeepseekClient()
        return self._ai_client

    async def analyze(self, segment: str) -> Optional[dict]:
        """Полный анализ конкурентов для сегмента.

        Returns:
            dict: {trending_topics, winning_formats, hooks_that_work, our_angle}
        """
        try:
            # 1. Читаем посты конкурентов
            all_posts = await self._fetch_competitor_posts(segment)

            if not all_posts:
                logger.info(f"[DIRECTOR] No competitor posts for {segment}, skipping analysis")
                return None

            # 2. Находим топ-10 по reactions/views
            sorted_posts = sorted(
                all_posts,
                key=lambda p: p.get("reactions", 0) + p.get("views", 0) * 0.01,
                reverse=True,
            )
            top_posts = sorted_posts[:10]

            # 3. AI анализ
            posts_block = "\n\n".join([
                f"{i+1}. [{p.get('reactions', 0)} реакций, {p.get('views', 0)} просмотров] "
                f"{p.get('channel', '?')}: \"{p.get('text', '')[:200]}\""
                for i, p in enumerate(top_posts)
            ])

            prompt = f"""Вот 10 самых успешных постов конкурентов в нише {segment} за неделю:

{posts_block}

Ответь СТРОГО JSON (без markdown):
{{
  "trending_topics": ["тема1", "тема2", "тема3"],
  "winning_formats": ["формат1", "формат2"],
  "hooks_that_work": ["хук1", "хук2"],
  "our_angle": "одно предложение — чем мы можем отличиться"
}}"""

            ai = self._get_ai()
            response = await ai.generate_response(
                system_prompt="Ты аналитик контента. Анализируешь конкурентов и выявляешь тренды. Отвечаешь только JSON.",
                user_message=prompt,
                temperature=0.7,
                max_tokens=500,
            )

            # Парсим
            insights = self._parse_insights(response)
            if not insights:
                logger.error(f"[DIRECTOR] Failed to parse competitor insights for {segment}")
                return None

            # 4. Сохраняем в ChannelMemory
            memory = get_channel_memory()
            await memory.set_competitor_insights(segment, insights)

            logger.info(f"[DIRECTOR] Competitor analysis complete for {segment}: {insights.get('trending_topics', [])}")
            return insights

        except Exception as e:
            logger.error(f"[DIRECTOR] Competitor analysis error: {e}")
            return None

    async def get_competitor_insights(self, segment: str) -> str:
        """Строка для промпта планировщика."""
        memory = get_channel_memory()
        state = await memory.get_state(segment)
        insights = state.get("competitor_insights", {})

        if not insights:
            return ""

        lines = ["🔍 КОНКУРЕНТЫ:"]

        topics = insights.get("trending_topics", [])
        if topics:
            lines.append(f"Trending: {', '.join(topics[:5])}")

        formats = insights.get("winning_formats", [])
        if formats:
            lines.append(f"Форматы: {', '.join(formats[:3])}")

        angle = insights.get("our_angle", "")
        if angle:
            lines.append(f"Наш угол: {angle}")

        return "\n".join(lines)

    async def _fetch_competitor_posts(self, segment: str) -> list[dict]:
        """Читает посты конкурентов через Telethon или ChannelFetcher."""
        channels = self.COMPETITOR_CHANNELS.get(segment, [])
        if not channels:
            return []

        all_posts = []

        try:
            # Пробуем через ChannelFetcher (shared)
            from shared.style_monitor.channel_fetcher import ChannelFetcher

            fetcher = ChannelFetcher()
            await fetcher.connect()

            for channel in channels:
                try:
                    posts = await fetcher.fetch_posts(
                        channel_id=channel,
                        limit=30,
                        min_date=datetime.utcnow() - timedelta(days=7),
                    )

                    for p in posts:
                        if p.get("text"):
                            all_posts.append({
                                "channel": channel,
                                "text": p["text"],
                                "views": p.get("views", 0),
                                "reactions": p.get("reactions", 0),
                                "date": p.get("date"),
                            })

                except Exception as e:
                    logger.warning(f"[DIRECTOR] Failed to fetch {channel}: {e}")
                    continue

            logger.info(f"[DIRECTOR] Fetched {len(all_posts)} competitor posts for {segment}")

        except ImportError:
            logger.warning("[DIRECTOR] ChannelFetcher not available, skipping competitor fetch")
        except Exception as e:
            logger.warning(f"[DIRECTOR] Competitor fetch error: {e}")

        return all_posts

    def _parse_insights(self, response: str) -> Optional[dict]:
        """Парсит insights из ответа AI."""
        try:
            text = response.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            start = text.find('{')
            end = text.rfind('}')
            if start == -1 or end == -1:
                return None

            data = json.loads(text[start:end + 1])

            # Минимальная валидация
            if "trending_topics" in data:
                return data

            return None

        except (json.JSONDecodeError, ValueError):
            return None


# Singleton
_analyzer: Optional[CompetitorAnalyzer] = None


def get_competitor_analyzer() -> CompetitorAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = CompetitorAnalyzer()
    return _analyzer
