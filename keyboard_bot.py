#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Telegram Bot для парсинга сообщений из каналов с использованием клавиатуры
"""

import os
import sys
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from database import Database
from scheduler import MessageScheduler

# Проверяем наличие Telethon
try:
    from telethon import TelegramClient, errors
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False
    print("ВНИМАНИЕ: Библиотека Telethon не установлена. Функционал доступа к каналам без бота будет ограничен.")
    print("Для установки выполните: pip install telethon")

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем настройки из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHANNEL_ID = os.getenv("TARGET_CHANNEL_ID")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "3"))

# Получаем настройки Telethon
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE")

if not BOT_TOKEN:
    logger.error("Не указан токен бота в переменных окружения (BOT_TOKEN)")
    sys.exit(1)

# Инициализация базы данных
db = Database()

# Глобальная переменная для планировщика
scheduler = None

# Глобальная переменная для Telethon клиента
telethon_client = None

# Клавиатуры
def get_main_keyboard():
    """Возвращает основную клавиатуру."""
    keyboard = [
        [KeyboardButton("🔑 Ключ-слова"), KeyboardButton("🚫 Стоп-слова")],
        [KeyboardButton("📢 Каналы"), KeyboardButton("👥 Группы"), KeyboardButton("💬 Диалоги")],
        [KeyboardButton("🟢 Игнор одинаковых сообщений")],
        [KeyboardButton("👤 Чёрный список 👤")],
        [KeyboardButton("📣 Чат для уведомлений 📣")],
        [KeyboardButton("⬅️ Назад ⬅️")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_status_keyboard(is_running):
    """Возвращает клавиатуру со статусом."""
    status = "🟢 Работает" if is_running else "🔴 Остановлен"
    keyboard = [
        [KeyboardButton(status)],
        [KeyboardButton("📢 Каналы"), KeyboardButton("👥 Группы"), KeyboardButton("💬 Диалоги")],
        [KeyboardButton("🟢 Игнор одинаковых сообщений")],
        [KeyboardButton("🔑 Ключ-слова"), KeyboardButton("🚫 Стоп-слова")],
        [KeyboardButton("👤 Чёрный список 👤")],
        [KeyboardButton("📣 Чат для уведомлений 📣")],
        [KeyboardButton("⬅️ Назад ⬅️")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_keywords_keyboard():
    """Возвращает клавиатуру для управления ключевыми словами."""
    keyboard = [
        [KeyboardButton("➕ Добавить ключевое слово")],
        [KeyboardButton("❌ Удалить все слова ❌")],
        [KeyboardButton("🔄 Сортировать по дате 🔄")],
        [KeyboardButton("📋 Копировать все слова 📋")],
        [KeyboardButton("⬅️ Назад ⬅️")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_stopwords_keyboard():
    """Возвращает клавиатуру для управления стоп-словами."""
    keyboard = [
        [KeyboardButton("➕ Добавить стоп-слово")],
        [KeyboardButton("❌ Удалить все слова ❌")],
        [KeyboardButton("🔄 Сортировать по дате 🔄")],
        [KeyboardButton("📋 Копировать все слова 📋")],
        [KeyboardButton("⬅️ Назад ⬅️")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_channels_keyboard():
    """Возвращает клавиатуру для управления каналами."""
    keyboard = [
        [KeyboardButton("➕ Добавить канал"), KeyboardButton("📋 Список каналов")],
        [KeyboardButton("🔍 Показать доступные каналы")],
        [KeyboardButton("🔐 Авторизовать Telethon")],
        [KeyboardButton("⬅️ Назад ⬅️")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Обработчики команд и сообщений
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    await update.message.reply_text(
        "👋 Привет! Я бот для мониторинга Telegram каналов.\n\n"
        "Я буду проверять каналы на наличие ключевых слов и пересылать "
        "подходящие сообщения в указанный канал.",
        reply_markup=get_status_keyboard(scheduler and scheduler.is_running)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    help_text = (
        "📋 Список доступных команд:\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n"
        "/status - Показать текущий статус бота\n\n"
        "Также вы можете использовать кнопки на клавиатуре для управления ботом."
    )
    await update.message.reply_text(help_text, reply_markup=get_status_keyboard(scheduler and scheduler.is_running))

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает текущий статус бота."""
    try:
        channels = await db.get_channels()
        keywords = await db.get_keywords()
        stopwords = await db.get_stopwords()
        
        # Статус парсера
        parser_status = "✅ Активен" if scheduler and scheduler.is_running else "⛔ Остановлен"
        
        status_text = (
            "📊 Текущий статус бота:\n\n"
            f"📢 Каналов: {len(channels)}\n"
            f"🔑 Ключевых слов: {len(keywords)}\n"
            f"🚫 Стоп-слов: {len(stopwords)}\n"
            f"⏱ Интервал проверки: {CHECK_INTERVAL} мин.\n"
            f"📍 Целевой канал: {TARGET_CHANNEL_ID}\n"
            f"🤖 Парсер: {parser_status}\n"
        )
        
        account_text = f"👤 Аккаунт: {update.effective_user.id}\n"
        notification_text = f"📣 ID чата для уведомлений:\n{TARGET_CHANNEL_ID}\n"
        keyword_count = f"🔑 Кол-во ключ-слов: {len(keywords)}\n"
        stopword_count = f"🚫 Кол-во стоп-слов: {len(stopwords)}"
        
        full_text = f"{status_text}\n{account_text}{notification_text}{keyword_count}{stopword_count}"
        
        await update.message.reply_text(full_text, reply_markup=get_status_keyboard(scheduler and scheduler.is_running))
    except Exception as e:
        logger.error(f"Ошибка при получении статуса: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {e}")

async def handle_keyboard_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия на кнопки клавиатуры."""
    text = update.message.text
    
    if text == "🔑 Ключ-слова":
        await show_keywords(update, context)
    elif text == "🚫 Стоп-слова":
        await show_stopwords(update, context)
    elif text == "📢 Каналы":
        await show_channels(update, context)
    elif text == "👥 Группы":
        await update.message.reply_text("Функционал работы с группами находится в разработке.", 
                                      reply_markup=get_status_keyboard(scheduler and scheduler.is_running))
    elif text == "💬 Диалоги":
        await update.message.reply_text("Функционал работы с диалогами находится в разработке.",
                                      reply_markup=get_status_keyboard(scheduler and scheduler.is_running))
    elif text == "🟢 Игнор одинаковых сообщений":
        await update.message.reply_text("Опция игнорирования одинаковых сообщений включена.",
                                      reply_markup=get_status_keyboard(scheduler and scheduler.is_running))
    elif text == "👤 Чёрный список 👤":
        await update.message.reply_text("Функционал черного списка находится в разработке.",
                                      reply_markup=get_status_keyboard(scheduler and scheduler.is_running))
    elif text == "📣 Чат для уведомлений 📣":
        await update.message.reply_text(f"Текущий чат для уведомлений: {TARGET_CHANNEL_ID}\nДля изменения чата отправьте его ID.",
                                      reply_markup=get_status_keyboard(scheduler and scheduler.is_running))
    elif text == "⬅️ Назад ⬅️":
        await update.message.reply_text("Главное меню", reply_markup=get_status_keyboard(scheduler and scheduler.is_running))
    elif text == "🟢 Работает":
        await stop_parsing_keyboard(update, context)
    elif text == "🔴 Остановлен":
        await start_parsing_keyboard(update, context)
    elif text == "➕ Добавить ключевое слово":
        context.user_data["waiting_for"] = "keyword"
        await update.message.reply_text("Введите ключевое слово для добавления.\nДля добавления нескольких обязательных слов используйте символ: +\nПример: продам+айфон")
    elif text == "➕ Добавить стоп-слово":
        context.user_data["waiting_for"] = "stopword"
        await update.message.reply_text("Введите стоп-слово для добавления:")
    elif text == "➕ Добавить канал":
        context.user_data["waiting_for"] = "channel"
        await update.message.reply_text(
            "✏️ Введите ID канала для добавления:\n\n"
            "Можно указать:\n"
            "- Числовой ID (начинается с -100...)\n"
            "- Имя канала (например, @channel_name)\n\n"
            "❗️ Важно: для мониторинга каналов через имя (@username) "
            "вам нужно авторизовать Telethon (если еще не сделано)"
        )
    elif text == "❌ Удалить канал":
        channels = await db.get_channels()
        if not channels:
            await update.message.reply_text("Список каналов пуст.", reply_markup=get_channels_keyboard())
            return
            
        keyboard = []
        for channel in channels:
            keyboard.append([InlineKeyboardButton(f"ID: {channel['channel_id']}", callback_data=f"del_channel_{channel['channel_id']}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Выберите канал для удаления:", reply_markup=reply_markup)
    elif text == "📋 Список каналов":
        await list_channels(update, context)
    elif text == "❌ Удалить все слова ❌":
        if "keyword_menu" in context.user_data:
            keyboard = [
                [InlineKeyboardButton("Да, удалить все ключевые слова", callback_data="confirm_delete_all_keywords")],
                [InlineKeyboardButton("Отмена", callback_data="cancel_delete_all")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Вы уверены, что хотите удалить ВСЕ ключевые слова?", reply_markup=reply_markup)
        elif "stopword_menu" in context.user_data:
            keyboard = [
                [InlineKeyboardButton("Да, удалить все стоп-слова", callback_data="confirm_delete_all_stopwords")],
                [InlineKeyboardButton("Отмена", callback_data="cancel_delete_all")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Вы уверены, что хотите удалить ВСЕ стоп-слова?", reply_markup=reply_markup)
    elif text == "🔄 Сортировать по дате 🔄":
        await update.message.reply_text("Сортировка по дате пока не реализована.", 
                                      reply_markup=get_status_keyboard(scheduler and scheduler.is_running))
    elif text == "📋 Копировать все слова 📋":
        if "keyword_menu" in context.user_data:
            keywords = await db.get_keywords()
            if not keywords:
                await update.message.reply_text("Список ключевых слов пуст.", reply_markup=get_keywords_keyboard())
                return
                
            keywords_text = "\n".join(keywords)
            await update.message.reply_text(f"Список ключевых слов:\n\n{keywords_text}", reply_markup=get_keywords_keyboard())
        elif "stopword_menu" in context.user_data:
            stopwords = await db.get_stopwords()
            if not stopwords:
                await update.message.reply_text("Список стоп-слов пуст.", reply_markup=get_stopwords_keyboard())
                return
                
            stopwords_text = "\n".join(stopwords)
            await update.message.reply_text(f"Список стоп-слов:\n\n{stopwords_text}", reply_markup=get_stopwords_keyboard())
    elif text == "🔍 Показать доступные каналы":
        # Получаем список доступных каналов через Telethon
        await get_available_channels(update, context)
    elif text == "🔐 Авторизовать Telethon":
        # Проверяем, авторизован ли уже клиент
        if await is_telethon_authorized():
            me = await telethon_client.get_me()
            await update.message.reply_text(
                f"✅ Telethon уже авторизован!\n"
                f"Аккаунт: {me.first_name} {getattr(me, 'last_name', '')} (@{me.username})",
                reply_markup=get_channels_keyboard()
            )
        else:
            # Отправляем запрос на код авторизации
            await send_code_request(update, context)

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает пользовательский ввод."""
    if "waiting_for" not in context.user_data:
        await handle_keyboard_button(update, context)
        return
        
    waiting_for = context.user_data["waiting_for"]
    text = update.message.text
    
    if waiting_for == "keyword":
        try:
            await db.add_keyword(text)
            await update.message.reply_text(f"✅ Ключевое слово '{text}' добавлено.", reply_markup=get_keywords_keyboard())
            context.user_data.pop("waiting_for", None)
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}", reply_markup=get_keywords_keyboard())
            context.user_data.pop("waiting_for", None)
    elif waiting_for == "stopword":
        try:
            await db.add_stopword(text)
            await update.message.reply_text(f"✅ Стоп-слово '{text}' добавлено.", reply_markup=get_stopwords_keyboard())
            context.user_data.pop("waiting_for", None)
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}", reply_markup=get_stopwords_keyboard())
            context.user_data.pop("waiting_for", None)
    elif waiting_for == "channel":
        try:
            # Проверяем, начинается ли ввод с '@' (имя канала)
            if text.startswith('@'):
                channel_id = text  # Используем имя канала как есть
                await db.add_channel(channel_id, text)
                await update.message.reply_text(f"✅ Канал {channel_id} добавлен в список мониторинга.", reply_markup=get_channels_keyboard())
                context.user_data.pop("waiting_for", None)
            else:
                # Пробуем преобразовать в числовой ID
                try:
                    channel_id = int(text)
                except ValueError:
                    await update.message.reply_text("❌ Неверный формат ID канала. Введите числовой ID или имя канала, начинающееся с @", reply_markup=get_channels_keyboard())
                    context.user_data.pop("waiting_for", None)
                    return
                
                await db.add_channel(channel_id)
                await update.message.reply_text(f"✅ Канал {channel_id} добавлен в список мониторинга.", reply_markup=get_channels_keyboard())
                context.user_data.pop("waiting_for", None)
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}", reply_markup=get_channels_keyboard())
            context.user_data.pop("waiting_for", None)
    elif waiting_for == "telethon_code":
        # Обработка кода авторизации Telethon
        code = text.strip()
        success = await sign_in_with_code(update, context, code)
        if success:
            context.user_data.pop("waiting_for", None)
            await update.message.reply_text("✅ Теперь вы можете использовать 'Показать доступные каналы'", reply_markup=get_channels_keyboard())
    elif waiting_for == "telethon_2fa":
        # Обработка пароля 2FA
        password = text.strip()
        success = await sign_in_with_2fa(update, context, password)
        if success:
            context.user_data.pop("waiting_for", None)
            await update.message.reply_text("✅ Теперь вы можете использовать 'Показать доступные каналы'", reply_markup=get_channels_keyboard())
    else:
        # Сбрасываем состояние ожидания для неизвестных состояний
        context.user_data.pop("waiting_for", None)
        await update.message.reply_text("❓ Неизвестное состояние ожидания. Пожалуйста, попробуйте снова.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия на inline-кнопки."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("del_channel_"):
        channel_id = int(data.replace("del_channel_", ""))
        try:
            await db.remove_channel(channel_id)
            await query.edit_message_text(f"✅ Канал {channel_id} удален из списка мониторинга.")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при удалении канала: {e}")
    elif data.startswith("del_keyword_"):
        keyword = data.replace("del_keyword_", "")
        try:
            await db.remove_keyword(keyword)
            await query.edit_message_text(f"✅ Ключевое слово '{keyword}' удалено.")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при удалении ключевого слова: {e}")
    elif data.startswith("del_stopword_"):
        stopword = data.replace("del_stopword_", "")
        try:
            await db.remove_stopword(stopword)
            await query.edit_message_text(f"✅ Стоп-слово '{stopword}' удалено.")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при удалении стоп-слова: {e}")
    elif data == "confirm_delete_all_keywords":
        try:
            keywords = await db.get_keywords()
            for keyword in keywords:
                await db.remove_keyword(keyword)
            await query.edit_message_text("✅ Все ключевые слова удалены.")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при удалении ключевых слов: {e}")
    elif data == "confirm_delete_all_stopwords":
        try:
            stopwords = await db.get_stopwords()
            for stopword in stopwords:
                await db.remove_stopword(stopword)
            await query.edit_message_text("✅ Все стоп-слова удалены.")
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при удалении стоп-слов: {e}")
    elif data == "cancel_delete_all":
        await query.edit_message_text("❌ Удаление отменено.")

async def show_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список ключевых слов."""
    context.user_data["keyword_menu"] = True
    context.user_data.pop("stopword_menu", None)
    
    try:
        keywords = await db.get_keywords()
        
        if not keywords:
            await update.message.reply_text("📋 Список ключевых слов пуст.", reply_markup=get_keywords_keyboard())
            return
        
        keyboard = []
        for keyword in keywords:
            keyboard.append([InlineKeyboardButton(f"❌ {keyword}", callback_data=f"del_keyword_{keyword}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("📋 Список ключевых слов:", reply_markup=reply_markup)
        await update.message.reply_text("Выберите действие:", reply_markup=get_keywords_keyboard())
    except Exception as e:
        logger.error(f"Ошибка при получении списка ключевых слов: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {e}", reply_markup=get_keywords_keyboard())

async def show_stopwords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список стоп-слов."""
    context.user_data["stopword_menu"] = True
    context.user_data.pop("keyword_menu", None)
    
    try:
        stopwords = await db.get_stopwords()
        
        if not stopwords:
            await update.message.reply_text("📋 Список стоп-слов пуст.", reply_markup=get_stopwords_keyboard())
            return
        
        keyboard = []
        for stopword in stopwords:
            keyboard.append([InlineKeyboardButton(f"❌ {stopword}", callback_data=f"del_stopword_{stopword}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("📋 Список стоп-слов:", reply_markup=reply_markup)
        await update.message.reply_text("Выберите действие:", reply_markup=get_stopwords_keyboard())
    except Exception as e:
        logger.error(f"Ошибка при получении списка стоп-слов: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {e}", reply_markup=get_stopwords_keyboard())

async def show_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает меню управления каналами."""
    await update.message.reply_text("Меню управления каналами:", reply_markup=get_channels_keyboard())

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список каналов для мониторинга."""
    try:
        channels = await db.get_channels()
        
        if not channels:
            await update.message.reply_text("📋 Список каналов пуст.", reply_markup=get_channels_keyboard())
            return
        
        channels_text = "📋 Список отслеживаемых каналов:\n\n"
        for i, channel in enumerate(channels, 1):
            channels_text += f"{i}. ID: {channel['channel_id']}"
            if channel['name']:
                channels_text += f" ({channel['name']})"
            channels_text += "\n"
        
        await update.message.reply_text(channels_text, reply_markup=get_channels_keyboard())
    except Exception as e:
        logger.error(f"Ошибка при получении списка каналов: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {e}", reply_markup=get_channels_keyboard())

async def start_parsing_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запускает процесс парсинга через клавиатуру."""
    global scheduler
    
    if scheduler and scheduler.is_running:
        await update.message.reply_text("⚠️ Парсинг уже запущен", reply_markup=get_status_keyboard(True))
        return
        
    try:
        if not scheduler:
            scheduler = MessageScheduler(
                db, 
                TARGET_CHANNEL_ID, 
                CHECK_INTERVAL, 
                "",
                telethon_client=telethon_client
            )
            
        scheduler.start()
        await update.message.reply_text("✅ Парсинг успешно запущен", reply_markup=get_status_keyboard(True))
    except Exception as e:
        logger.error(f"Ошибка при запуске парсинга: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {e}", reply_markup=get_status_keyboard(False))

async def stop_parsing_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Останавливает процесс парсинга через клавиатуру."""
    global scheduler
    
    if not scheduler or not scheduler.is_running:
        await update.message.reply_text("⚠️ Парсинг не запущен", reply_markup=get_status_keyboard(False))
        return
        
    try:
        scheduler.stop()
        await update.message.reply_text("✅ Парсинг успешно остановлен", reply_markup=get_status_keyboard(False))
    except Exception as e:
        logger.error(f"Ошибка при остановке парсинга: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {e}", reply_markup=get_status_keyboard(True))

async def init_database():
    """Инициализирует базу данных."""
    try:
        connected = await db.connect()
        if not connected:
            logger.error("Не удалось подключиться к базе данных.")
            return False
            
        # Проверяем и мигрируем схему базы данных
        await migrate_database_schema()
            
        return True
    except Exception as e:
        logger.error(f"Ошибка при подключении к базе данных: {e}")
        return False

async def migrate_database_schema():
    """Проверяет и мигрирует схему базы данных."""
    try:
        async with db.pool.acquire() as conn:
            # Проверяем текущий тип channel_id в таблице channels
            table_info = await conn.fetch("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'channels' AND column_name = 'channel_id'
            """)
            
            if table_info and table_info[0]['data_type'] == 'bigint':
                logger.info("Миграция схемы: изменение типа channel_id с BIGINT на TEXT")
                
                # Создаем временную таблицу с новой схемой
                await conn.execute("""
                    CREATE TABLE channels_temp (
                        id SERIAL PRIMARY KEY,
                        channel_id TEXT UNIQUE NOT NULL,
                        name TEXT,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                """)
                
                # Копируем данные со преобразованием
                await conn.execute("""
                    INSERT INTO channels_temp (id, channel_id, name, is_active)
                    SELECT id, CAST(channel_id AS TEXT), name, is_active FROM channels
                """)
                
                # Удаляем старую таблицу и переименовываем новую
                await conn.execute("DROP TABLE channels")
                await conn.execute("ALTER TABLE channels_temp RENAME TO channels")
                
                logger.info("Миграция схемы успешно завершена")
    except Exception as e:
        logger.error(f"Ошибка при миграции схемы базы данных: {e}")
        # Продолжаем работу, даже если миграция не удалась

async def main_async():
    """Асинхронная функция для запуска бота."""
    # Подключаемся к базе данных
    if not await init_database():
        return
    
    # Инициализируем Telethon клиент
    await init_telethon()
        
    # Создаем экземпляр приложения
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    
    # Добавляем обработчик для кнопок клавиатуры
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    
    # Добавляем обработчик для inline-кнопок
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Запускаем бота
    await application.initialize()
    await application.start()
    
    # Запускаем поллинг
    await application.updater.start_polling()
    
    logger.info("Бот успешно запущен!")
    
    # Запускаем парсер в автоматическом режиме
    global scheduler
    if not scheduler:
        scheduler = MessageScheduler(
            db, 
            TARGET_CHANNEL_ID, 
            CHECK_INTERVAL, 
            "",
            telethon_client=telethon_client
        )
        
    scheduler.start()
    logger.info("Парсер запущен автоматически в боевом режиме!")
    
    # Ждем вечно или до сигнала завершения
    try:
        # Создаем событие, которое никогда не будет установлено
        stop_event = asyncio.Event()
        await stop_event.wait()
    finally:
        # Останавливаем бота
        await application.stop()
        # Закрываем соединение с базой данных
        await db.close()
        # Закрываем Telethon клиент
        if telethon_client:
            await telethon_client.disconnect()

def main() -> None:
    """Запускает бота."""
    print("Запуск Telegram бота с поддержкой клавиатуры...")
    
    try:
        # Запускаем асинхронную функцию
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("Бот остановлен пользователем")
    except Exception as e:
        print(f"Ошибка при выполнении бота: {e}")

# Функции для работы с Telethon
async def init_telethon():
    """Инициализирует клиент Telethon."""
    global telethon_client
    
    # Проверяем, есть ли настройки для Telethon
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH or not TELEGRAM_PHONE:
        logger.warning("Не указаны настройки для Telethon в .env файле")
        return None
        
    try:
        # Преобразуем API_ID в число
        api_id = int(TELEGRAM_API_ID)
        
        # Создаем клиент Telethon с дополнительными параметрами
        telethon_client = TelegramClient(
            'telegram_parser_session', 
            api_id, 
            TELEGRAM_API_HASH,
            device_model="Windows Desktop",
            system_version="4.16.30-vxCUSTOM",
            app_version="1.0.0"
        )
        
        # Подключаемся
        await telethon_client.connect()
        
        logger.info("Telethon клиент инициализирован")
        return telethon_client
    except Exception as e:
        logger.error(f"Ошибка при инициализации Telethon: {e}")
        return None

async def is_telethon_authorized():
    """Проверяет, авторизован ли клиент Telethon."""
    global telethon_client
    
    if not telethon_client:
        telethon_client = await init_telethon()
        
    if not telethon_client:
        return False
        
    try:
        return await telethon_client.is_user_authorized()
    except Exception as e:
        logger.error(f"Ошибка при проверке авторизации Telethon: {e}")
        return False

async def send_code_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет запрос на код авторизации Telethon."""
    global telethon_client
    
    if not telethon_client:
        telethon_client = await init_telethon()
        
    if not telethon_client:
        await update.message.reply_text(
            "❌ Не удалось инициализировать Telethon клиент.\n"
            "Проверьте настройки в .env файле:\n"
            "TELEGRAM_API_ID=...\n"
            "TELEGRAM_API_HASH=...\n"
            "TELEGRAM_PHONE=..."
        )
        return
        
    try:
        # Отправляем запрос на код
        await telethon_client.send_code_request(TELEGRAM_PHONE)
        
        # Устанавливаем состояние ожидания кода
        context.user_data["waiting_for"] = "telethon_code"
        
        await update.message.reply_text(
            f"📱 Код авторизации отправлен на номер {TELEGRAM_PHONE}.\n"
            "Пожалуйста, введите полученный код:"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при отправке кода: {e}")

async def sign_in_with_code(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
    """Авторизуется в Telethon с помощью кода."""
    global telethon_client
    
    if not telethon_client:
        await update.message.reply_text("❌ Telethon клиент не инициализирован.")
        return False
        
    try:
        # Авторизуемся с кодом
        await telethon_client.sign_in(TELEGRAM_PHONE, code)
        
        # Проверяем успешность авторизации
        if await telethon_client.is_user_authorized():
            me = await telethon_client.get_me()
            await update.message.reply_text(
                f"✅ Авторизация успешна!\n"
                f"Авторизован как: {me.first_name} {getattr(me, 'last_name', '')} (@{me.username})"
            )
            return True
        else:
            await update.message.reply_text("❌ Не удалось авторизоваться. Попробуйте снова.")
            return False
            
    except errors.SessionPasswordNeededError:
        # Если требуется двухфакторная аутентификация
        context.user_data["waiting_for"] = "telethon_2fa"
        await update.message.reply_text("🔐 Требуется пароль двухфакторной аутентификации. Пожалуйста, введите пароль:")
        return False
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при авторизации: {e}")
        return False

async def sign_in_with_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE, password: str):
    """Авторизуется в Telethon с помощью пароля 2FA."""
    global telethon_client
    
    if not telethon_client:
        await update.message.reply_text("❌ Telethon клиент не инициализирован.")
        return False
        
    try:
        # Авторизуемся с паролем 2FA
        await telethon_client.sign_in(password=password)
        
        # Проверяем успешность авторизации
        if await telethon_client.is_user_authorized():
            me = await telethon_client.get_me()
            await update.message.reply_text(
                f"✅ Авторизация успешна!\n"
                f"Авторизован как: {me.first_name} {getattr(me, 'last_name', '')} (@{me.username})"
            )
            return True
        else:
            await update.message.reply_text("❌ Не удалось авторизоваться. Попробуйте снова.")
            return False
            
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при авторизации с 2FA: {e}")
        return False

async def get_available_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает список доступных каналов через Telethon."""
    global telethon_client
    
    if not telethon_client:
        telethon_client = await init_telethon()
        
    if not telethon_client:
        await update.message.reply_text("❌ Telethon клиент не инициализирован.")
        return
        
    # Проверяем авторизацию
    if not await is_telethon_authorized():
        await update.message.reply_text(
            "❌ Telethon клиент не авторизован.\n"
            "Используйте опцию '🔐 Авторизовать Telethon' для авторизации."
        )
        return
        
    try:
        # Получаем диалоги
        await update.message.reply_text("🔍 Получаем список каналов, пожалуйста, подождите...")
        
        dialogs = await telethon_client.get_dialogs(limit=50)
        
        # Выбираем только каналы
        channels = [d for d in dialogs if d.is_channel]
        
        if not channels:
            await update.message.reply_text("❕ Не найдено каналов, доступных через ваш аккаунт.")
            return
            
        # Отправляем список каналов
        message = "📋 Доступные каналы через ваш аккаунт:\n\n"
        for i, dialog in enumerate(channels, 1):
            channel_id = dialog.id
            name = dialog.title
            message += f"{i}. ID: {channel_id} - {name}\n"
            
            # Если сообщение становится слишком длинным, отправляем его и начинаем новое
            if len(message) > 3500:
                await update.message.reply_text(message)
                message = ""
                
        if message:
            await update.message.reply_text(message)
            
        # Предлагаем добавить каналы
        await update.message.reply_text(
            "✅ Для добавления канала выберите 'Добавить канал' и введите ID канала из списка.",
            reply_markup=get_channels_keyboard()
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при получении списка каналов: {e}")

if __name__ == "__main__":
    main() 