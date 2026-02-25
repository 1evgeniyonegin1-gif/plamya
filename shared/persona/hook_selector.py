"""
Селектор hook'ов (цепляющих фраз).

Выбирает подходящий hook на основе:
- Версии персоны
- Категории настроения
- Типа поста/сообщения

Используется в:
- AI-Контент-Менеджер: начало постов
- AI-Куратор: начало ответов в чате
"""

import random
from typing import Optional
from .hook_templates import HOOK_TEMPLATES


class HookSelector:
    """Выбирает подходящий hook для контента"""

    def __init__(self):
        # Отслеживание недавно использованных hooks (чтобы не повторять)
        self.recent_hooks: list[str] = []
        self.max_recent = 10  # Хранить последние 10 hooks

    def select_hook(
        self,
        persona_version: str,
        mood_category: Optional[str] = None,
        post_type: Optional[str] = None,
        avoid_recent: bool = True
    ) -> str:
        """
        Выбирает hook на основе критериев.

        Args:
            persona_version: Версия персоны (expert, friend, rebel, etc.)
            mood_category: Категория настроения (joy, anger, etc.)
            post_type: Тип поста (product, motivation, etc.)
            avoid_recent: Избегать недавно использованных

        Returns:
            str: Текст hook'а
        """
        # Получить все hooks для версии персоны
        persona_hooks = HOOK_TEMPLATES.get(persona_version, HOOK_TEMPLATES["friend"])

        # Фильтровать по критериям
        suitable_hooks = self._filter_hooks(
            persona_hooks,
            mood_category=mood_category,
            post_type=post_type
        )

        # Если нет подходящих — вернуть все hooks версии
        if not suitable_hooks:
            suitable_hooks = persona_hooks

        # Исключить недавно использованные
        if avoid_recent and self.recent_hooks:
            suitable_hooks = [
                h for h in suitable_hooks
                if h["template"] not in self.recent_hooks
            ]

            # Если после исключения не осталось — использовать все
            if not suitable_hooks:
                suitable_hooks = persona_hooks

        # Случайный выбор
        selected_hook = random.choice(suitable_hooks)

        # Добавить в недавние
        self._add_to_recent(selected_hook["template"])

        # Вернуть шаблон (без заполнения переменных)
        return selected_hook["template"]

    def select_hook_with_variables(
        self,
        persona_version: str,
        variables: dict[str, str],
        mood_category: Optional[str] = None,
        post_type: Optional[str] = None,
        avoid_recent: bool = True
    ) -> str:
        """
        Выбирает hook и заполняет переменные.

        Args:
            persona_version: Версия персоны
            variables: Словарь переменных {name: value}
            mood_category: Категория настроения
            post_type: Тип поста
            avoid_recent: Избегать недавно использованных

        Returns:
            str: Hook с заполненными переменными
        """
        template = self.select_hook(
            persona_version=persona_version,
            mood_category=mood_category,
            post_type=post_type,
            avoid_recent=avoid_recent
        )

        return self.fill_variables(template, variables)

    def _filter_hooks(
        self,
        hooks: list[dict],
        mood_category: Optional[str] = None,
        post_type: Optional[str] = None
    ) -> list[dict]:
        """
        Фильтрует hooks по критериям.

        Args:
            hooks: Список hooks
            mood_category: Категория настроения
            post_type: Тип поста

        Returns:
            list[dict]: Отфильтрованные hooks
        """
        filtered = hooks

        # Фильтр по категории настроения
        if mood_category:
            filtered = [
                h for h in filtered
                if not h.get("mood_categories") or mood_category in h["mood_categories"]
            ]

        # Фильтр по типу поста
        if post_type:
            filtered = [
                h for h in filtered
                if not h.get("post_types") or post_type in h["post_types"]
            ]

        return filtered

    def _add_to_recent(self, hook_template: str):
        """Добавляет hook в список недавно использованных"""
        self.recent_hooks.append(hook_template)

        # Ограничить размер списка
        if len(self.recent_hooks) > self.max_recent:
            self.recent_hooks = self.recent_hooks[-self.max_recent:]

    @staticmethod
    def fill_variables(hook_template: str, variables: dict[str, str]) -> str:
        """
        Заполняет переменные в шаблоне hook'а.

        Args:
            hook_template: Шаблон hook'а
            variables: Словарь переменных {name: value}

        Returns:
            str: Hook с заполненными переменными

        Example:
            >>> HookSelector.fill_variables(
            ...     "{percentage}% людей не знают, что",
            ...     {"percentage": "87"}
            ... )
            "87% людей не знают, что"
        """
        result = hook_template
        for var_name, var_value in variables.items():
            result = result.replace(f"{{{var_name}}}", str(var_value))
        return result

    def clear_recent(self):
        """Очищает список недавно использованных hooks"""
        self.recent_hooks = []

    def get_hooks_stats(self) -> dict:
        """
        Возвращает статистику по hooks.

        Returns:
            dict: Статистика (количество по версиям)
        """
        return {
            persona: len(hooks)
            for persona, hooks in HOOK_TEMPLATES.items()
        }

    def get_hooks_for_persona(self, persona_version: str) -> list[str]:
        """
        Возвращает все шаблоны hooks для версии персоны.

        Args:
            persona_version: Версия персоны

        Returns:
            list[str]: Список шаблонов
        """
        hooks = HOOK_TEMPLATES.get(persona_version, HOOK_TEMPLATES["friend"])
        return [h["template"] for h in hooks]
