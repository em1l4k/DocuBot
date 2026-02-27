from aiogram.types import Message
from bot.rbac import Role, WhitelistStore


async def reload_whitelist_command(message: Message, current_user, store: WhitelistStore):
    """Обработчик команды /reload_whitelist"""
    if current_user.role != Role.admin:
        await message.answer("Недостаточно прав.")
        return
    count = store.reload()
    await message.answer(f"Whitelist перезагружен. Записей: {count}.")
