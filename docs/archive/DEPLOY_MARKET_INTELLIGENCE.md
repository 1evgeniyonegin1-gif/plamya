# Деплой системы маркетинговой аналитики

## Быстрый старт (5 минут)

```bash
# 1. Подключиться к серверу
ssh root@194.87.86.103

# 2. Перейти в проект
cd /root/nl-international-ai-bots

# 3. Обновить код
git pull

# 4. Создать директорию для логов
mkdir -p logs

# 5. Установить systemd сервисы
sudo cp scripts/systemd/market-intelligence.service /etc/systemd/system/
sudo cp scripts/systemd/market-intelligence.timer /etc/systemd/system/
sudo systemctl daemon-reload

# 6. Включить и запустить таймер
sudo systemctl enable market-intelligence.timer
sudo systemctl start market-intelligence.timer

# 7. Проверить что работает
systemctl status market-intelligence.timer
```

## Проверка работы

```bash
# Посмотреть когда следующий запуск
systemctl list-timers market-intelligence.timer

# Запустить вручную для теста
sudo systemctl start market-intelligence.service

# Посмотреть логи
journalctl -u market-intelligence.service -n 50

# Логи в файле
tail -f /root/nl-international-ai-bots/logs/market_intelligence.log
```

## Что дальше?

После базовой установки нужно:

1. **Реализовать парсинг источников**
   - Добавить парсинг сайта NL International
   - Настроить поиск новостей конкурентов
   - Подключить RSS если доступен

2. **Протестировать интеграцию с RAG**
   - Убедиться что данные сохраняются
   - Проверить что куратор видит новые данные
   - Протестировать автоочистку старых данных

3. **Мониторинг**
   - Настроить алерты если скрипт падает
   - Добавить уведомления в Telegram о важных новостях

## Troubleshooting

### Скрипт не запускается

```bash
# Проверить права
chmod +x /root/nl-international-ai-bots/scripts/update_market_intelligence.py

# Проверить Python путь
/root/nl-international-ai-bots/venv/bin/python --version

# Запустить вручную с полным выводом
cd /root/nl-international-ai-bots
source venv/bin/activate
python scripts/update_market_intelligence.py
```

### Ошибки импорта

```bash
# Убедиться что все зависимости установлены
cd /root/nl-international-ai-bots
source venv/bin/activate
pip install -r requirements.txt
```

### Нет логов

```bash
# Создать директорию логов
mkdir -p /root/nl-international-ai-bots/logs

# Проверить права
chmod -R 755 /root/nl-international-ai-bots/logs
```

## Полная документация

См. [MARKET_INTELLIGENCE.md](./MARKET_INTELLIGENCE.md)
