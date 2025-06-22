#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для авторизации Telethon клиента
"""

import os
import sys
import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Получение настроек Telethon
API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE = os.getenv("TELEGRAM_PHONE")

# Проверка наличия необходимых переменных
if not API_ID or not API_HASH or not PHONE:
    print("Ошибка: Не указаны необходимые переменные окружения для Telethon.")
    print("Создайте файл .env и укажите следующие переменные:")
    print("TELEGRAM_API_ID=ваш_api_id")
    print("TELEGRAM_API_HASH=ваш_api_hash")
    print("TELEGRAM_PHONE=ваш_номер_телефона")
    sys.exit(1)

async def main():
    print(f"Авторизация Telethon клиента для номера {PHONE}...")
    
    # Создаем клиент Telethon
    client = TelegramClient(
        'telegram_parser_session', 
        API_ID, 
        API_HASH,
        device_model="Windows Desktop",
        system_version="4.16.30-vxCUSTOM",
        app_version="1.0.0"
    )
    
    # Подключаемся
    await client.connect()
    
    # Проверяем, авторизован ли клиент
    if await client.is_user_authorized():
        print("Клиент уже авторизован!")
        me = await client.get_me()
        print(f"Авторизован как: {me.first_name} {me.last_name} (@{me.username})")
        
        # Получаем список доступных каналов
        print("\nДоступные каналы:")
        dialogs = await client.get_dialogs()
        channels = [dialog for dialog in dialogs if dialog.is_channel]
        
        for i, channel in enumerate(channels[:10], 1):
            print(f"{i}. {channel.title} (@{channel.entity.username if hasattr(channel.entity, 'username') and channel.entity.username else 'private'}) - ID: {channel.id}")
        
        if len(channels) > 10:
            print(f"...и еще {len(channels) - 10} каналов")
        
        await client.disconnect()
        return
    
    # Отправляем код авторизации
    await client.send_code_request(PHONE)
    print(f"Код авторизации отправлен на номер {PHONE}")
    
    # Запрашиваем код у пользователя
    code = input("Введите полученный код: ")
    
    try:
        # Авторизуемся с помощью кода
        await client.sign_in(PHONE, code)
    except SessionPasswordNeededError:
        # Если включена двухфакторная аутентификация
        password = input("Введите пароль двухфакторной аутентификации: ")
        await client.sign_in(password=password)
    
    # Проверяем успешность авторизации
    if await client.is_user_authorized():
        print("Авторизация успешна!")
        me = await client.get_me()
        print(f"Авторизован как: {me.first_name} {me.last_name} (@{me.username})")
        
        # Получаем список доступных каналов
        print("\nДоступные каналы:")
        dialogs = await client.get_dialogs()
        channels = [dialog for dialog in dialogs if dialog.is_channel]
        
        for i, channel in enumerate(channels[:10], 1):
            print(f"{i}. {channel.title} (@{channel.entity.username if hasattr(channel.entity, 'username') and channel.entity.username else 'private'}) - ID: {channel.id}")
        
        if len(channels) > 10:
            print(f"...и еще {len(channels) - 10} каналов")
    else:
        print("Авторизация не удалась.")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 