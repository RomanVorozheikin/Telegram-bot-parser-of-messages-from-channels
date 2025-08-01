# Настройка "боевого режима" для мониторинга каналов

"Боевой режим" позволяет боту мониторить каждое новое сообщение в каналах в реальном времени. Для этого необходимо:

## 1. Авторизовать Telethon клиент

Telethon позволяет получать доступ к каналам от имени пользователя, а не бота. Это необходимо для мониторинга каналов, в которых бот не является участником.

1. Создайте файл `.env` в корне проекта и добавьте следующие параметры:

```
# Telegram Bot Token
BOT_TOKEN=ваш_токен_бота

# Target channel ID for forwarding messages
TARGET_CHANNEL_ID=ид_целевого_канала

# Checking interval in minutes (для боевого режима рекомендуется 2-3 минуты)
CHECK_INTERVAL=2

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
MAX_CHANNELS_PER_RUN=15
DELAY_BETWEEN_CHANNELS=2.5
MAX_MESSAGES_PER_CHANNEL=15
JITTER=0.5
TELETHON_SESSION_NAME=telegram_parser_session
```

2. Запустите скрипт авторизации Telethon:
```
authorize_telethon.bat
```

3. Следуйте инструкциям в консоли для ввода кода подтверждения

## 2. Добавьте каналы для мониторинга

После авторизации Telethon вы можете добавить каналы для мониторинга через интерфейс бота:

1. Запустите бота:
```
start_bot.bat
```

2. В интерфейсе бота выберите "📢 Каналы" -> "🔍 Показать доступные каналы"

3. Бот покажет список доступных вам каналов. Добавьте нужные каналы, нажав на соответствующие кнопки.

## 3. Настройте параметры боевого режима

Для эффективного мониторинга в реальном времени с защитой от блокировки:

1. Установите оптимальные параметры в файле `.env`:
```
# Более частые проверки, но с ограничениями для защиты от блокировки
CHECK_INTERVAL=2
MAX_CHANNELS_PER_RUN=15
DELAY_BETWEEN_CHANNELS=2.5
MAX_MESSAGES_PER_CHANNEL=15
```

2. Добавьте ключевые слова через интерфейс бота:
   - Выберите "🔑 Ключ-слова" -> "➕ Добавить ключевое слово"
   - Добавьте нужные ключевые слова

3. Добавьте стоп-слова для фильтрации ненужных сообщений:
   - Выберите "🚫 Стоп-слова" -> "➕ Добавить стоп-слово"
   - Добавьте нужные стоп-слова

## 4. Запустите бота в боевом режиме

1. Запустите бота:
```
start_bot.bat
```

2. Убедитесь, что бот активен (должна быть кнопка "🟢 Работает")

3. Бот будет проверять каналы каждые 2 минуты и пересылать сообщения, содержащие ключевые слова, в целевой канал

## Безопасные настройки для боевого режима

Для минимизации риска блокировки аккаунта при интенсивном мониторинге используйте эти рекомендации:

### Для небольшого количества каналов (5-10):
```
CHECK_INTERVAL=2
MAX_CHANNELS_PER_RUN=10
DELAY_BETWEEN_CHANNELS=1.5
MAX_MESSAGES_PER_CHANNEL=15
```

### Для среднего количества каналов (10-20):
```
CHECK_INTERVAL=3
MAX_CHANNELS_PER_RUN=15
DELAY_BETWEEN_CHANNELS=2.5
MAX_MESSAGES_PER_CHANNEL=10
```

### Для большого количества каналов (более 20):
```
CHECK_INTERVAL=5
MAX_CHANNELS_PER_RUN=20
DELAY_BETWEEN_CHANNELS=3.0
MAX_MESSAGES_PER_CHANNEL=5
```

## Решение проблем

### Бот не видит сообщения в каналах

Если бот не может получать сообщения из каналов:

1. Убедитесь, что Telethon авторизован:
   - Запустите `authorize_telethon.bat` и проверьте, что авторизация успешна

2. Проверьте, что вы являетесь участником канала:
   - Telethon может мониторить только те каналы, в которых вы являетесь участником

3. Для публичных каналов используйте формат @username:
   - Например: @channel_name вместо числового ID

### Бот не пересылает сообщения

Если бот видит каналы, но не пересылает сообщения:

1. Убедитесь, что добавлены ключевые слова:
   - Выберите "🔑 Ключ-слова" в интерфейсе бота и проверьте список

2. Проверьте, что указан правильный целевой канал:
   - Параметр TARGET_CHANNEL_ID в файле .env

3. Убедитесь, что бот имеет права администратора в целевом канале

### Ошибки превышения лимитов API (FloodWaitError)

Если вы видите в логах ошибки FloodWaitError:

1. Увеличьте интервал между проверками (CHECK_INTERVAL)
2. Увеличьте задержку между каналами (DELAY_BETWEEN_CHANNELS)
3. Уменьшите количество каналов (MAX_CHANNELS_PER_RUN)
4. Используйте отдельный аккаунт для бота, а не ваш основной 