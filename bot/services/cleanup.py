"""
Сервис для автоматического удаления сообщений
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.types import Message


class MessageCleanupService:
    """Сервис для управления удалением сообщений"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.message_timers: Dict[int, asyncio.Task] = {}
        self.auto_delete_enabled = True
        self.default_delete_delay = 30  # секунд
    
    async def schedule_message_deletion(
        self, 
        message: Message, 
        delay_seconds: Optional[int] = None
    ) -> None:
        """
        Планирует удаление сообщения через указанное время
        
        Args:
            message: Сообщение для удаления
            delay_seconds: Задержка в секундах (по умолчанию 30)
        """
        if not self.auto_delete_enabled:
            return
        
        delay = delay_seconds or self.default_delete_delay
        
        async def delete_message():
            try:
                await asyncio.sleep(delay)
                await self.bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=message.message_id
                )
            except Exception as e:
                # Игнорируем ошибки удаления (сообщение уже удалено и т.д.)
                pass
        
        # Отменяем предыдущий таймер, если есть
        if message.message_id in self.message_timers:
            self.message_timers[message.message_id].cancel()
        
        # Создаем новый таймер
        task = asyncio.create_task(delete_message())
        self.message_timers[message.message_id] = task
    
    async def delete_message_immediately(self, message: Message) -> bool:
        """
        Немедленно удаляет сообщение
        
        Args:
            message: Сообщение для удаления
            
        Returns:
            True если удаление прошло успешно
        """
        try:
            await self.bot.delete_message(
                chat_id=message.chat.id,
                message_id=message.message_id
            )
            
            # Отменяем таймер, если есть
            if message.message_id in self.message_timers:
                self.message_timers[message.message_id].cancel()
                del self.message_timers[message.message_id]
            
            return True
        except Exception:
            return False
    
    async def cleanup_old_messages(
        self, 
        chat_id: int, 
        hours_old: int = 24
    ) -> int:
        """
        Удаляет старые сообщения в чате
        
        Args:
            chat_id: ID чата
            hours_old: Возраст сообщений в часах
            
        Returns:
            Количество удаленных сообщений
        """
        # Telegram API не предоставляет прямой способ получить историю сообщений
        # Поэтому этот метод является заглушкой для будущей реализации
        # В реальном проекте можно использовать webhook или другие методы
        
        return 0
    
    def set_auto_delete_enabled(self, enabled: bool) -> None:
        """Включает/выключает автоматическое удаление"""
        self.auto_delete_enabled = enabled
    
    def set_default_delete_delay(self, delay_seconds: int) -> None:
        """Устанавливает задержку по умолчанию для удаления"""
        self.default_delete_delay = delay_seconds
    
    async def cleanup_all_timers(self) -> None:
        """Отменяет все активные таймеры удаления"""
        for task in self.message_timers.values():
            task.cancel()
        self.message_timers.clear()
    
    def get_active_timers_count(self) -> int:
        """Возвращает количество активных таймеров"""
        return len(self.message_timers)


# Глобальный экземпляр сервиса
cleanup_service: Optional[MessageCleanupService] = None

def get_cleanup_service(bot: Bot) -> MessageCleanupService:
    """Получает глобальный экземпляр сервиса очистки"""
    global cleanup_service
    if cleanup_service is None:
        cleanup_service = MessageCleanupService(bot)
    return cleanup_service
