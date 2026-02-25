# Подключение YandexGPT к проекту

**Дата:** 19 января 2026
**Статус:** Код готов, требуется настройка на сервере

---

## Что было сделано

### 1. Создан клиент YandexGPT
- **Файл:** `shared/ai_clients/yandexgpt_client.py`
- **Функционал:**
  - JWT авторизация через сервисный аккаунт
  - Автоматическое обновление IAM токенов (живут 12 часов)
  - Поддержка обоих моделей (lite и pro)
  - RAG интеграция (работа с базой знаний)

### 2. Обновлен генератор контента
- **Файл:** `content_manager_bot/ai/content_generator.py`
- **Изменения:**
  - Добавлена поддержка YandexGPT как основной модели
  - Автоматический выбор модели из настроек
  - Fallback на GigaChat если YandexGPT не настроен
  - GPT-4 для premium постов (если настроен)

### 3. Обновлены настройки
- **Файл:** `shared/config/settings.py`
- **Новые переменные:**
  ```python
  yandex_service_account_id: str
  yandex_key_id: str
  yandex_private_key: str
  yandex_folder_id: str
  yandex_model: str  # yandexgpt-lite или yandexgpt
  ```

### 4. Обновлены зависимости
- **Файл:** `requirements.txt`
- **Добавлено:**
  - `PyJWT==2.8.0` - для JWT авторизации
  - `cryptography==42.0.0` - для RS256 подписи

---

## Данные от Yandex Cloud

**Получены от ассистента 19 января 2026:**

```
Folder ID: b1gibb3gjf11pjbu65r3
Service Account ID: aje76dc7i20078podfrc
Key ID: ajensd96tl0d2q9fqmp9
```

**Приватный ключ:**
```
PLEASE DO NOT REMOVE THIS LINE! Yandex.Cloud SA Key ID <ajensd96tl0d2q9fqmp9>
-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDG9yxz3uQg5uvx
oz5uRjX/jjqK8dTudPyaGySnhYPuESQInTH/jI6bf246HO5dgWq43OPJRm2grKYv
3s2YJ73+MXquaRkZrF+WMgA3A+hUvjyljzkcnE/Xgt4FYldQroPv3JvVyrVINFl8
bZO3+TGT/GiRjBzdfVZ+LrP4TRYE1d9WePXwYM5Dhqr7L6RIClA+yeBWYPf+Ni+0
2m8qx2wXWvo1cg8PREDRvl0gu46hinbyQlLuo8azkSl/PMuo1kGHGKOhDpwKnHwx
M4T2j9NfCgyWvF8TXXxQXBEPFH+wzeA6GFDSIRXKGsDKi7aTHYOLymr0bclOKeY3
BvHY66ibAgMBAAECggEANx4D73lggwjVddP+GHhUvx28c/84OHKqA1rflZS0DoAr
FkPNtPhQDR2JAIpBMiAG2309kOV0uxz40KwNEkh4JnG4hZZRwL3yoN3rF1J6yvcE
P+zkKlvW9mGndaBfhddCb3ESrnAANidiXsjQMhfTNyamJSPGX0k4a64uZuub3OyR
Y9E/VI0Av4Yx5NW6qRzln+M4ieurGjBBi5zUCGF8BEVRcL8bmsuzGxyyPl47Kgo/
kxRDfSk4t5zHpigYsSjm/8yT0zHzY9xxIVNvwWhJrbFoU2RuuXhqQGLz/UR0Nuw6
X83lt8NoAi5MqoEbcuBhLivJvMAa1yLH/tF2P1YQIQKBgQDnkJKTESiYNhoSj/MA
86946p4eVGHxWoCvjh/axirWpgGTVvyb+VMpjcNiPaIywGXJ0sS4XKEr2zWO4dgF
uH0YVcjc2TqQr/bmLaqvqDLf6D+PAHQIxDW/JcGU6Yd+bPJkB/3pBkqCjHeYCl1l
wKjAxwMjwMIWu2rHFA57bRTAcQKBgQDb9fmE1/eRoTONQCoL0ZOAeI2cgwP9NUQ3
8WTzVKujR3N21IYrC8yLAe9eu+RjiEnPISglGs5c9YZ+sjXDZaiWpbEFWVoJNqLA
eX5pXd+UYfLjm/C9yEA8ZpXaxicT29RcLB7eODN5dMuaOPxUPBZs+L2FjEhHUbR1
ppEd7W9/ywKBgGwZX3NsNSkpSG6V6HjvSWEHFZ1PAxHqj9xkWpaEoAboJCAmIXKm
p53kYeuAnjFXA619yPvPsiWJBa2X3IJ/J1au5T/D4MUegAHgG6g4utcv0kvtiD13
aye6dm4PvoLUVStBV9TqbOoYrNO7MvKHR8AGp36PQ4vdHfGleUVBHMjhAoGAHOhd
y5Sqh6wc31JwdC8t6HNvgQNC8fMfLQ7/im81Q3cveI2DuIKLdjVh5RxibqZJtPwR
j5bPSi5GZ746DJz+pBXQhvhwOcfBafRNpcFdkd2xkzI6WGbJ8mY1CZSDLDv208pE
oEXYlfzAiVs15kgjVlz2Y2fFVAIr6k5iwgEjZzMCgYAvqGm74cCs+bgJ253nITeH
aPApiW5TBHE1oIFQ41ZJG59Tr7/r40KotZmk6T3quRBasFVBeVvnHYjJXR//9lwj
s5PxCrHIQcW+CXP/YV0Vf2/4JI8seQ5sip183NN0dbmbw6QEc2mWgxFv7Xiuk3xW
6V2wT8B3jQ7H6/FoCIWLRA==
-----END PRIVATE KEY-----
```

---

## Что нужно сделать на сервере

### Шаг 1: Подключиться к VPS

```bash
ssh root@194.87.86.103
cd /root/nl-international-ai-bots
```

### Шаг 2: Обновить код с GitHub

```bash
git pull origin main
```

### Шаг 3: Установить новые зависимости

```bash
pip install -r requirements.txt
```

Или только новые пакеты:
```bash
pip install PyJWT==2.8.0 cryptography==42.0.0
```

### Шаг 4: Создать файл с приватным ключом

```bash
nano /root/yandex_private_key.pem
```

**Вставь туда содержимое ключа** (всё от `PLEASE DO NOT...` до `-----END PRIVATE KEY-----` включительно), затем сохрани:
- `Ctrl+O` → Enter (сохранить)
- `Ctrl+X` (выйти)

Установи правильные права доступа:
```bash
chmod 600 /root/yandex_private_key.pem
```

### Шаг 5: Обновить .env файл

```bash
nano /root/nl-international-ai-bots/.env
```

**Добавь в конец файла:**

```env
# ===== YandexGPT Configuration =====
YANDEX_SERVICE_ACCOUNT_ID=aje76dc7i20078podfrc
YANDEX_KEY_ID=ajensd96tl0d2q9fqmp9
YANDEX_FOLDER_ID=b1gibb3gjf11pjbu65r3
YANDEX_MODEL=yandexgpt-lite

# Приватный ключ - путь к файлу
YANDEX_PRIVATE_KEY=$(cat /root/yandex_private_key.pem)

# Переключаемся на YandexGPT как основную модель
CONTENT_MANAGER_AI_MODEL=YandexGPT

# ===== Topic IDs для публикации =====
# ВАЖНО: Нужно получить реальные ID через @getmyid_bot
GROUP_ID=-1003676349853
TOPIC_PRODUCTS=???   # Зайди в тему "Продукты" и напиши /start боту @getmyid_bot
TOPIC_BUSINESS=???   # Аналогично для остальных тем
TOPIC_TRAINING=???
TOPIC_NEWS=???
TOPIC_SUCCESS=???
TOPIC_FAQ=???
```

**Сохрани файл:** Ctrl+O → Enter → Ctrl+X

### Шаг 6: Получить Topic IDs

1. Открой группу с Topics в Telegram
2. Зайди в каждую тему (Продукты, Бизнес, Обучение и т.д.)
3. Напиши `/start` боту `@getmyid_bot`
4. Скопируй ID темы (это число, например `123`)
5. Вставь ID в соответствующую строку `.env` файла

**Маппинг тем:**
```
TOPIC_PRODUCTS   → Тема "Продукты NL"
TOPIC_BUSINESS   → Тема "Бизнес-возможности"
TOPIC_TRAINING   → Тема "Обучение"
TOPIC_NEWS       → Тема "Новости"
TOPIC_SUCCESS    → Тема "Истории успеха"
TOPIC_FAQ        → Тема "Вопросы и ответы"
```

### Шаг 7: Перезапустить ботов

```bash
systemctl restart nl-bots
```

Проверить статус:
```bash
systemctl status nl-bots
```

Посмотреть логи:
```bash
journalctl -u nl-bots -f
```

В логах должно появиться:
```
ContentGenerator initialized with YandexGPT as main model
YandexGPT IAM token obtained
```

---

## Проверка работы

### 1. Проверка YandexGPT

В боте выполни команду:
```
/generate product
```

В логах должно быть:
```
YandexGPT client initialized with model: yandexgpt-lite
Using yandexgpt for post type: product
Response generated successfully from YandexGPT
```

### 2. Проверка публикации в правильный топик

После генерации и одобрения поста:
- Пост типа `product` должен попасть в тему "Продукты NL"
- Пост типа `success_story` → "Истории успеха"
- И т.д.

---

## Сравнение моделей

| Модель | Качество | Скорость | Стоимость | Лимиты |
|--------|----------|----------|-----------|--------|
| **yandexgpt-lite** | ⭐⭐⭐⭐ | Быстрая | ₽0.4/1K токенов | Бесплатно до 10K запросов/мес |
| **yandexgpt (pro)** | ⭐⭐⭐⭐⭐ | Средняя | ₽2/1K токенов | Оплата рублями |
| **GigaChat** | ⭐⭐⭐ | Средняя | Бесплатно | Токен протухает каждые 30 дней |

---

## Переключение моделей

### На yandexgpt (pro версию)

В `.env` измени:
```env
YANDEX_MODEL=yandexgpt
```

### Обратно на GigaChat

В `.env` измени:
```env
CONTENT_MANAGER_AI_MODEL=GigaChat
```

(Нужно будет обновить токен GigaChat)

---

## Troubleshooting

### Ошибка: "No AI client configured"
- Проверь что все переменные `YANDEX_*` заполнены в `.env`
- Проверь что файл `/root/yandex_private_key.pem` существует

### Ошибка: "401 Unauthorized" от YandexGPT
- Проверь что `YANDEX_FOLDER_ID` правильный
- Проверь что приватный ключ скопирован полностью
- Проверь права сервисного аккаунта в Yandex Cloud (должна быть роль `ai.languageModels.user`)

### Ошибка: "Токен истёк"
- IAM токены обновляются автоматически каждые 12 часов
- Если ошибка повторяется — проверь системное время на сервере (`date`)

### Пост публикуется не в ту тему
- Проверь что `GROUP_ID` правильный (с минусом!)
- Проверь что все `TOPIC_*` заполнены
- ID топика можно получить через `@getmyid_bot` в каждой теме группы

---

## Полезные команды

```bash
# Посмотреть переменные окружения бота
cat /root/nl-international-ai-bots/.env | grep YANDEX

# Проверить приватный ключ
cat /root/yandex_private_key.pem

# Логи в реальном времени
journalctl -u nl-bots -f

# Последние 100 строк логов
journalctl -u nl-bots -n 100 --no-pager

# Перезапустить боты
systemctl restart nl-bots

# Остановить боты
systemctl stop nl-bots

# Запустить боты
systemctl start nl-bots
```

---

## Контакты и ссылки

- **Yandex Cloud Console:** https://console.yandex.cloud
- **YandexGPT Documentation:** https://cloud.yandex.ru/docs/foundation-models/
- **VPS сервер:** 194.87.86.103
- **Telegram группа:** -1003676349853

---

**Создано:** 19 января 2026
**Автор:** Claude Sonnet 4.5
**Статус:** Готово к деплою
