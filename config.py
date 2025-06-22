import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# PostgreSQL connection parameters
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "telegram_parser")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

# Target channel ID for forwarding messages
TARGET_CHANNEL_ID = os.getenv("TARGET_CHANNEL_ID")

# Checking interval in minutes
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "3"))

# Signature for forwarded messages
SIGNATURE = "#Найдено_по_запросу" 