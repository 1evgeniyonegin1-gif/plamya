# 🚀 Быстрая инструкция: Деплой медиа-библиотеки

**Время применения:** ~5 минут
**Требуется:** PostgreSQL, Python 3.11+

---

## Локальная машина (Windows)

### 1. Применить SQL миграцию

```powershell
# Открыть PowerShell
cd "c:\Users\mafio\OneDrive\Документы\projects\nl-international-ai-bots"

# Применить миграцию
psql -U postgres -d nl_international -f scripts/migrations/002_media_library_index.sql
```

✅ **Ожидаемый вывод:**
```
NOTICE:  ✓ Миграция завершена успешно
```

### 2. Запустить индексацию

```powershell
# Активировать venv
venv\Scripts\activate

# Запустить индексацию
python scripts/index_media_library.py
```

✅ **Ожидаемый вывод:**
```
✓ ИНДЕКСАЦИЯ ЗАВЕРШЕНА
  Файлов просканировано: 120
  Assets создано: 80
  Keywords создано: 200+
```

### 3. Тестирование

```powershell
# Быстрый тест
python -c "import asyncio; from shared.media import media_library; asyncio.run(media_library.get_stats())"
```

### 4. Перезапустить ботов

```powershell
# Остановить (Ctrl+C)
python run_bots.py
```

Проверить логи:
```
[ФОТО] ✅ MediaLibrary: найдено фото omega за 12.3ms
```

---

## VPS Сервер (Ubuntu/Debian)

### 1. Деплой на сервер

```bash
# Локально: закоммитить
git add .
git commit -m "feat: индексированная медиа-библиотека"
git push

# На VPS
ssh root@194.87.86.103
cd /root/nl-international-ai-bots
git pull
```

### 2. Применить миграцию

```bash
sudo -u postgres psql -d nl_international -f scripts/migrations/002_media_library_index.sql
```

### 3. Индексация

```bash
source venv/bin/activate
python scripts/index_media_library.py
```

### 4. Перезапуск бота

```bash
systemctl restart nl-bots

# Проверить логи
journalctl -u nl-bots -f | grep "ФОТО"
```

---

## Проверка работы

### Запрос в БД

```sql
-- Количество проиндексированных фото
SELECT asset_type, COUNT(*)
FROM content_media_assets
GROUP BY asset_type;

-- Количество keywords
SELECT COUNT(*) FROM media_keyword_index;

-- Топ-10 часто используемых
SELECT nl_products, usage_count
FROM content_media_assets
WHERE asset_type = 'product'
ORDER BY usage_count DESC
LIMIT 10;
```

### Python тест

```python
import asyncio
from shared.media import media_library

async def test():
    # Поиск
    asset = await media_library.find_by_keyword("коллаген")
    print(f"Найдено: {asset.nl_products if asset else None}")

    # Статистика
    stats = await media_library.get_stats()
    print(f"Кэш hit rate: {stats['cache_hit_rate']:.1f}%")
    print(f"Avg search: {stats['avg_search_time_ms']:.1f}ms")

asyncio.run(test())
```

---

## Откат изменений (если что-то пошло не так)

### Откатить миграцию

```sql
-- Удалить новую таблицу
DROP TABLE IF EXISTS media_keyword_index;

-- Удалить новые колонки
ALTER TABLE content_media_assets
DROP COLUMN IF EXISTS asset_type,
DROP COLUMN IF EXISTS keywords,
DROP COLUMN IF EXISTS description,
DROP COLUMN IF EXISTS nl_products,
DROP COLUMN IF EXISTS file_hash,
DROP COLUMN IF EXISTS tags;
```

### Откатить код

```bash
git revert HEAD
git push

# На VPS
git pull
systemctl restart nl-bots
```

---

## Частые проблемы

### ❌ Ошибка: "psql: command not found"

**Windows:**
```powershell
# Добавить PostgreSQL в PATH
$env:PATH += ";C:\Program Files\PostgreSQL\16\bin"
```

**Linux:**
```bash
sudo apt install postgresql-client
```

### ❌ Ошибка: "relation content_media_assets does not exist"

```bash
# Создать таблицы
python scripts/create_database.py
```

### ❌ Ошибка: "No module named 'shared.media'"

```bash
# Переустановить зависимости
pip install -r requirements.txt
```

### ❌ Поиск не находит продукты

```bash
# Пересоздать индекс
python scripts/index_media_library.py --force
```

---

## Что дальше?

После успешного деплоя:

1. ✅ Проверить логи бота на упоминания `[ФОТО] ✅ MediaLibrary`
2. ✅ Сгенерировать несколько постов типа `product`
3. ✅ Посмотреть статистику через `media_library.get_stats()`
4. ✅ Добавить чеки партнёров в `content/testimonials/checks/`

Подробная документация: [docs/MEDIA_LIBRARY_OPTIMIZATION.md](docs/MEDIA_LIBRARY_OPTIMIZATION.md)

---

## Контакты

По вопросам: @mafio (Telegram)
