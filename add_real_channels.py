#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для добавления реальных каналов
"""

import asyncio
from database import Database
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# ВНИМАНИЕ: Замените эти значения на свои реальные каналы
# Каналы могут быть указаны как числовые ID или username
# Примеры:
# - Числовой ID: -1001234567890 (должен начинаться с -100)
# - Username: @channel_name (должен начинаться с @)
REAL_CHANNELS = [
    # Замените эти примеры на свои реальные каналы
    {"id": "@telegram", "name": "Официальный канал Telegram"},
    {"id": "@durov", "name": "Канал Павла Дурова"},
    # Добавьте свои каналы здесь
]

# Убедитесь, что целевой канал указан в .env файле (TARGET_CHANNEL_ID)
# и бот добавлен в этот канал с правами на отправку сообщений

async def add_real_channels():
    """Добавляет реальные каналы в базу данных."""
    # Инициализация базы данных
    db = Database()
    
    try:
        # Подключение к базе данных
        connected = await db.connect()
        if not connected:
            print("Не удалось подключиться к базе данных.")
            return
        
        # Очищаем существующие каналы
        await clear_existing_channels(db)
        
        print("Добавление реальных каналов в базу данных...")
        
        # Добавление каналов
        print("\nДобавление каналов:")
        for channel in REAL_CHANNELS:
            try:
                channel_id = channel["id"]
                name = channel["name"]
                
                # Если канал указан через @username, сохраняем как есть
                # Иначе преобразуем в числовой ID
                if isinstance(channel_id, str) and channel_id.startswith('@'):
                    final_id = channel_id
                else:
                    # Убедитесь, что ID числовой и начинается с -100
                    final_id = int(str(channel_id))
                
                await db.add_channel(final_id, name)
                print(f"✅ Канал {final_id} ({name}) добавлен")
            except Exception as e:
                print(f"❌ Ошибка при добавлении канала {channel['id']}: {e}")
        
        print("\nПроверьте, что бот добавлен в следующие каналы:")
        for channel in REAL_CHANNELS:
            print(f"  - {channel['name']} ({channel['id']})")
        
        print("\nВажно: Бот должен быть добавлен как администратор в каналы, которые нужно мониторить.")
        print("Кроме того, бот должен быть добавлен в целевой канал с правами на отправку сообщений.")
        print("\nПосле добавления каналов запустите check_channels.py для проверки доступа.")
    
    except Exception as e:
        print(f"Ошибка при добавлении реальных каналов: {e}")
    finally:
        # Закрытие соединения с базой данных
        await db.close()

async def clear_existing_channels(db):
    """Удаляет существующие каналы из базы данных."""
    try:
        print("Удаление существующих каналов...")
        channels = await db.get_channels()
        for channel in channels:
            await db.remove_channel(channel['channel_id'])
            print(f"✅ Канал {channel['channel_id']} удален")
    except Exception as e:
        print(f"Ошибка при удалении каналов: {e}")

def main():
    """Запускает скрипт."""
    print("Запуск скрипта для добавления реальных каналов...")
    print("\nВНИМАНИЕ: Перед запуском отредактируйте файл add_real_channels.py")
    print("и замените примеры каналов на свои реальные каналы.")
    
    confirm = input("\nПродолжить? (y/n): ")
    if confirm.lower() != 'y':
        print("Отмена.")
        return
    
    try:
        # Запускаем асинхронную функцию
        asyncio.run(add_real_channels())
    except KeyboardInterrupt:
        print("Скрипт остановлен пользователем")
    except Exception as e:
        print(f"Ошибка при выполнении скрипта: {e}")

if __name__ == "__main__":
    main() 