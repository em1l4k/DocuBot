"""
Обработчики навигации и кнопок клавиатуры
"""
from aiogram.types import Message
from bot.handlers.keyboards.keyboards import (
    get_main_keyboard, get_search_keyboard, get_archive_keyboard,
    get_reminders_keyboard, get_admin_keyboard
)
from bot.handlers.commands.statistics import my_stats_command, storage_stats_command
from bot.handlers.commands.search import search_command, recent_command, search_overdue_command, filters_command
from bot.handlers.commands.archive import archived_command, archive_stats_command
from bot.handlers.commands.reminders import (
    reminders_overdue_command, approaching_command, reminder_stats_command
)
from bot.handlers.commands.admin_advanced import (
    admin_panel_command, users_command, system_stats_command, overdue_all_command
)
from bot.rbac import Permission


async def handle_search_button(message: Message, current_user):
    """Обработчик кнопки '🔍 Поиск'"""
    await message.answer(
        "🔍 <b>Поиск документов</b>\n\n"
        "Используйте кнопки ниже для поиска и фильтрации документов:",
        reply_markup=get_search_keyboard(),
        parse_mode="HTML"
    )


async def handle_statistics_button(message: Message, current_user):
    """Обработчик кнопки '📊 Статистика'"""
    await my_stats_command(message, current_user)


async def handle_reminders_button(message: Message, current_user):
    """Обработчик кнопки '⏰ Напоминания'"""
    await message.answer(
        "⏰ <b>Напоминания и дедлайны</b>\n\n"
        "Используйте кнопки ниже для работы с напоминаниями:",
        reply_markup=get_reminders_keyboard(),
        parse_mode="HTML"
    )


async def handle_archive_button(message: Message, current_user):
    """Обработчик кнопки '📦 Архив'"""
    await message.answer(
        "📦 <b>Архив документов</b>\n\n"
        "Используйте кнопки ниже для работы с архивом:",
        reply_markup=get_archive_keyboard(),
        parse_mode="HTML"
    )


async def handle_admin_button(message: Message, current_user):
    """Обработчик кнопки '🛠️ Админ-панель'"""
    await message.answer(
        "🛠️ <b>Админ-панель</b>\n\n"
        "Используйте кнопки ниже для администрирования:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )


async def handle_help_button(message: Message, current_user):
    """Обработчик кнопки '❓ Помощь'"""
    from bot.handlers.commands.help import help_command
    await help_command(message, current_user)


async def handle_main_menu_button(message: Message, current_user):
    """Обработчик кнопки '🔙 Главное меню'"""
    await message.answer(
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard(current_user),
        parse_mode="HTML"
    )


# Обработчики для клавиатуры поиска
async def handle_search_search_button(message: Message, current_user):
    """Обработчик кнопки '🔍 Поиск' в меню поиска"""
    await message.answer(
        "🔍 <b>Поиск документов</b>\n\n"
        "Используйте команду /search с параметрами:\n"
        "• <code>/search отчет</code> - поиск по названию\n"
        "• <code>/search status:approved</code> - по статусу\n"
        "• <code>/search kind:order</code> - по типу\n\n"
        "Примеры:\n"
        "• <code>/search отчет status:approved</code>\n"
        "• <code>/search kind:order status:in_review</code>",
        parse_mode="HTML"
    )


async def handle_recent_button(message: Message, current_user):
    """Обработчик кнопки '📅 Недавние'"""
    await recent_command(message, current_user)


async def handle_overdue_button(message: Message, current_user):
    """Обработчик кнопки '⚠️ Просроченные'"""
    await search_overdue_command(message, current_user)


async def handle_filters_button(message: Message, current_user):
    """Обработчик кнопки '📋 Фильтры'"""
    await filters_command(message, current_user)


# Обработчики для клавиатуры архива
async def handle_archived_documents_button(message: Message, current_user):
    """Обработчик кнопки '📦 Архивные документы'"""
    await archived_command(message, current_user)


async def handle_archive_stats_button(message: Message, current_user):
    """Обработчик кнопки '📊 Статистика архива'"""
    await archive_stats_command(message, current_user)


# Обработчики для клавиатуры напоминаний
async def handle_reminders_overdue_button(message: Message, current_user):
    """Обработчик кнопки '⚠️ Просроченные' в меню напоминаний"""
    await reminders_overdue_command(message, current_user)


async def handle_approaching_button(message: Message, current_user):
    """Обработчик кнопки '⏰ Приближающиеся'"""
    await approaching_command(message, current_user)


async def handle_reminder_stats_button(message: Message, current_user):
    """Обработчик кнопки '📊 Статистика напоминаний'"""
    await reminder_stats_command(message, current_user)


# Обработчики для админской клавиатуры
async def handle_users_button(message: Message, current_user):
    """Обработчик кнопки '👥 Пользователи'"""
    await users_command(message, current_user)


async def handle_system_button(message: Message, current_user):
    """Обработчик кнопки '📊 Система'"""
    await system_stats_command(message, current_user)


async def handle_all_overdue_button(message: Message, current_user):
    """Обработчик кнопки '⚠️ Все просроченные'"""
    await overdue_all_command(message, current_user)


async def handle_admin_archive_button(message: Message, current_user):
    """Обработчик кнопки '📦 Архив' в админ-панели"""
    await message.answer(
        "📦 <b>Управление архивом</b>\n\n"
        "Используйте команды:\n"
        "• <code>/archived</code> - архивные документы\n"
        "• <code>/archive_stats</code> - статистика архива\n"
        "• <code>/archive [id] [причина]</code> - архивировать\n"
        "• <code>/unarchive [id]</code> - разархивировать\n"
        "• <code>/auto_archive [дни]</code> - автоматическая архивация",
        parse_mode="HTML"
    )


async def handle_reload_whitelist_button(message: Message, current_user):
    """Обработчик кнопки '🔄 Перезагрузить whitelist'"""
    from bot.handlers.commands.admin import reload_whitelist_command
    from bot.rbac import get_global_store
    
    # Получаем глобальный экземпляр store
    store = get_global_store()
    if not store:
        await message.answer("❌ Ошибка: store не инициализирован")
        return
    
    # Принудительно обновляем глобальный store
    import bot.main
    if hasattr(bot.main, 'store'):
        bot.main.store.cache.clear()
        bot.main.store.reload()
    
    await reload_whitelist_command(message, current_user, store)
