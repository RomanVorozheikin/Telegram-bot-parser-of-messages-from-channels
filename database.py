import asyncpg
from loguru import logger
import config

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            
            # Создаем таблицу для хранения информации о каналах и ключевых словах
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS channels (
                        id SERIAL PRIMARY KEY,
                        channel_id TEXT UNIQUE NOT NULL,
                        name TEXT,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                ''')
                
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS keywords (
                        id SERIAL PRIMARY KEY,
                        word TEXT UNIQUE NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                ''')
                
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS stopwords (
                        id SERIAL PRIMARY KEY,
                        word TEXT UNIQUE NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                ''')
                
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS processed_messages (
                        id SERIAL PRIMARY KEY,
                        channel_id TEXT NOT NULL,
                        message_id BIGINT NOT NULL,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(channel_id, message_id)
                    )
                ''')
            
            logger.info("База данных успешно подключена и инициализирована")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к базе данных: {e}")
            return False

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def add_channel(self, channel_id, name=None):
        async with self.pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO channels (channel_id, name) VALUES ($1, $2) ON CONFLICT (channel_id) DO UPDATE SET name = $2',
                channel_id, name
            )
    
    async def remove_channel(self, channel_id):
        async with self.pool.acquire() as conn:
            await conn.execute(
                'DELETE FROM channels WHERE channel_id = $1',
                channel_id
            )
    
    async def get_channels(self):
        async with self.pool.acquire() as conn:
            channels = await conn.fetch('SELECT * FROM channels WHERE is_active = TRUE')
            return channels
    
    async def add_keyword(self, word):
        async with self.pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO keywords (word) VALUES ($1) ON CONFLICT (word) DO UPDATE SET is_active = TRUE',
                word
            )
    
    async def remove_keyword(self, word):
        async with self.pool.acquire() as conn:
            await conn.execute(
                'DELETE FROM keywords WHERE word = $1',
                word
            )
    
    async def get_keywords(self):
        async with self.pool.acquire() as conn:
            keywords = await conn.fetch('SELECT * FROM keywords WHERE is_active = TRUE')
            return [k['word'] for k in keywords]
    
    async def add_stopword(self, word):
        async with self.pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO stopwords (word) VALUES ($1) ON CONFLICT (word) DO UPDATE SET is_active = TRUE',
                word
            )
    
    async def remove_stopword(self, word):
        async with self.pool.acquire() as conn:
            await conn.execute(
                'DELETE FROM stopwords WHERE word = $1',
                word
            )
    
    async def get_stopwords(self):
        async with self.pool.acquire() as conn:
            stopwords = await conn.fetch('SELECT * FROM stopwords WHERE is_active = TRUE')
            return [s['word'] for s in stopwords]
    
    async def mark_message_processed(self, channel_id, message_id):
        async with self.pool.acquire() as conn:
            try:
                # Преобразуем channel_id в строку для единообразия
                if not isinstance(channel_id, str):
                    channel_id = str(channel_id)
                    
                await conn.execute(
                    'INSERT INTO processed_messages (channel_id, message_id) VALUES ($1, $2) ON CONFLICT DO NOTHING',
                    channel_id, message_id
                )
            except Exception as e:
                logger.error(f"Ошибка при пометке сообщения как обработанного: {e}")
    
    async def is_message_processed(self, channel_id, message_id):
        async with self.pool.acquire() as conn:
            try:
                # Преобразуем channel_id в строку для единообразия
                if not isinstance(channel_id, str):
                    channel_id = str(channel_id)
                    
                result = await conn.fetchval(
                    'SELECT EXISTS(SELECT 1 FROM processed_messages WHERE channel_id = $1 AND message_id = $2)',
                    channel_id, message_id
                )
                return result
            except Exception as e:
                logger.error(f"Ошибка при проверке статуса обработки сообщения: {e}")
                return False 