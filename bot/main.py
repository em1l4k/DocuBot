import asyncio
import logging
from io import BytesIO
from pathlib import Path

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from bot import config
from bot.config import BOT_TOKEN, WHITELIST_PATH, MAX_FILE_MB, ALLOWED_MIME, ALLOWED_EXT
from bot.db.init_schema import init_schema
from bot.middlewares.rbac import RBACMiddleware
from bot.rbac import WhitelistStore, Role
from bot.services.repo import get_version_info_by_id, ensure_file, create_document, add_version
from bot.services.storage import get_object_bytes, upload_bytes, presigned_get_url, ensure_bucket

# Импорты из handlers
from bot.handlers import (
    get_main_keyboard, start_command, profile_command, my_docs_command,
    reload_whitelist_command
)
from bot.handlers.commands.approval import (
    pending_approvals_command, approval_history_command, approval_stats_command
)
from bot.handlers.commands.approval_callbacks import (
    handle_approve_callback, handle_reject_callback, 
    handle_history_callback, handle_details_callback
)

# Новые импорты для расширенного функционала
from bot.handlers.commands.statistics import (
    stats_command, my_stats_command, storage_stats_command
)
from bot.handlers.commands.search import (
    search_command, filters_command, recent_command, search_overdue_command
)
from bot.handlers.commands.archive import (
    archive_command, unarchive_command, archived_command, 
    archive_stats_command, auto_archive_command
)
from bot.handlers.commands.reminders import (
    reminders_overdue_command, approaching_command, reminder_stats_command, my_reminder_stats_command
)
from bot.handlers.commands.admin_advanced import (
    admin_panel_command, users_command, system_stats_command,
    overdue_all_command, user_stats_command
)
from bot.handlers.commands.help import (
    help_command, commands_command, keep_command, cleanup_command, keyboard_command
)
from bot.handlers.commands.navigation import (
    handle_search_button, handle_statistics_button, handle_reminders_button,
    handle_archive_button, handle_admin_button, handle_help_button,
    handle_main_menu_button, handle_recent_button, handle_overdue_button,
    handle_filters_button, handle_archived_documents_button, handle_archive_stats_button,
    handle_reminders_overdue_button, handle_approaching_button, handle_reminder_stats_button,
    handle_users_button, handle_system_button, handle_all_overdue_button,
    handle_admin_archive_button, handle_reload_whitelist_button
)
from bot.services.cleanup import get_cleanup_service
from bot.services.cache import init_cache_service, cleanup_cache_periodically
from bot.utils import bytes_to_human, short_type

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")  # важно для 3.7+
)

init_schema()
dp = Dispatcher()

# === RBAC ===
store = WhitelistStore(WHITELIST_PATH)

# Подключаем проверку для сообщений и колбеков
dp.message.middleware(RBACMiddleware(store))
dp.callback_query.middleware(RBACMiddleware(store))

# === КЛАВИАТУРЫ ===
# Клавиатуры вынесены в bot/handlers/keyboards/main.py


async def on_startup() -> None:
    """Инициализация при запуске бота"""
    logging.info("Инициализация бота...")
    ensure_bucket()
    
    # Инициализируем сервис очистки сообщений
    cleanup_service = get_cleanup_service(bot)
    cleanup_service.set_auto_delete_enabled(True)
    cleanup_service.set_default_delete_delay(30)  # 30 секунд
    
    # Инициализируем кэш
    init_cache_service(default_ttl=300)  # 5 минут по умолчанию
    
    # Запускаем периодическую очистку кэша
    asyncio.create_task(cleanup_cache_periodically(interval=60))
    
    logging.info("Бот готов к работе!")

async def check_bot_conflicts() -> bool:
    """Проверяет, нет ли конфликтов с другими экземплярами бота"""
    try:
        # Пробуем получить информацию о боте
        me = await bot.get_me()
        logging.info(f"Бот @{me.username} готов к работе")
        return True
    except Exception as e:
        if "Conflict" in str(e):
            logging.error("Обнаружен конфликт с другим экземпляром бота")
            return False
        logging.error(f"Ошибка при проверке бота: {e}")
        return False

@dp.message(CommandStart())
async def on_start(message: Message, current_user):
    await start_command(message, current_user)

# Функция bytes_to_human перенесена в bot/utils.py

# Функция short_type перенесена в bot/utils.py

@dp.message(F.document)
async def on_doc(message: Message):
    """Обработчик загрузки документов с улучшенной логикой"""
    doc = message.document

    # --- валидация файла ---
    size_ok = doc.file_size is None or doc.file_size <= MAX_FILE_MB * 1024 * 1024
    ext = Path(doc.file_name or "").suffix.lower()
    mime_ok = (doc.mime_type in ALLOWED_MIME) or (ext in ALLOWED_EXT)
    
    if not size_ok:
        await message.answer(f"❌ Файл слишком большой. Максимум: {MAX_FILE_MB} МБ.")
        return
    if not mime_ok:
        await message.answer("❌ Допустимы только PDF и DOCX файлы.")
        return

    # --- скачиваем файл ---
    try:
        buf = BytesIO()
        await bot.download(doc, destination=buf)
        data = buf.getvalue()
    except Exception as e:
        logging.error(f"Ошибка скачивания файла: {e}")
        await message.answer("❌ Ошибка при скачивании файла. Попробуйте еще раз.")
        return

    # --- загружаем в MinIO с новой структурой папок ---
    try:
        key, sha256, size = upload_bytes(
            user_id=message.from_user.id,
            title=doc.file_name,
            data=data,
            mime=doc.mime_type or "application/octet-stream",
            ext=ext if ext in {".pdf", ".docx"} else "",
        )
    except Exception as e:
        logging.error(f"Ошибка загрузки в MinIO: {e}")
        await message.answer("❌ Ошибка при сохранении файла в хранилище.")
        return

    # --- сохраняем метаданные в БД ---
    try:
        file_id = ensure_file(
            minio_key=key,
            sha256=sha256,
            mime=doc.mime_type or "application/octet-stream",
            ext=ext or "",
            size_bytes=size,
        )
        
        # Создаем документ
        doc_id = create_document(
            title=doc.file_name or "Без названия",
            kind="other",
            owner_tg_id=message.from_user.id,
        )
        
        # Добавляем версию
        ver_id, ver_no = add_version(
            document_id=doc_id,
            file_id=file_id,
            author_tg_id=message.from_user.id,
        )
        
        # --- СОЗДАНИЕ WORKFLOW СОГЛАСОВАНИЯ ---
        from bot.services.workflow import create_approval_workflow
        from bot.rbac import Role
        from datetime import datetime, timedelta
        
        # Получаем информацию о пользователе
        current_user = store.get(message.from_user.id)
        approvers = []
        workflow_created = False
        
        if current_user:
            if current_user.role == Role.employee:
                # Сотрудники нуждаются в согласовании от менеджера
                # TODO: Получить менеджера из структуры организации
                approvers = [579583676]  # ID админа как fallback
            elif current_user.role == Role.manager:
                # Менеджеры могут создавать документы с согласованием от админа
                approvers = [579583676]  # ID админа
            elif current_user.role == Role.admin:
                # Админы могут создавать документы без согласования
                approvers = []
        
        # Создаем workflow если нужны согласующие
        if approvers:
            try:
                deadlines = [datetime.now() + timedelta(days=3)]  # Дедлайн 3 дня
                create_approval_workflow(doc_id, approvers, deadlines)
                workflow_created = True
            except Exception as e:
                logging.error(f"Ошибка создания workflow: {e}")
                # Продолжаем без workflow
            
    except Exception as e:
        logging.exception("Ошибка сохранения в БД")
        await message.answer(
            "⚠️ <b>Частичная ошибка сохранения</b>\n\n"
            "Файл сохранен в хранилище, но метаданные в БД не созданы.\n"
            "Обратитесь к администратору."
        )
        return

    # --- формируем ответ пользователю ---
    human_size = bytes_to_human(size)
    simple_type = short_type(doc.file_name, doc.mime_type)
    
    # Статус workflow
    workflow_status = ""
    if workflow_created:
        workflow_status = "\n🔄 <b>Отправлен на согласование</b>"
    elif current_user and current_user.role == Role.admin:
        workflow_status = "\n✅ <b>Создан администратором</b>"
    
    # Создаем ссылку для скачивания
    try:
        url = presigned_get_url(key)
        url_text = f"\n🔗 <b>Ссылка для скачивания:</b>\n<code>{url}</code>\n<i>(действует {config.PRESIGN_TTL_MIN} мин)</i>"
    except Exception as e:
        logging.error(f"Ошибка создания ссылки: {e}")
        url_text = "\n⚠️ <i>Ссылка для скачивания недоступна</i>"
    
    await message.answer(
        "✅ <b>Документ успешно сохранен!</b>\n\n"
        f"📄 <b>Название:</b> {doc.file_name}\n"
        f"🆔 <b>ID документа:</b> <code>{doc_id[:8]}</code>\n"
        f"📊 <b>Версия:</b> v{ver_no}\n"
        f"📁 <b>Тип:</b> {simple_type}\n"
        f"💾 <b>Размер:</b> {human_size}\n"
        f"🔐 <b>Хэш:</b> <code>{sha256[:10]}…</code>{workflow_status}{url_text}",
        parse_mode="HTML"
    )


@dp.message(Command("profile"))
async def my_profile(message: Message, current_user):
    await profile_command(message, current_user)

# === ОБРАБОТЧИКИ КНОПОК ===
# Старые обработчики кнопок удалены - используются новые из navigation.py

# === ОБРАБОТЧИКИ СОГЛАСОВАНИЯ ===
@dp.message(Command("pending"))
async def pending_approvals_handler(message: Message, current_user):
    await pending_approvals_command(message, current_user)

@dp.message(Command("approval_history"))
async def approval_history_handler(message: Message, current_user):
    await approval_history_command(message, current_user)

@dp.message(Command("approval_stats"))
async def approval_stats_handler(message: Message, current_user):
    await approval_stats_command(message, current_user)

# Обработчик кнопки "⏳ На согласование" удален - используется новый из navigation.py

@dp.callback_query(F.data.startswith("dl:"))
async def on_download_btn(call: types.CallbackQuery):
    try:
        _, version_id = call.data.split(":", 1)   # <-- БЕЗ int()
    except Exception:
        await call.answer("Некорректная ссылка", show_alert=True)
        return

    info = get_version_info_by_id(version_id)     # <-- передаём строковый UUID
    if not info:
        await call.answer("Документ не найден", show_alert=True)
        return

    key = info["minio_key"]
    data = get_object_bytes(key)
    filename = (info.get("title") or "document") + (info.get("ext") or "")
    await call.message.answer_document(
        document=BufferedInputFile(data, filename=filename)
    )
    await call.answer()

# === CALLBACK ОБРАБОТЧИКИ СОГЛАСОВАНИЯ ===
@dp.callback_query(F.data.startswith("approve:"))
async def on_approve_callback(call: types.CallbackQuery, current_user):
    await handle_approve_callback(call, current_user)

@dp.callback_query(F.data.startswith("reject:"))
async def on_reject_callback(call: types.CallbackQuery, current_user):
    await handle_reject_callback(call, current_user)

@dp.callback_query(F.data.startswith("history:"))
async def on_history_callback(call: types.CallbackQuery, current_user):
    await handle_history_callback(call, current_user)

@dp.callback_query(F.data.startswith("details:"))
async def on_details_callback(call: types.CallbackQuery, current_user):
    await handle_details_callback(call, current_user)

@dp.callback_query(F.data == "back_to_docs")
async def on_back_callback(call: types.CallbackQuery, current_user):
    """Обработчик кнопки Назад"""
    await call.message.edit_text(
        "🔙 Возврат к списку документов.\n\n"
        "Используйте кнопку '⏳ На согласование' для просмотра документов.",
        parse_mode="HTML"
    )
    await call.answer()

# === НОВЫЕ КОМАНДЫ ===

# Статистика
@dp.message(Command("stats"))
async def stats_handler(message: Message, current_user):
    await stats_command(message, current_user)

@dp.message(Command("my_stats"))
async def my_stats_handler(message: Message, current_user):
    await my_stats_command(message, current_user)

@dp.message(Command("storage_stats"))
async def storage_stats_handler(message: Message, current_user):
    await storage_stats_command(message, current_user)

# Поиск
@dp.message(Command("search"))
async def search_handler(message: Message, current_user):
    await search_command(message, current_user)

@dp.message(Command("filters"))
async def filters_handler(message: Message, current_user):
    await filters_command(message, current_user)

@dp.message(Command("recent"))
async def recent_handler(message: Message, current_user):
    await recent_command(message, current_user)

@dp.message(Command("overdue"))
async def overdue_handler(message: Message, current_user):
    await reminders_overdue_command(message, current_user)

# Архив
@dp.message(Command("archive"))
async def archive_handler(message: Message, current_user):
    await archive_command(message, current_user)

@dp.message(Command("unarchive"))
async def unarchive_handler(message: Message, current_user):
    await unarchive_command(message, current_user)

@dp.message(Command("archived"))
async def archived_handler(message: Message, current_user):
    await archived_command(message, current_user)

@dp.message(Command("archive_stats"))
async def archive_stats_handler(message: Message, current_user):
    await archive_stats_command(message, current_user)

@dp.message(Command("auto_archive"))
async def auto_archive_handler(message: Message, current_user):
    await auto_archive_command(message, current_user)

# Напоминания
@dp.message(Command("approaching"))
async def approaching_handler(message: Message, current_user):
    await approaching_command(message, current_user)

@dp.message(Command("reminder_stats"))
async def reminder_stats_handler(message: Message, current_user):
    await reminder_stats_command(message, current_user)

@dp.message(Command("my_reminder_stats"))
async def my_reminder_stats_handler(message: Message, current_user):
    await my_reminder_stats_command(message, current_user)

# Админ-панель
@dp.message(Command("admin"))
async def admin_panel_handler(message: Message, current_user):
    await admin_panel_command(message, current_user)

@dp.message(Command("users"))
async def users_handler(message: Message, current_user):
    await users_command(message, current_user)

@dp.message(Command("system_stats"))
async def system_stats_handler(message: Message, current_user):
    await system_stats_command(message, current_user)

@dp.message(Command("overdue_all"))
async def overdue_all_handler(message: Message, current_user):
    await overdue_all_command(message, current_user)

@dp.message(Command("user_stats"))
async def user_stats_handler(message: Message, current_user):
    await user_stats_command(message, current_user)

# Новые команды помощи
@dp.message(Command("help"))
async def help_handler(message: Message, current_user):
    await help_command(message, current_user)

@dp.message(Command("commands"))
async def commands_handler(message: Message, current_user):
    await commands_command(message, current_user)

@dp.message(Command("keep"))
async def keep_handler(message: Message, current_user):
    await keep_command(message, current_user)

@dp.message(Command("cleanup"))
async def cleanup_handler(message: Message, current_user):
    await cleanup_command(message, current_user)

@dp.message(Command("keyboard"))
async def keyboard_handler(message: Message, current_user):
    await keyboard_command(message, current_user)

# Обработчики кнопок клавиатуры
@dp.message(lambda message: message.text == "🔍 Поиск")
async def search_button_handler(message: Message, current_user):
    await handle_search_button(message, current_user)

@dp.message(lambda message: message.text == "👤 Профиль")
async def profile_button_handler(message: Message, current_user):
    await profile_command(message, current_user)

@dp.message(lambda message: message.text == "📄 Мои документы")
async def my_docs_button_handler(message: Message, current_user):
    await my_docs_command(message, current_user)

@dp.message(lambda message: message.text == "⏳ На согласование")
async def pending_approvals_button_handler(message: Message, current_user):
    await pending_approvals_command(message, current_user)

@dp.message(lambda message: message.text == "📊 Статистика")
async def statistics_button_handler(message: Message, current_user):
    await handle_statistics_button(message, current_user)

@dp.message(lambda message: message.text == "⏰ Напоминания")
async def reminders_button_handler(message: Message, current_user):
    await handle_reminders_button(message, current_user)

@dp.message(lambda message: message.text == "📦 Архив")
async def archive_button_handler(message: Message, current_user):
    await handle_archive_button(message, current_user)

@dp.message(lambda message: message.text == "🛠️ Админ-панель")
async def admin_button_handler(message: Message, current_user):
    await handle_admin_button(message, current_user)

@dp.message(lambda message: message.text == "❓ Помощь")
async def help_button_handler(message: Message, current_user):
    await handle_help_button(message, current_user)

@dp.message(lambda message: message.text == "🔙 Главное меню")
async def main_menu_button_handler(message: Message, current_user):
    await handle_main_menu_button(message, current_user)

# Обработчики для клавиатуры поиска
@dp.message(lambda message: message.text == "📅 Недавние")
async def recent_button_handler(message: Message, current_user):
    await handle_recent_button(message, current_user)

@dp.message(lambda message: message.text == "⚠️ Просроченные")
async def overdue_button_handler(message: Message, current_user):
    await handle_overdue_button(message, current_user)

@dp.message(lambda message: message.text == "📋 Фильтры")
async def filters_button_handler(message: Message, current_user):
    await handle_filters_button(message, current_user)

# Обработчики для клавиатуры архива
@dp.message(lambda message: message.text == "📦 Архивные документы")
async def archived_documents_button_handler(message: Message, current_user):
    await handle_archived_documents_button(message, current_user)

@dp.message(lambda message: message.text == "📊 Статистика архива")
async def archive_stats_button_handler(message: Message, current_user):
    await handle_archive_stats_button(message, current_user)

# Обработчики для клавиатуры напоминаний
@dp.message(lambda message: message.text == "⏰ Приближающиеся")
async def approaching_button_handler(message: Message, current_user):
    await handle_approaching_button(message, current_user)

@dp.message(lambda message: message.text == "📊 Статистика напоминаний")
async def reminder_stats_button_handler(message: Message, current_user):
    await handle_reminder_stats_button(message, current_user)

# Обработчики для админской клавиатуры
@dp.message(lambda message: message.text == "👥 Пользователи")
async def users_button_handler(message: Message, current_user):
    await handle_users_button(message, current_user)

@dp.message(lambda message: message.text == "📊 Система")
async def system_button_handler(message: Message, current_user):
    await handle_system_button(message, current_user)

@dp.message(lambda message: message.text == "⚠️ Все просроченные")
async def all_overdue_button_handler(message: Message, current_user):
    await handle_all_overdue_button(message, current_user)

@dp.message(lambda message: message.text == "🔄 Перезагрузить whitelist")
async def reload_whitelist_button_handler(message: Message, current_user):
    await handle_reload_whitelist_button(message, current_user)

@dp.message()
async def fallback(message: Message, current_user):
    keyboard = get_main_keyboard(current_user)
    await message.answer(
        "🤔 Не понимаю эту команду.\n\n"
        "Используйте кнопки на клавиатуре или пришлите PDF/DOCX файл.",
        reply_markup=keyboard
    )

async def main():
    """Основная функция запуска бота с обработкой конфликтов"""
    try:
        # Проверяем конфликты перед запуском
        if not await check_bot_conflicts():
            logging.error("Не удалось запустить бота из-за конфликтов")
            return
        
        # Инициализация перед запуском
        await on_startup()
        
        # Запуск бота с обработкой конфликтов
        await dp.start_polling(
            bot, 
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True  # Игнорируем накопившиеся обновления
        )
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")
        if "Conflict" in str(e):
            logging.error("Конфликт: уже запущен другой экземпляр бота")
            logging.error("Остановите другие процессы и попробуйте снова")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        exit(1)