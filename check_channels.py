#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для проверки доступа к каналам
"""

import asyncio
import logging
from dotenv import load_dotenv
import os
from telegram import Bot
from database import Database
from parser import MessageParser

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Получаем настройки из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHANNEL_ID = os.getenv("TARGET_CHANNEL_ID")

async def check_channels():
    """Проверяет доступ к каналам и отправляет тестовое сообщение."""
    # Инициализация базы данных и бота
    db = Database()
    bot = Bot(BOT_TOKEN)
    
    try:
        # Подключение к базе данных
        connected = await db.connect()
        if not connected:
            logger.error("Не удалось подключиться к базе данных.")
            return
        
        # Создаем парсер
        parser = MessageParser(bot, db, TARGET_CHANNEL_ID)
        
        # Получаем список каналов
        channels = await db.get_channels()
        
        if not channels:
            logger.warning("Нет каналов для проверки.")
            return
        
        logger.info(f"Проверка доступа к {len(channels)} каналам...")
        
        # Проверяем доступ к каждому каналу
        for channel in channels:
            channel_id = channel['channel_id']
            channel_name = channel['name'] or str(channel_id)
            
            logger.info(f"Проверка канала {channel_name} ({channel_id})...")
            
            # Проверяем доступ к каналу
            has_access, actual_id = await parser.check_channel_access(channel_id)
            
            if has_access:
                logger.info(f"✅ Доступ к каналу {channel_name} ({channel_id}) успешно получен.")
                
                # Отправляем тестовое сообщение в целевой канал
                try:
                    await bot.send_message(
                        chat_id=TARGET_CHANNEL_ID,
                        text=f"✅ Тестовое сообщение: Канал {channel_name} ({channel_id}) доступен для мониторинга."
                    )
                    logger.info(f"✅ Тестовое сообщение отправлено в целевой канал {TARGET_CHANNEL_ID}")
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки тестового сообщения: {e}")
            else:
                logger.error(f"❌ Нет доступа к каналу {channel_name} ({channel_id})")
                
                # Отправляем сообщение об ошибке в целевой канал
                try:
                    await bot.send_message(
                        chat_id=TARGET_CHANNEL_ID,
                        text=f"❌ Ошибка: Нет доступа к каналу {channel_name} ({channel_id})"
                    )
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки сообщения об ошибке: {e}")
        
        # Проверяем доступ к целевому каналу
        try:
            target_chat = await bot.get_chat(chat_id=TARGET_CHANNEL_ID)
            logger.info(f"✅ Доступ к целевому каналу {target_chat.title} ({TARGET_CHANNEL_ID}) успешно получен.")
        except Exception as e:
            logger.error(f"❌ Нет доступа к целевому каналу {TARGET_CHANNEL_ID}: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка при проверке каналов: {e}")
    finally:
        # Закрытие соединения с базой данных
        await db.close()

async def main_async():
    """Асинхронная функция для запуска проверки каналов."""
    await check_channels()

def main():
    """Запускает скрипт."""
    print("Запуск скрипта для проверки доступа к каналам...")
    
    try:
        # Запускаем асинхронную функцию
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("Скрипт остановлен пользователем")
    except Exception as e:
        print(f"Ошибка при выполнении скрипта: {e}")

if __name__ == "__main__":
    main() 