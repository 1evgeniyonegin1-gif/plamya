"""
ReflectionEngine — обучение на правках и отклонениях.

Вдохновлено: LangChain Social Media Agent reflection system.

Когда админ отклоняет/редактирует пост:
1. Логируем в channel_memory.rejection_log
2. Каждые 5 отклонений → AI формулирует новые правила
3. Правила попадают в промпт планировщика
"""
import json
from typing import Optional

from loguru import logger

from shared.ai_clients.deepseek_client import DeepseekClient
from content_manager_bot.director.channel_memory import get_channel_memory


class ReflectionEngine:
    """Учится на правках и отклонениях постов."""

    # Порог: каждые N отклонений запускаем анализ
    REFLECTION_THRESHOLD = 5

    def __init__(self):
        self._ai_client: Optional[DeepseekClient] = None

    def _get_ai(self) -> DeepseekClient:
        if self._ai_client is None:
            self._ai_client = DeepseekClient()
        return self._ai_client

    async def on_reject(self, segment: str, content: str, reason: str, post_type: str):
        """Вызывается когда админ отклоняет пост."""
        memory = get_channel_memory()
        await memory.add_rejection(segment, content, "reject", reason, post_type)
        await self._maybe_reflect(segment)

    async def on_edit(self, segment: str, original: str, edited: str, post_type: str):
        """Вызывается когда админ редактирует пост."""
        # Вычисляем diff
        diff = self._compute_diff(original, edited)
        memory = get_channel_memory()
        await memory.add_rejection(segment, original, "edit", diff, post_type)
        await self._maybe_reflect(segment)

    async def _maybe_reflect(self, segment: str):
        """Запускает рефлексию если накопилось достаточно данных."""
        memory = get_channel_memory()
        state = await memory.get_state(segment)

        log = state.get("rejection_log", [])
        existing_rules = state.get("reflection_rules", [])

        # Считаем неотрефлексированные
        unreflected = len(log) - (len(existing_rules) * self.REFLECTION_THRESHOLD)

        if unreflected < self.REFLECTION_THRESHOLD:
            return

        logger.info(f"[DIRECTOR] Running reflection for {segment} ({len(log)} rejections)")
        await self._run_reflection(segment, log[-self.REFLECTION_THRESHOLD:], existing_rules)

    async def _run_reflection(self, segment: str, recent_rejections: list, existing_rules: list):
        """AI анализирует отклонения и формулирует правила."""
        try:
            rejections_text = "\n\n".join([
                f"#{i+1} ({r.get('action', 'reject')}, тип: {r.get('post_type', '?')}):\n"
                f"Текст: {r.get('original_preview', '...')}\n"
                f"Причина: {r.get('reason', 'не указана')}"
                for i, r in enumerate(recent_rejections)
            ])

            rules_text = "\n".join(f"- {r}" for r in existing_rules) if existing_rules else "Пока нет"

            prompt = f"""Вот {len(recent_rejections)} последних отклонений/правок постов:

{rejections_text}

Текущие правила генерации:
{rules_text}

Какие паттерны ты видишь? Сформулируй 2-3 НОВЫХ правила
которые предотвратят подобные отклонения.

Ответь СТРОГО JSON (без markdown): {{"new_rules": ["правило 1", "правило 2"]}}"""

            ai = self._get_ai()
            response = await ai.generate_response(
                system_prompt="Ты AI-аналитик контента. Формулируешь правила на основе паттернов отклонений. Отвечаешь JSON.",
                user_message=prompt,
                temperature=0.7,
                max_tokens=400,
            )

            # Парсим
            new_rules = self._parse_rules(response)
            if not new_rules:
                logger.warning(f"[DIRECTOR] Failed to parse reflection rules")
                return

            # Объединяем с существующими
            all_rules = existing_rules + new_rules
            # Max 10 правил, новые заменяют старые
            all_rules = all_rules[-10:]

            # Сохраняем
            memory = get_channel_memory()
            await memory.set_reflection_rules(segment, all_rules)

            logger.info(f"[DIRECTOR] Reflection complete: {len(new_rules)} new rules → total {len(all_rules)}")

        except Exception as e:
            logger.error(f"[DIRECTOR] Reflection error: {e}")

    def _compute_diff(self, original: str, edited: str) -> str:
        """Вычисляет краткое описание правки."""
        if len(edited) < len(original) * 0.5:
            return "Сокращено больше чем вдвое"
        if len(edited) > len(original) * 1.5:
            return "Значительно расширено"

        # Простое сравнение: что добавлено/убрано
        orig_words = set(original.lower().split())
        edit_words = set(edited.lower().split())

        removed = orig_words - edit_words
        added = edit_words - orig_words

        parts = []
        if removed:
            parts.append(f"Убрано: {', '.join(list(removed)[:5])}")
        if added:
            parts.append(f"Добавлено: {', '.join(list(added)[:5])}")

        return "; ".join(parts) if parts else "Незначительные правки"

    def _parse_rules(self, response: str) -> Optional[list]:
        """Парсит правила из ответа AI."""
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
            rules = data.get("new_rules", [])

            if isinstance(rules, list) and all(isinstance(r, str) for r in rules):
                return rules

            return None

        except (json.JSONDecodeError, ValueError):
            return None


# Singleton
_engine: Optional[ReflectionEngine] = None


def get_reflection_engine() -> ReflectionEngine:
    global _engine
    if _engine is None:
        _engine = ReflectionEngine()
    return _engine
