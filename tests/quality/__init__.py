"""
Система качественного тестирования ботов NL International.

Проверяет:
- AI-Куратор: recurring characters, фирменные фразы, эмоциональные горки
- Контент-Менеджер: новые типы постов, cliffhangers, hooks

Запуск:
    python -m tests.quality.run --all
    python -m tests.quality.run --curator --limit 10
    python -m tests.quality.run --content --category "series"
"""
