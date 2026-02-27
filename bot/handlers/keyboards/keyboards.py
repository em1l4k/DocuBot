from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from bot.rbac import Role, Permission


def get_main_keyboard(current_user) -> ReplyKeyboardMarkup:
    """Создает основную клавиатуру в зависимости от роли пользователя"""
    buttons = [
        [KeyboardButton(text="📄 Мои документы"), KeyboardButton(text="🔍 Поиск")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="📤 Загрузить документ")]
    ]
    
    # Добавляем кнопки для согласования (менеджеры и админы)
    if current_user.has_permission(Permission.APPROVE_DOCUMENTS):
        buttons.append([KeyboardButton(text="⏳ На согласование")])
    
    # Добавляем кнопки для напоминаний
    buttons.append([KeyboardButton(text="⏰ Напоминания")])
    
    # Добавляем кнопки для архива
    buttons.append([KeyboardButton(text="📦 Архив")])
    
    # Добавляем кнопки для админов
    if current_user.role == Role.admin:
        buttons.append([KeyboardButton(text="🛠️ Админ-панель")])
    
    # Добавляем кнопку помощи
    buttons.append([KeyboardButton(text="❓ Помощь")])
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_search_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для поиска"""
    buttons = [
        [KeyboardButton(text="🔍 Поиск"), KeyboardButton(text="📅 Недавние")],
        [KeyboardButton(text="⚠️ Просроченные"), KeyboardButton(text="📋 Фильтры")],
        [KeyboardButton(text="🔙 Главное меню")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_archive_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для архива"""
    buttons = [
        [KeyboardButton(text="📦 Архивные документы"), KeyboardButton(text="📊 Статистика архива")],
        [KeyboardButton(text="🔙 Главное меню")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_reminders_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для напоминаний"""
    buttons = [
        [KeyboardButton(text="⚠️ Просроченные"), KeyboardButton(text="⏰ Приближающиеся")],
        [KeyboardButton(text="📊 Статистика напоминаний")],
        [KeyboardButton(text="🔙 Главное меню")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для админов"""
    buttons = [
        [KeyboardButton(text="👥 Пользователи"), KeyboardButton(text="📊 Система")],
        [KeyboardButton(text="⚠️ Все просроченные"), KeyboardButton(text="📦 Архив")],
        [KeyboardButton(text="🔄 Перезагрузить whitelist")],
        [KeyboardButton(text="🔙 Главное меню")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )
