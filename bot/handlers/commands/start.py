from aiogram.types import Message
from bot.handlers.keyboards.keyboards import get_main_keyboard


async def start_command(message: Message, current_user):
    """Обработчик команды /start"""
    keyboard = get_main_keyboard(current_user)
    response = await message.answer(
        f"Привет, {message.from_user.full_name}!\n"
        f"Твоя роль: <b>{current_user.role.value}</b>.\n\n"
        "Выберите действие на клавиатуре или пришлите PDF/DOCX файл.",
        reply_markup=keyboard
    )
    
    # Планируем автоматическое удаление сообщения
    from bot.services.cleanup import get_cleanup_service
    from aiogram import Bot
    from bot.config import BOT_TOKEN
    
    bot = Bot(token=BOT_TOKEN)
    cleanup_service = get_cleanup_service(bot)
    await cleanup_service.schedule_message_deletion(response)
