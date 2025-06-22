# Настройка Telethon для доступа к каналам

Для мониторинга каналов, в которых бот не является участником, необходимо использовать клиентский API Telegram (Telethon). Вот пошаговая инструкция:

## 1. Получите API ID и API Hash

1. Перейдите на сайт https://my.telegram.org/auth
2. Войдите в свой аккаунт Telegram
3. Перейдите в раздел "API development tools"
4. Создайте новое приложение, заполнив необходимые поля:
   - App title: Telegram Parser Bot
   - Short name: tg_parser_bot
   - Platform: Desktop
   - Description: Bot for parsing messages from channels
5. После создания приложения вы получите `api_id` и `api_hash`

## 2. Настройте файл .env

Создайте файл `.env` в корне проекта и добавьте следующие параметры:

```
# Telegram Bot Token
BOT_TOKEN=ваш_токен_бота

# Target channel ID for forwarding messages
TARGET_CHANNEL_ID=ид_целевого_канала

# Checking interval in minutes
CHECK_INTERVAL=3

# PostgreSQL connection parameters
DB_HOST=localhost
DB_PORT=5432
DB_NAME=telegram_parser
DB_USER=postgres
DB_PASSWORD=password

# Telethon API credentials (required for accessing private channels)
TELEGRAM_API_ID=ваш_api_id
TELEGRAM_API_HASH=ваш_api_hash
TELEGRAM_PHONE=ваш_номер_телефона

# Anti-ban protection parameters (защита от блокировки)
MAX_CHANNELS_PER_RUN=20
DELAY_BETWEEN_CHANNELS=2.0
MAX_MESSAGES_PER_CHANNEL=20
JITTER=0.5
TELETHON_SESSION_NAME=telegram_parser_session
```

Замените значения на свои:
- `ваш_api_id` - числовое значение API ID, полученное на шаге 1
- `ваш_api_hash` - строковое значение API Hash, полученное на шаге 1
- `ваш_номер_телефона` - номер телефона в международном формате (например, +79123456789)

## 3. Авторизуйте Telethon

1. Запустите бота
2. В интерфейсе бота выберите "📢 Каналы" -> "🔐 Авторизовать Telethon"
3. Следуйте инструкциям для ввода кода подтверждения, который придет в Telegram

## 4. Добавьте каналы для мониторинга

После авторизации Telethon вы сможете добавлять каналы для мониторинга:
- Публичные каналы: добавляйте через @username
- Приватные каналы: вы должны быть участником канала, чтобы мониторить его

## Параметры защиты от блокировки

В файле `.env` вы можете настроить параметры защиты от блокировки:

| Параметр | Описание | Рекомендуемое значение |
|----------|----------|------------------------|
| MAX_CHANNELS_PER_RUN | Максимальное количество каналов, проверяемых за один запуск | 20 |
| DELAY_BETWEEN_CHANNELS | Задержка между проверками каналов (в секундах) | 2.0 |
| MAX_MESSAGES_PER_CHANNEL | Максимальное количество сообщений, получаемых из канала за один запрос | 20 |
| JITTER | Случайное отклонение для задержек (±%) | 0.5 |
| CHECK_INTERVAL | Интервал между проверками каналов (в минутах) | 3 |

### Рекомендации по настройке:

1. **Для небольшого количества каналов (до 10):**
   ```
   MAX_CHANNELS_PER_RUN=10
   DELAY_BETWEEN_CHANNELS=1.5
   MAX_MESSAGES_PER_CHANNEL=20
   CHECK_INTERVAL=3
   ```

2. **Для среднего количества каналов (10-30):**
   ```
   MAX_CHANNELS_PER_RUN=20
   DELAY_BETWEEN_CHANNELS=2.0
   MAX_MESSAGES_PER_CHANNEL=15
   CHECK_INTERVAL=5
   ```

3. **Для большого количества каналов (более 30):**
   ```
   MAX_CHANNELS_PER_RUN=20
   DELAY_BETWEEN_CHANNELS=3.0
   MAX_MESSAGES_PER_CHANNEL=10
   CHECK_INTERVAL=10
   ```

## Решение проблем

### Ошибка "Pool timeout"

Если вы видите ошибку "Pool timeout", это означает, что слишком много одновременных запросов к API Telegram. Решения:
- Увеличьте интервал проверки (CHECK_INTERVAL)
- Уменьшите количество мониторимых каналов
- Разделите каналы между несколькими экземплярами бота

### Ошибка доступа к каналу

Если бот не может получить доступ к каналу:
1. Убедитесь, что Telethon авторизован
2. Проверьте, что вы являетесь участником этого канала
3. Для публичных каналов используйте формат @username вместо числового ID

### Ошибка FloodWaitError

Если вы видите ошибку "FloodWaitError", это означает, что Telegram обнаружил слишком много запросов и временно ограничил доступ. Бот автоматически обработает эту ошибку и будет ждать указанное время, но вам следует:
- Увеличить значение DELAY_BETWEEN_CHANNELS
- Уменьшить MAX_CHANNELS_PER_RUN
- Увеличить CHECK_INTERVAL 