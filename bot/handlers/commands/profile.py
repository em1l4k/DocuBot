from aiogram.types import Message


async def profile_command(message: Message, current_user):
    """Обработчик команды /profile"""
    await message.answer(
        f"👤 Профиль\n"
        f"ID: <code>{current_user.telegram_id}</code>\n"
        f"ФИО: {current_user.full_name or '—'}\n"
        f"Роль: <b>{current_user.role.value}</b>\n"
        f"Доступ: {'активен' if current_user.is_active else 'заблокирован'}"
    )
