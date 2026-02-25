# ✅ Чек-лист проверки медиа-библиотеки

Перед применением на продакшн проверьте все пункты.

## 1. Синтаксис Python (локально)

```bash
cd "c:\Users\mafio\OneDrive\Документы\projects\nl-international-ai-bots"

# Проверка синтаксиса
python -m py_compile shared/media/media_library.py
python -m py_compile scripts/index_media_library.py
python -m py_compile content_manager_bot/database/models.py
python -m py_compile content_manager_bot/ai/content_generator.py
```

**Ожидаемый результат:** Нет вывода (успех)

## 2. Импорты

```python
# Проверка что модули импортируются
python -c "from shared.media import media_library; print('✓ MediaLibrary OK')"
python -c "from content_manager_bot.database.models import MediaAsset, MediaKeywordIndex; print('✓ Models OK')"
```

**Ожидаемый результат:**
```
✓ MediaLibrary OK
✓ Models OK
```

## 3. SQL миграция (dry-run)

```bash
# Проверка синтаксиса SQL (без применения)
psql -U postgres -d nl_international --dry-run -f scripts/migrations/002_media_library_index.sql 2>&1 | head -20
```

**Что проверить:**
- [ ] Нет синтаксических ошибок
- [ ] Используется `IF NOT EXISTS` (безопасность)
- [ ] Все индексы названы корректно

## 4. Структура папок

```bash
# Проверка что папки созданы
ls content/testimonials/
ls shared/media/
ls scripts/migrations/
```

**Ожидаемый результат:**
```
content/testimonials/
  ├── checks/
  ├── before_after/
  ├── stories/
  └── README.md

shared/media/
  ├── __init__.py
  └── media_library.py

scripts/migrations/
  └── 002_media_library_index.sql
```

## 5. Документация

**Проверить что существуют:**
- [ ] `DEPLOYMENT_MEDIA_LIBRARY.md` (инструкция деплоя)
- [ ] `docs/MEDIA_LIBRARY_OPTIMIZATION.md` (полная документация)
- [ ] `docs/CHANGELOG_2026_01_26_MEDIA_LIBRARY.md` (changelog)
- [ ] `content/testimonials/README.md` (инструкция testimonials)

## 6. Миграция БД (локально)

```bash
# BACKUP БАЗЫ ПЕРЕД ПРИМЕНЕНИЕМ!
pg_dump -U postgres nl_international > backup_before_migration.sql

# Применить миграцию
psql -U postgres -d nl_international -f scripts/migrations/002_media_library_index.sql
```

**Ожидаемый вывод:**
```
NOTICE:  ✓ Миграция завершена успешно
NOTICE:    - Всего медиа-активов: 0
NOTICE:    - Всего keywords в индексе: 0
NOTICE:  ✓ Дубликаты не найдены
```

**Проверка в БД:**
```sql
-- Проверить что колонки добавлены
\d content_media_assets

-- Должны быть новые колонки:
-- asset_type, keywords, description, nl_products, file_hash, tags

-- Проверить новую таблицу
\d media_keyword_index

-- Должна быть таблица с полями:
-- id, keyword, normalized_keyword, asset_id, priority
```

## 7. Индексация (локально)

```bash
# Сначала dry-run
python scripts/index_media_library.py --dry-run

# Если всё OK, реальная индексация
python scripts/index_media_library.py
```

**Ожидаемая статистика:**
```
✓ ИНДЕКСАЦИЯ ЗАВЕРШЕНА
  Файлов просканировано: 100-150
  Assets создано: 80-100
  Keywords создано: 200+
  Дубликатов найдено: 30-50
  Ошибок: 0
```

**Проверка в БД:**
```sql
-- Количество assets по типам
SELECT asset_type, COUNT(*)
FROM content_media_assets
GROUP BY asset_type;

-- Ожидаемый результат:
-- product | 80-100

-- Количество keywords
SELECT COUNT(*) FROM media_keyword_index;

-- Ожидаемый результат: 200+

-- Топ-10 продуктов
SELECT nl_products, COUNT(*) as cnt
FROM content_media_assets
WHERE asset_type = 'product'
GROUP BY nl_products
ORDER BY cnt DESC
LIMIT 10;
```

## 8. Тестирование API

```python
import asyncio
from shared.media import media_library

async def test():
    # Поиск по keyword
    asset = await media_library.find_by_keyword("коллаген")
    assert asset is not None, "Коллаген не найден!"
    print(f"✓ find_by_keyword: {asset.nl_products}")

    # Поиск в тексте
    asset = await media_library.find_in_text("Попробуй лимф гьян для детокса")
    assert asset is not None, "Лимф гьян не найден!"
    print(f"✓ find_in_text: {asset.nl_products}")

    # Статистика
    stats = await media_library.get_stats()
    print(f"✓ Статистика:")
    print(f"  Assets: {stats['assets']}")
    print(f"  Keywords: {stats['total_keywords']}")
    print(f"  Cache hit rate: {stats['cache_hit_rate']:.1f}%")
    print(f"  Avg search time: {stats['avg_search_time_ms']:.1f}ms")

asyncio.run(test())
```

**Ожидаемый результат:**
```
✓ find_by_keyword: ['collagen']
✓ find_in_text: ['lymph_gyan']
✓ Статистика:
  Assets: {'product': 85}
  Keywords: 215
  Cache hit rate: 50.0%
  Avg search time: 15.3ms
```

## 9. Интеграция в ContentGenerator

```bash
# Запустить бота локально
venv\Scripts\activate
python run_bots.py
```

**В логах искать:**
```
[ФОТО] ✅ MediaLibrary: найдено фото omega за 12.3ms
```

**Проверка:**
- [ ] Бот запускается без ошибок
- [ ] В логах видны `[ФОТО] ✅ MediaLibrary`
- [ ] Fallback на ProductReferenceManager работает при ошибках

## 10. Производительность

```python
import time
import asyncio
from shared.media import media_library

async def benchmark():
    keywords = ["коллаген", "омега", "3d slim", "лимф гьян", "happy smile"]

    # Холодный старт
    await media_library.clear_cache()
    start = time.time()
    for kw in keywords:
        await media_library.find_by_keyword(kw)
    cold_time = (time.time() - start) * 1000 / len(keywords)

    # Горячий кэш
    start = time.time()
    for kw in keywords:
        await media_library.find_by_keyword(kw)
    hot_time = (time.time() - start) * 1000 / len(keywords)

    print(f"Холодный кэш: {cold_time:.1f}ms")
    print(f"Горячий кэш: {hot_time:.1f}ms")
    print(f"Улучшение: {cold_time / hot_time:.1f}x")

asyncio.run(benchmark())
```

**Целевые показатели:**
- Холодный кэш: < 20ms ✅
- Горячий кэш: < 5ms ✅
- Улучшение: > 3x ✅

## 11. Откат (если что-то пошло не так)

```bash
# Восстановить БД из backup
psql -U postgres -d nl_international < backup_before_migration.sql

# Откатить код
git diff HEAD~1 HEAD

# Если нужен полный откат
git revert HEAD
```

## 12. Деплой на VPS

**Только после успешной проверки всех пунктов выше!**

```bash
# Локально
git add .
git commit -m "feat: indexed media library (< 20ms search)"
git push

# На VPS
ssh root@194.87.86.103
cd /root/nl-international-ai-bots

# BACKUP!
sudo -u postgres pg_dump nl_international > ~/backup_$(date +%Y%m%d_%H%M%S).sql

# Деплой
git pull
sudo -u postgres psql -d nl_international -f scripts/migrations/002_media_library_index.sql
source venv/bin/activate
python scripts/index_media_library.py
systemctl restart nl-bots

# Проверить логи
journalctl -u nl-bots -f | grep "ФОТО"
```

## ✅ Финальный чек-лист

Перед продакшн деплоем убедитесь что:

- [ ] Все Python файлы компилируются без ошибок
- [ ] Миграция применяется без ошибок (локально)
- [ ] Индексация завершается успешно (100+ assets)
- [ ] API тесты проходят (find_by_keyword, find_in_text)
- [ ] Производительность < 20ms (холодный кэш)
- [ ] Бот запускается и находит фото продуктов
- [ ] Логи показывают `[ФОТО] ✅ MediaLibrary`
- [ ] Создан BACKUP базы данных
- [ ] Документация обновлена (CLAUDE.md)

**Если хотя бы один пункт не пройден — НЕ деплоить на VPS!**

## Контакты

По вопросам: @mafio (Telegram)
