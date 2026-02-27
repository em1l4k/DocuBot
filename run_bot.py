#!/usr/bin/env python3
"""
Скрипт для безопасного запуска бота с проверкой конфликтов
"""
import asyncio
import logging
import sys
from bot.main import main

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

async def safe_start():
    """Безопасный запуск бота"""
    try:
        logging.info("🚀 Запуск бота...")
        await main()
    except KeyboardInterrupt:
        logging.info("⏹️ Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"❌ Критическая ошибка: {e}")
        if "Conflict" in str(e):
            logging.error("💥 Конфликт: уже запущен другой экземпляр бота")
            logging.error("🔧 Решение: остановите другие процессы и попробуйте снова")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(safe_start())

