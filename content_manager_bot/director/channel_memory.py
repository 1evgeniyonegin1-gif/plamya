"""
ChannelMemory — Structured Memory (Mem0/A.U.D.N. стиль).

Вместо тупого «последние 15 постов» → компактное состояние канала:
- Topic Authority Map (MarketMuse)
- Narrative threads
- Performance memory (top/worst)
- Voice fingerprint (Lately.ai)
- Reflection rules (из ReflectionEngine)

A.U.D.N. цикл: Add / Update / Delete / No-op.
"""
import re
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger
from sqlalchemy import select

from shared.database.base import AsyncSessionLocal
from content_manager_bot.database.director_models import ChannelMemoryModel
from content_manager_bot.database.models import Post


class ChannelMemory:
    """Структурированная память канала."""

    # Дефолтное состояние
    DEFAULT_STATE = {
        "total_posts": 0,
        "topic_coverage": {},
        "topic_gaps": [],
        "active_threads": [],
        "pending_questions": [],
        "top_posts": [],
        "worst_posts": [],
        "avg_length": 0,
        "emoji_density": 0.0,
        "question_rate": 0.0,
        "cta_rate": 0.0,
        "reflection_rules": [],
        "rejection_log": [],
        "competitor_insights": {},
        "keyword_baseline": {},
        "last_updated": None,
    }

    async def get_state(self, segment: str) -> dict:
        """Получает текущее состояние канала."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ChannelMemoryModel).where(ChannelMemoryModel.segment == segment)
                )
                record = result.scalar_one_or_none()

                if record and record.state_data:
                    # Merge defaults with stored data
                    state = {**self.DEFAULT_STATE, **record.state_data}
                    return state

                return dict(self.DEFAULT_STATE)

        except Exception as e:
            logger.warning(f"[DIRECTOR] get_state error: {e}")
            return dict(self.DEFAULT_STATE)

    async def update_after_publish(self, segment: str, post_content: str, post_type: str,
                                    post_id: int, engagement_rate: Optional[float] = None):
        """A.U.D.N. цикл после публикации поста."""
        try:
            state = await self.get_state(segment)

            # === ADD ===
            state["total_posts"] += 1

            # Topic coverage: извлекаем ключевые слова
            topics = self._extract_topics(post_content)
            for topic in topics:
                state["topic_coverage"][topic] = state["topic_coverage"].get(topic, 0) + 1

            # === UPDATE ===
            # Active threads: если тема совпадает с существующей
            for thread in state.get("active_threads", []):
                thread_topic = thread.get("topic", "").lower()
                if any(t.lower() in thread_topic or thread_topic in t.lower() for t in topics):
                    thread["posts_count"] = thread.get("posts_count", 0) + 1
                    thread["last_mention"] = datetime.utcnow().isoformat()

            # Pending questions: проверяем есть ли вопрос в конце
            last_100 = post_content[-100:] if len(post_content) > 100 else post_content
            if '?' in last_100:
                question = last_100.split('?')[0].split('\n')[-1].strip() + '?'
                if len(question) > 10:
                    questions = state.get("pending_questions", [])
                    questions.append(question[:100])
                    state["pending_questions"] = questions[-5:]  # keep last 5

            # Performance memory
            if engagement_rate is not None:
                post_info = {
                    "id": post_id,
                    "preview": post_content[:80],
                    "type": post_type,
                    "engagement": engagement_rate,
                }

                # Top posts
                top = state.get("top_posts", [])
                top.append(post_info)
                top.sort(key=lambda x: x.get("engagement", 0), reverse=True)
                state["top_posts"] = top[:5]

                # Worst posts
                worst = state.get("worst_posts", [])
                worst.append(post_info)
                worst.sort(key=lambda x: x.get("engagement", 0))
                state["worst_posts"] = worst[:3]

            # === DELETE ===
            # Удаляем threads старше 14 дней
            now = datetime.utcnow()
            active_threads = []
            for thread in state.get("active_threads", []):
                last_mention = thread.get("last_mention")
                if last_mention:
                    try:
                        last_dt = datetime.fromisoformat(last_mention)
                        if (now - last_dt).days < 14:
                            active_threads.append(thread)
                    except (ValueError, TypeError):
                        active_threads.append(thread)
                else:
                    active_threads.append(thread)
            state["active_threads"] = active_threads

            # === NO-OP: Voice fingerprint каждые 5 постов ===
            if state["total_posts"] % 5 == 0:
                await self._update_voice_fingerprint(state, segment)

            # Topic gaps
            all_expected_topics = self._get_expected_topics(segment)
            state["topic_gaps"] = [
                t for t in all_expected_topics
                if state["topic_coverage"].get(t, 0) < 2
            ]

            state["last_updated"] = now.isoformat()

            # Save
            await self._save_state(segment, state)
            logger.info(f"[DIRECTOR] ChannelMemory updated for {segment}: {state['total_posts']} posts")

        except Exception as e:
            logger.error(f"[DIRECTOR] update_after_publish error: {e}")

    async def get_context_for_prompt(self, segment: str) -> str:
        """Возвращает компактную строку (~200 токенов) для промпта."""
        state = await self.get_state(segment)

        if state["total_posts"] == 0:
            return ""

        lines = [f"📊 КАНАЛ ({segment}, {state['total_posts']} постов):"]

        # Сильные темы
        coverage = state.get("topic_coverage", {})
        if coverage:
            sorted_topics = sorted(coverage.items(), key=lambda x: x[1], reverse=True)[:5]
            topics_str = ", ".join(f"{t} ({c})" for t, c in sorted_topics)
            lines.append(f"Сильные темы: {topics_str}")

        # Пробелы
        gaps = state.get("topic_gaps", [])
        if gaps:
            lines.append(f"Пробелы: {', '.join(gaps[:5])}")

        # Нити
        threads = state.get("active_threads", [])
        if threads:
            threads_str = ", ".join(f'"{t["topic"]}" ({t.get("posts_count", 1)} п.)' for t in threads[:3])
            lines.append(f"Активные нити: {threads_str}")

        # Нераскрытые вопросы
        questions = state.get("pending_questions", [])
        if questions:
            lines.append(f"Нераскрытый вопрос: \"{questions[-1]}\"")

        # Топ-пост
        top = state.get("top_posts", [])
        if top:
            best = top[0]
            lines.append(f"Топ-пост: {best['type']} ({best.get('engagement', 0):.1f}% eng)")

        # Voice
        if state.get("avg_length"):
            q_rate = state.get("question_rate", 0)
            lines.append(f"Voice: средняя {state['avg_length']} символов, вопрос в {q_rate:.0%} постов")

        # Reflection rules
        rules = state.get("reflection_rules", [])
        if rules:
            lines.append(f"Уроки из правок: {'; '.join(rules[:3])}")

        # Competitor insights
        insights = state.get("competitor_insights", {})
        if insights.get("trending_topics"):
            lines.append(f"Trending у конкурентов: {', '.join(insights['trending_topics'][:3])}")

        return "\n".join(lines)

    async def add_thread(self, segment: str, topic: str, post_id: int):
        """Добавляет новую нарративную нить."""
        state = await self.get_state(segment)
        threads = state.get("active_threads", [])
        threads.append({
            "topic": topic,
            "started_post_id": post_id,
            "posts_count": 1,
            "last_mention": datetime.utcnow().isoformat(),
        })
        state["active_threads"] = threads[-10:]  # max 10
        await self._save_state(segment, state)

    async def add_rejection(self, segment: str, original_content: str, action: str,
                            reason: str, post_type: str):
        """Логирует отклонение/правку для ReflectionEngine."""
        state = await self.get_state(segment)

        log = state.get("rejection_log", [])
        log.append({
            "original_preview": original_content[:200],
            "action": action,  # "reject" or "edit"
            "reason": reason,
            "post_type": post_type,
            "timestamp": datetime.utcnow().isoformat(),
        })
        state["rejection_log"] = log[-10:]  # keep last 10

        await self._save_state(segment, state)
        logger.info(f"[DIRECTOR] Rejection logged for {segment}: {action}")

    async def set_reflection_rules(self, segment: str, rules: list[str]):
        """Устанавливает правила из ReflectionEngine."""
        state = await self.get_state(segment)
        state["reflection_rules"] = rules[-10:]  # max 10
        await self._save_state(segment, state)
        logger.info(f"[DIRECTOR] Reflection rules updated for {segment}: {len(rules)} rules")

    async def set_competitor_insights(self, segment: str, insights: dict):
        """Устанавливает insights от CompetitorAnalyzer."""
        state = await self.get_state(segment)
        state["competitor_insights"] = insights
        await self._save_state(segment, state)
        logger.info(f"[DIRECTOR] Competitor insights updated for {segment}")

    async def update_keyword_baseline(self, segment: str, baseline: dict):
        """Обновляет фоновую частоту ключевых слов для TrendDetector."""
        state = await self.get_state(segment)
        state["keyword_baseline"] = baseline
        await self._save_state(segment, state)

    async def _update_voice_fingerprint(self, state: dict, segment: str):
        """Пересчитывает voice fingerprint (каждые 5 постов)."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Post.content).where(
                        Post.status == "published",
                        Post.segment == segment,
                    ).order_by(Post.published_at.desc()).limit(20)
                )
                contents = [row[0] for row in result.all()]

                if not contents:
                    return

                # Средняя длина
                state["avg_length"] = int(sum(len(c) for c in contents) / len(contents))

                # Emoji density
                total_emojis = sum(len(re.findall(r'[\U0001f600-\U0001f999]', c)) for c in contents)
                total_chars = sum(len(c) for c in contents)
                state["emoji_density"] = total_emojis / max(total_chars, 1)

                # Question rate
                questions = sum(1 for c in contents if '?' in c[-100:])
                state["question_rate"] = questions / len(contents)

                # CTA rate
                cta_markers = ["пиши", "переходи", "ссылк", "бот", "@"]
                ctas = sum(1 for c in contents if any(m in c.lower() for m in cta_markers))
                state["cta_rate"] = ctas / len(contents)

                logger.info(
                    f"[DIRECTOR] Voice fingerprint updated: avg_len={state['avg_length']}, "
                    f"question_rate={state['question_rate']:.0%}"
                )

        except Exception as e:
            logger.warning(f"[DIRECTOR] Voice fingerprint update failed: {e}")

    def _extract_topics(self, content: str) -> list[str]:
        """Извлекает ключевые темы из поста (простой TF)."""
        # Стоп-слова
        stop_words = {
            "это", "что", "как", "для", "уже", "все", "вот", "так", "тоже",
            "есть", "мне", "мой", "где", "тут", "там", "они", "она", "ему",
            "если", "когда", "потому", "чтобы", "может", "нет", "просто",
            "очень", "даже", "или", "при", "без", "ещё", "еще", "был",
            "была", "было", "были", "будет", "буду", "которые", "который",
            "которая", "которое", "после", "через", "между", "перед",
        }

        words = re.findall(r'[а-яёА-ЯЁ]{4,}', content.lower())
        words = [w for w in words if w not in stop_words and len(w) > 3]

        # Берём 3 самых частых
        freq = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1

        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_words[:3]]

    def _get_expected_topics(self, segment: str) -> list[str]:
        """Возвращает ожидаемые темы для сегмента."""
        expected = {
            "zozh": ["спорт", "питание", "рецепты", "мотивация", "восстановление", "сон", "привычки"],
            "business": ["доход", "продажи", "команда", "мотивация", "инструменты", "рост"],
            "mama": ["дети", "здоровье", "питание", "энергия", "время", "баланс"],
            "student": ["учёба", "деньги", "мотивация", "подработка", "привычки"],
        }
        return expected.get(segment, ["мотивация", "продукт", "путь", "честность"])

    async def _save_state(self, segment: str, state: dict):
        """Сохраняет состояние в БД."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ChannelMemoryModel).where(ChannelMemoryModel.segment == segment)
                )
                record = result.scalar_one_or_none()

                if record:
                    record.state_data = state
                    record.updated_at = datetime.utcnow()
                else:
                    record = ChannelMemoryModel(
                        segment=segment,
                        state_data=state,
                        updated_at=datetime.utcnow(),
                    )
                    session.add(record)

                await session.commit()

        except Exception as e:
            logger.error(f"[DIRECTOR] _save_state error: {e}")


# Singleton
_memory: Optional[ChannelMemory] = None


def get_channel_memory() -> ChannelMemory:
    global _memory
    if _memory is None:
        _memory = ChannelMemory()
    return _memory
