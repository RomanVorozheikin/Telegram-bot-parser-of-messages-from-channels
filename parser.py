import asyncio
from datetime import datetime, timedelta
from loguru import logger
from telegram import Bot
from telegram.error import TelegramError, BadRequest, Forbidden
from telegram.constants import ParseMode
from database import Database
import telethon
from telethon import TelegramClient
from telethon.errors import FloodWaitError
import os
import re
import random
import time

# Устанавливаем уровень логирования на DEBUG
logger.remove()
logger.add(lambda msg: print(msg, end=""), level="DEBUG")
logger.add("debug_logs.log", level="DEBUG", rotation="5 MB")

class MessageParser:
    """Класс для парсинга сообщений из каналов."""
    
    def __init__(self, db, target_channel_id=None, check_interval=3, signature="", telethon_client=None):
        """Инициализирует парсер.
        
        Args:
            db: Экземпляр базы данных
            target_channel_id: ID целевого канала для пересылки сообщений
            check_interval: Интервал проверки в минутах
            signature: Подпись для пересылаемых сообщений
            telethon_client: Экземпляр клиента Telethon (опционально)
        """
        self.db = db
        self.target_channel_id = target_channel_id
        self.check_interval = check_interval
        self.signature = signature
        
        # Параметры для Telethon
        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.phone = os.getenv("TELEGRAM_PHONE")
        self.telethon_session_name = 'telegram_parser_session'
        self.client = telethon_client  # Используем переданный клиент, если он есть
        
        # Проверяем наличие параметров для Telethon
        if not self.api_id or not self.api_hash or not self.phone:
            logger.error("Не указаны параметры для Telethon клиента. Парсер не будет работать.")
        else:
            logger.info("Найдены данные для Telethon клиента")
            
        # Параметры для защиты от блокировки
        self.max_channels_per_run = int(os.getenv("MAX_CHANNELS_PER_RUN", "20"))  # Максимальное количество каналов за один запуск
        self.delay_between_channels = float(os.getenv("DELAY_BETWEEN_CHANNELS", "1.0"))  # Задержка между каналами (секунды)
        self.max_messages_per_channel = int(os.getenv("MAX_MESSAGES_PER_CHANNEL", "20"))
        self.jitter = float(os.getenv("JITTER", "0.2"))  # Случайное отклонение для задержек (±20%)
        self.last_channel_request_time = 0  # Время последнего запроса к каналу
        
    def normalize_channel_id(self, channel_id):
        """Преобразует ID канала в правильный формат для API"""
        # Если это уже строка и начинается с @, это уже имя канала
        if isinstance(channel_id, str) and channel_id.startswith('@'):
            return channel_id
            
        # Преобразуем в строку для обработки
        channel_id_str = str(channel_id)
        
        # Если это числовой ID с префиксом -100, значит это supergroup/channel
        if channel_id_str.startswith('-100'):
            # Проверяем, можно ли преобразовать в юзернейм (для публичных каналов)
            # Но сохраняем оригинальный ID, если не удается
            try:
                clean_id = channel_id_str.replace('-100', '')
                return clean_id
            except:
                return channel_id_str
        
        # Проверяем, может быть это ссылка t.me/...
        if 't.me/' in channel_id_str:
            username_match = re.search(r't\.me/(?:joinchat/)?([a-zA-Z0-9_-]+)', channel_id_str)
            if username_match:
                return f"@{username_match.group(1)}"
        
        # Если ничего не подошло, возвращаем исходное значение
        return channel_id_str
    

        
    async def initialize_telethon(self):
        """Инициализирует клиент Telethon."""
        # Если клиент уже инициализирован и подключен, используем его
        if self.client and self.client.is_connected():
            try:
                # Проверяем, авторизован ли клиент
                if await self.client.is_user_authorized():
                    logger.info("Используем существующий Telethon клиент")
                    return True
            except Exception as e:
                logger.error(f"Ошибка при проверке авторизации существующего Telethon клиента: {e}")
        
        # Если нет существующего клиента или он не подключен, создаем новый
        if not self.api_id or not self.api_hash or not self.phone:
            logger.error("Не указаны настройки для Telethon")
            return False
            
        try:
            # Преобразуем API ID в число
            api_id = int(self.api_id)
            
            # Используем device_info для имитации реального устройства
            device_model = "Windows Desktop"
            system_version = "4.16.30-vxCUSTOM"
            app_version = "1.0.0"
            
            # Создаем клиент только если он еще не был создан
            if not self.client:
                self.client = TelegramClient(
                    self.telethon_session_name, 
                    api_id, 
                    self.api_hash,
                    device_model=device_model,
                    system_version=system_version,
                    app_version=app_version
                )
                await self.client.connect()
            
            # Проверяем авторизацию
            if not await self.client.is_user_authorized():
                logger.info(f"Отправляем код авторизации на номер {self.phone}")
                await self.client.send_code_request(self.phone)
                logger.error("Требуется ручная авторизация через консоль. Запустите authorize_telethon.py")
                return False
            else:
                logger.info("Telethon клиент успешно авторизован")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при инициализации Telethon клиента: {e}")
            return False
    
    async def add_delay(self, base_delay=1.0):
        """Добавляет случайную задержку для имитации человеческого поведения"""
        # Вычисляем случайную задержку с отклонением ±jitter%
        jitter_factor = 1 + random.uniform(-self.jitter, self.jitter)
        delay = base_delay * jitter_factor
        
        # Добавляем задержку
        await asyncio.sleep(delay)
        return delay
    
    async def check_keywords_in_message(self, message_text, keywords, stopwords):
        """Проверяет наличие ключевых слов в сообщении и отсутствие стоп-слов"""
        if not message_text:
            logger.debug("Пустой текст сообщения, пропускаем проверку")
            return False
            
        # Если сообщение содержит только тип медиа в квадратных скобках (например, [фото]),
        # то пропускаем проверку на ключевые слова
        if re.match(r'^\[\w+\]$', message_text):
            logger.debug(f"Пропускаем проверку ключевых слов для медиа без текста: {message_text}")
            return False
        
        # Если сообщение содержит медиа и текст, удаляем префикс типа медиа для проверки
        if re.match(r'^\[\w+\]\s+.+', message_text):
            # Извлекаем только текстовую часть для проверки ключевых слов
            clean_text = re.sub(r'^\[\w+\]\s+', '', message_text)
            logger.debug(f"Проверяем только текстовую часть сообщения: {clean_text}")
            message_lower = clean_text.lower()
        else:
            message_lower = message_text.lower()
        
        logger.debug(f"Текст для проверки (в нижнем регистре): {message_lower[:100]}...")
        logger.debug(f"Ключевые слова для проверки: {keywords}")
        
        # Проверка на стоп-слова
        for stopword in stopwords:
            if stopword.lower() in message_lower:
                logger.debug(f"Найдено стоп-слово: {stopword}")
                return False
        
        # Проверка на ключевые слова
        for keyword in keywords:
            # Проверяем составные ключевые слова (с символом +)
            if "+" in keyword:
                parts = keyword.lower().split("+")
                all_parts_found = True
                for part in parts:
                    if part.strip() not in message_lower:
                        all_parts_found = False
                        break
                if all_parts_found:
                    logger.debug(f"Найдено составное ключевое слово: {keyword}")
                    return True
            elif keyword.lower() in message_lower:
                logger.debug(f"Найдено ключевое слово: {keyword}")
                return True
        
        logger.debug("Ключевые слова не найдены")
        return False
    
    async def forward_message(self, from_chat_id, message_id):
        """Пересылает сообщение в целевой канал с подписью используя только Telethon"""
        try:
            if not self.target_channel_id:
                logger.error("Не указан целевой канал для пересылки сообщений")
                return False
                
            logger.info(f"Пересылаем сообщение {message_id} из канала {from_chat_id} в канал {self.target_channel_id}")
            
            # Проверяем, что Telethon клиент готов к работе
            if not self.client or not self.client.is_connected() or not await self.client.is_user_authorized():
                logger.error("Telethon клиент не инициализирован или не авторизован")
                return False
            
            try:
                # Получаем сущности каналов
                source_entity = None
                target_entity = None
                
                # Получаем сущность исходного канала
                if isinstance(from_chat_id, str) and from_chat_id.startswith('@'):
                    source_entity = await self.client.get_entity(from_chat_id)
                else:
                    try:
                        source_entity = await self.client.get_entity(int(from_chat_id))
                    except ValueError:
                        source_entity = await self.client.get_entity(from_chat_id)
                
                # Получаем сущность целевого канала
                target_entity = await self.client.get_entity(int(self.target_channel_id))
                
                logger.info(f"Получены сущности каналов: источник={source_entity.id}, цель={target_entity.id}")
                
                # Получаем сообщение
                message = await self.client.get_messages(source_entity, ids=message_id)
                if not message:
                    logger.error(f"Сообщение {message_id} не найдено в канале {from_chat_id}")
                    return False
                
                # Пересылаем сообщение
                forwarded = await self.client.forward_messages(
                    entity=target_entity,
                    messages=message,
                    silent=False
                )
                
                if forwarded:
                    # Убираем отправку подписи, так как она не нужна
                    
                    # Отмечаем сообщение как обработанное
                    await self.db.mark_message_processed(from_chat_id, message_id)
                    
                    logger.info(f"Сообщение {message_id} из канала {from_chat_id} успешно переслано через Telethon")
                    return True
                else:
                    logger.error(f"Не удалось переслать сообщение через Telethon")
                    return False
                    
            except Exception as e:
                logger.error(f"Ошибка при пересылке сообщения через Telethon: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при пересылке сообщения: {e}")
            return False
    
    async def get_recent_messages_telethon(self, channel_id, limit=20):
        """Получает последние сообщения из канала через Telethon с защитой от блокировки"""
        try:
            if not self.client or not self.client.is_connected():
                success = await self.initialize_telethon()
                if not success:
                    logger.warning("Не удалось инициализировать Telethon клиент")
                    return []
            
            if not await self.client.is_user_authorized():
                logger.warning("Telethon клиент не авторизован, не удается получить сообщения")
                return []
            
            # Ограничиваем количество сообщений
            limit = min(limit, self.max_messages_per_channel)
            
            # Добавляем задержку между запросами к каналам
            current_time = time.time()
            time_since_last_request = current_time - self.last_channel_request_time
            
            if time_since_last_request < self.delay_between_channels:
                await asyncio.sleep(self.delay_between_channels - time_since_last_request)
            
            # Получаем сущность канала в зависимости от типа ID
            try:
                logger.info(f"Получаем сущность канала {channel_id} через Telethon")
                
                if isinstance(channel_id, str) and channel_id.startswith('@'):
                    # Если это имя канала, используем как есть
                    entity = await self.client.get_entity(channel_id)
                else:
                    # Иначе пробуем как числовой ID
                    try:
                        entity = await self.client.get_entity(int(channel_id))
                    except ValueError:
                        # Если не удалось преобразовать в число, используем как строку
                        entity = await self.client.get_entity(channel_id)
                
                logger.info(f"Успешно получена сущность канала: {entity.title} (ID: {entity.id})")
                
                # Добавляем небольшую задержку перед получением сообщений
                await self.add_delay(0.5)
                
                try:
                    # Получаем сообщения с обработкой FloodWaitError
                    logger.info(f"Запрашиваем {limit} сообщений из канала {entity.title}")
                    messages = await self.client.get_messages(entity, limit=limit)
                    
                    if not messages:
                        logger.warning(f"Канал {entity.title} не содержит сообщений или у вас нет доступа к истории")
                        return []
                        
                    logger.info(f"Получено {len(messages)} сообщений из канала {entity.title}")
                    
                except FloodWaitError as e:
                    # Если получили ошибку о превышении лимита запросов, ждем указанное время
                    wait_time = e.seconds
                    logger.warning(f"Превышен лимит запросов к API. Ожидаем {wait_time} секунд")
                    await asyncio.sleep(wait_time)
                    # Повторяем запрос с меньшим лимитом
                    logger.info(f"Повторный запрос с уменьшенным лимитом ({min(5, limit)} сообщений)")
                    messages = await self.client.get_messages(entity, limit=min(5, limit))
                
                # Обновляем время последнего запроса
                self.last_channel_request_time = time.time()
                
                # Конвертируем сообщения Telethon в формат, схожий с python-telegram-bot
                result = []
                for msg in messages:
                    # Выводим сырое сообщение для отладки
                    logger.debug(f"Обрабатываем сообщение ID: {msg.id}")
                    
                    # Выводим все атрибуты сообщения
                    logger.debug(f"Все атрибуты сообщения: {dir(msg)}")
                    
                    # Выводим все важные атрибуты и их значения
                    for attr in ['message', 'text', 'raw_text', 'caption', 'grouped_id', 'post', 'post_author']:
                        if hasattr(msg, attr):
                            value = getattr(msg, attr)
                            logger.debug(f"Атрибут {attr}: {value}")
                    
                    # Проверяем наличие текста или медиа с подписью
                    text = None
                    
                    # Проверяем основной текст сообщения (в разных атрибутах)
                    if hasattr(msg, 'message') and msg.message:
                        text = msg.message
                        logger.debug(f"Найден текст сообщения (message): {text[:100]}...")
                    elif hasattr(msg, 'text') and msg.text:
                        text = msg.text
                        logger.debug(f"Найден текст сообщения (text): {text[:100]}...")
                    
                    # Проверяем наличие подписи к медиа
                    caption = None
                    if hasattr(msg, 'caption') and msg.caption:
                        caption = msg.caption
                        logger.debug(f"Найдена подпись к медиа: {caption[:100]}...")
                    
                    # Проверяем наличие raw_text (иногда текст может быть там)
                    if not text and hasattr(msg, 'raw_text') and msg.raw_text:
                        text = msg.raw_text
                        logger.debug(f"Найден текст в raw_text: {text[:100]}...")
                    
                    # Определяем тип сообщения для отладки
                    msg_type = "неизвестно"
                    has_media = False
                    
                    if hasattr(msg, 'photo') and msg.photo:
                        msg_type = "фото"
                        has_media = True
                        logger.debug("Сообщение содержит фото")
                    elif hasattr(msg, 'video') and msg.video:
                        msg_type = "видео"
                        has_media = True
                    elif hasattr(msg, 'document') and msg.document:
                        msg_type = "документ"
                        has_media = True
                    elif hasattr(msg, 'audio') and msg.audio:
                        msg_type = "аудио"
                        has_media = True
                    elif hasattr(msg, 'voice') and msg.voice:
                        msg_type = "голосовое"
                        has_media = True
                    elif hasattr(msg, 'poll') and msg.poll:
                        msg_type = "опрос"
                        has_media = True
                    elif text:
                        msg_type = "текст"
                    
                    # Для отладки выводим подробную информацию о сообщении
                    logger.debug(f"Сообщение {msg.id}: тип={msg_type}, текст={bool(text)}, подпись={bool(caption)}")
                    
                    # Проверяем, есть ли текст для проверки ключевых слов
                    message_text = text or caption or ""
                    
                    # Если сообщение содержит только медиа без текста, добавляем метку типа
                    if not message_text and has_media:
                        message_text = f"[{msg_type}]"
                    
                    # Если сообщение содержит медиа и текст, добавляем информацию о типе медиа к тексту
                    if has_media and message_text and not message_text.startswith(f"[{msg_type}]"):
                        message_text = f"[{msg_type}] {message_text}"
                    
                    # Создаем простой объект для совместимости
                    message_obj = type('obj', (object,), {
                        'message_id': msg.id,
                        'text': message_text,
                        'caption': caption,
                        'type': msg_type,
                        'has_media': has_media
                    })
                    result.append(message_obj)
                
                # Выводим статистику по типам сообщений
                text_count = sum(1 for m in result if m.type == 'текст')
                media_count = sum(1 for m in result if m.has_media)
                media_with_text_count = sum(1 for m in result if m.has_media and (m.text and not m.text.startswith(f"[{m.type}]")))
                
                logger.info(f"Обработано {len(result)} сообщений из канала {entity.title} "
                           f"(текст: {text_count}, медиа: {media_count}, медиа с текстом: {media_with_text_count})")
                
                return result
                
            except FloodWaitError as e:
                # Обработка ошибки превышения лимита запросов
                wait_time = e.seconds
                logger.warning(f"Превышен лимит запросов к API. Ожидаем {wait_time} секунд")
                await asyncio.sleep(wait_time)
                return []
                
        except Exception as e:
            logger.error(f"Ошибка при получении сообщений через Telethon: {e}")
            return []
    
    async def get_recent_messages(self, channel_id, limit=100):
        """Получает последние сообщения из канала, используя только Telethon"""
        try:
            # Проверяем, что Telethon клиент доступен
            if not self.client or not self.client.is_connected():
                logger.error(f"Telethon клиент не инициализирован или не подключен")
                return []
                
            logger.info(f"Пробуем получить сообщения из канала {channel_id} через Telethon")
            messages = await self.get_recent_messages_telethon(channel_id, limit)
            
            if not messages:
                logger.warning(f"Не удалось получить сообщения из канала {channel_id}")
                return []
                
            return messages
            
        except Exception as e:
            logger.error(f"Ошибка при получении сообщений из канала {channel_id}: {e}")
            return []
    
    async def process_channel(self, channel):
        """Обрабатывает последние сообщения из канала"""
        channel_id = channel['channel_id']
        
        try:
            # Проверяем, первый ли это запуск для данного канала
            async with self.db.pool.acquire() as conn:
                first_run = await conn.fetchval(
                    'SELECT NOT EXISTS(SELECT 1 FROM processed_messages WHERE channel_id = $1)',
                    str(channel_id)
                )
                
                # Получаем ID последнего обработанного сообщения
                last_message_id = await conn.fetchval(
                    'SELECT message_id FROM processed_messages WHERE channel_id = $1 ORDER BY message_id DESC LIMIT 1',
                    str(channel_id)
                )
            
            # При первом запуске получаем только 2 последних сообщения
            # При последующих запусках получаем больше сообщений для проверки новых
            limit = 5 if first_run else min(20, self.max_messages_per_channel)
            
            # Получаем последние сообщения из канала
            messages = await self.get_recent_messages(channel_id, limit=limit)
            
            if not messages:
                logger.info(f"Нет доступных сообщений в канале {channel_id}")
                return 0
            
            keywords = await self.db.get_keywords()
            stopwords = await self.db.get_stopwords()
            
            logger.info(f"Проверяем {len(messages)} сообщений из канала {channel_id} на наличие {len(keywords)} ключевых слов")
            logger.info(f"Первый запуск для канала: {first_run}, лимит сообщений: {limit}")
            
            # Обрабатываем сообщения в обратном порядке (от старых к новым)
            count_matched = 0
            for message in reversed(messages):
                # Проверяем, не обрабатывали ли мы уже это сообщение
                is_processed = await self.db.is_message_processed(channel_id, message.message_id)
                if is_processed:
                    continue
                
                # Проверяем наличие ключевых слов и отсутствие стоп-слов
                message_text = message.text or message.caption or ""
                logger.debug(f"Проверяем сообщение {message.message_id}: '{message_text[:100]}...'")
                logger.debug(f"Доступные ключевые слова: {keywords}")
                
                # Проверяем напрямую наличие слова "США" в тексте
                if 'сша' in message_text.lower():
                    logger.debug("Слово 'США' найдено в тексте напрямую!")
                
                matched = await self.check_keywords_in_message(message_text, keywords, stopwords)
                
                if matched:
                    logger.info(f"Найдено совпадение в сообщении {message.message_id} канала {channel_id}")
                    success = await self.forward_message(channel_id, message.message_id)
                    if success:
                        count_matched += 1
                        # Добавляем задержку между пересылками сообщений
                        await self.add_delay(1.0)
                else:
                    logger.debug(f"Совпадений не найдено в сообщении {message.message_id}")
                    # Отмечаем сообщение как обработанное, даже если оно не соответствует условиям
                    await self.db.mark_message_processed(channel_id, message.message_id)
            
            logger.info(f"Обработка канала {channel_id} завершена. Найдено и переслано {count_matched} сообщений")
            return count_matched
            
        except Forbidden:
            logger.error(f"Бот не имеет доступа к каналу {channel_id}, удаляем канал из списка")
            await self.db.remove_channel(channel_id)
            return 0
        except Exception as e:
            logger.error(f"Ошибка при обработке канала {channel_id}: {e}")
            return 0
    
    async def run(self):
        """Запускает процесс парсинга каналов один раз"""
        try:
            # Инициализируем Telethon клиент
            if not self.client:
                success = await self.initialize_telethon()
                if not success:
                    logger.error("Не удалось инициализировать Telethon клиент. Парсинг невозможен.")
                    return
                
            # Получаем список активных каналов
            channels = await self.db.get_channels()
            
            if not channels:
                logger.warning("Нет активных каналов для мониторинга")
            else:
                logger.info(f"Начинаем проверку {len(channels)} каналов")
                
                # Ограничиваем количество каналов для проверки
                if len(channels) > self.max_channels_per_run:
                    logger.warning(f"Слишком много каналов ({len(channels)}). Ограничиваем до {self.max_channels_per_run} для защиты от блокировки.")
                    # Перемешиваем каналы для равномерной проверки
                    random.shuffle(channels)
                    channels = channels[:self.max_channels_per_run]
                
                # Обрабатываем каждый канал с задержкой между запросами
                total_processed = 0
                for i, channel in enumerate(channels):
                    processed = await self.process_channel(channel)
                    if processed:
                        total_processed += processed
                    
                    # Добавляем задержку между каналами, кроме последнего
                    if i < len(channels) - 1:
                        delay = await self.add_delay(self.delay_between_channels)
                        logger.debug(f"Задержка {delay:.2f} сек перед следующим каналом")
            
            # Возвращаем время следующей проверки
            logger.info(f"Проверка завершена. Обработано {total_processed} сообщений. Следующая проверка через {self.check_interval} минут")
            
        except Exception as e:
            logger.error(f"Ошибка в цикле проверки: {e}")
            raise 