import asyncio
import logging
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError, BadRequest, Forbidden
from database import Database
from parser import MessageParser

logger = logging.getLogger(__name__)

class MessageScheduler:
    """Планировщик для периодического запуска парсера сообщений."""
    
    def __init__(self, db, target_channel_id, check_interval=3, signature="", telethon_client=None):
        """Инициализирует планировщик.
        
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
        self.is_running = False
        self.parser = MessageParser(db, target_channel_id, check_interval, signature, telethon_client=telethon_client)
        self._task = None
        
    def start(self):
        """Запускает планировщик."""
        if self.is_running:
            logger.warning("Планировщик уже запущен")
            return
            
        self.is_running = True
        # Создаем задачу с использованием базового цикла событий
        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._run())
        logger.info("Планировщик запущен")
        
    def stop(self):
        """Останавливает планировщик."""
        if not self.is_running:
            logger.warning("Планировщик не запущен")
            return
            
        self.is_running = False
        if self._task:
            self._task.cancel()
        logger.info("Планировщик остановлен")
        
    async def _run(self):
        """Запускает периодическую проверку каналов."""
        try:
            while self.is_running:
                try:
                    # Запускаем парсер
                    logger.info(f"Запуск проверки каналов в {datetime.now().strftime('%H:%M:%S')}")
                    await self.parser.run()
                    
                    # Ждем указанный интервал перед следующей проверкой
                    logger.info(f"Следующая проверка через {self.check_interval} минут")
                    await asyncio.sleep(self.check_interval * 60)
                except Exception as e:
                    logger.error(f"Ошибка при выполнении планировщика: {e}")
                    # Короткая пауза перед повторной попыткой в случае ошибки
                    await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("Задача планировщика отменена")
            raise 