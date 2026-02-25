# Деплой Traffic Engine

## Быстрый деплой на VPS

### 1. Обновить код

```bash
ssh root@194.87.86.103

cd /root/nl-international-ai-bots
git pull
```

### 2. Применить миграцию БД

```bash
psql -U postgres -d nl_international -f scripts/migrations/007_traffic_accounts_and_warmup.sql
```

### 3. Перезапустить ботов

```bash
systemctl restart nl-bots
journalctl -u nl-bots -f  # проверить логи
```

---

## Что добавлено

### 1. Напоминание о 70 PV в онбординге

Теперь День 1 требует заказа на 70 PV (не просто "1 продукт").

**Напоминания:**
- 4 часа: "Ты уже заказал стартовый набор на 70 PV?"
- 12 часов: "Без заказа на 70 PV партнёрство не активно"
- 24 часа: "Ты заказал 70 PV?"
- 48 часов: "Что застопорило?"
- 7 дней: "Последняя попытка"

### 2. Система прогрева аккаунтов (`warmup/`)

30-дневный план прогрева:

| Фаза | Дни | Описание |
|------|-----|----------|
| 1 | 1-7 | Базовый траст (подписки, реакции) |
| 2 | 8-14 | Наращивание (сообщения, комментарии) |
| 3 | 15-21 | Контент (создание каналов, посты) |
| 4 | 22-30 | Полноценная работа |

**Использование:**
```python
from traffic_engine.warmup import WarmupScheduler

scheduler = WarmupScheduler()
await scheduler.start_warmup(account_id=1)
status = await scheduler.get_warmup_status(account_id=1)
```

### 3. Автопостинг (`posting/`)

**Rate Limiter** — защита от банов:
- День 1-7: max 0-2 поста/день, задержка 45-120 сек
- День 22-30: max 5-10 постов/день, задержка 30 сек

**Content Queue** — очередь контента:
```python
from traffic_engine.posting import ContentQueue, AutoPoster

queue = ContentQueue()
await queue.add_post(channel_id=1, post_type="product", content="...", scheduled_at=datetime)

poster = AutoPoster()
await poster.start()
```

### 4. Мониторинг (`monitoring/`)

**Ban Detector** — обнаружение банов:
- Проверка через @SpamBot раз в день
- Алерты админу при бане
- Автозамена на backup аккаунт

**Metrics Collector** — метрики:
- Подписчики, просмотры, клики
- Конверсии по каналам и сегментам
- Ежедневные отчёты

**Alert Manager** — алерты в Telegram:
```python
from traffic_engine.monitoring import AlertManager

alerts = AlertManager(admin_ids=[756877849])
await alerts.alert_account_banned(account_id=1, reason="SpamBot detected")
```

---

## Новые таблицы БД

| Таблица | Описание |
|---------|----------|
| `traffic_accounts` | Telegram аккаунты с прокси и статусом прогрева |
| `traffic_channels` | Каналы привязанные к аккаунтам |
| `traffic_content_schedule` | Очередь контента для автопостинга |
| `warmup_logs` | Логи прогревочных действий |
| `warmup_daily_limits` | Дефолтные лимиты по фазам |
| `producer_agents` | Агенты-продюсеры по сегментам |

---

## Следующие шаги

1. **Применить миграцию на VPS**
2. **Купить SIM-карты** для новых аккаунтов
3. **Настроить прокси** (резидентные или мобильные)
4. **Создать первый тестовый канал** через `setup_nl_account.py`
5. **Запустить прогрев** через WarmupScheduler

---

*Создано: 3 февраля 2026*
