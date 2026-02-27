"""
Команды для работы с архивом документов
"""
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from bot.services.archive import ArchiveService
from bot.rbac import Permission
from datetime import datetime


async def archive_command(message: Message, current_user):
    """Команда архивации документа"""
    try:
        # Парсим аргументы команды
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        
        if not args:
            await message.answer(
                "📦 <b>Архивация документов</b>\n\n"
                "Использование:\n"
                "• <code>/archive document_id</code> - архивировать документ\n"
                "• <code>/archive document_id причина</code> - с причиной\n\n"
                "Примеры:\n"
                "• <code>/archive a1b2c3d4</code>\n"
                "• <code>/archive a1b2c3d4 Документ устарел</code>",
                parse_mode="HTML"
            )
            return
        
        document_id = args[0]
        reason = " ".join(args[1:]) if len(args) > 1 else None
        
        archive_service = ArchiveService()
        
        # Архивируем документ
        success = archive_service.archive_document(
            document_id=document_id,
            user_id=message.from_user.id,
            reason=reason
        )
        
        if success:
            await message.answer(
                f"✅ <b>Документ заархивирован</b>\n\n"
                f"🆔 ID: <code>{document_id}</code>\n"
                f"📦 Статус: Архивирован\n"
                f"💬 Причина: {reason or 'Не указана'}",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "❌ <b>Ошибка архивации</b>\n\n"
                "Возможные причины:\n"
                "• Документ не найден\n"
                "• Нет прав на архивацию\n"
                "• Документ уже заархивирован",
                parse_mode="HTML"
            )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка архивации: {e}")


async def unarchive_command(message: Message, current_user):
    """Команда разархивации документа (только для админов)"""
    if not current_user.has_permission(Permission.MANAGE_DOCUMENTS):
        await message.answer("❌ У вас нет прав на разархивацию документов.")
        return
    
    try:
        # Парсим аргументы команды
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        
        if not args:
            await message.answer(
                "📦 <b>Разархивация документов</b>\n\n"
                "Использование:\n"
                "• <code>/unarchive document_id</code> - разархивировать документ\n\n"
                "Пример:\n"
                "• <code>/unarchive a1b2c3d4</code>",
                parse_mode="HTML"
            )
            return
        
        document_id = args[0]
        
        archive_service = ArchiveService()
        
        # Разархивируем документ
        success = archive_service.unarchive_document(
            document_id=document_id,
            user_id=message.from_user.id
        )
        
        if success:
            await message.answer(
                f"✅ <b>Документ разархивирован</b>\n\n"
                f"🆔 ID: <code>{document_id}</code>\n"
                f"📦 Статус: Одобрен",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "❌ <b>Ошибка разархивации</b>\n\n"
                "Возможные причины:\n"
                "• Документ не найден\n"
                "• Документ не заархивирован\n"
                "• Нет прав на разархивацию",
                parse_mode="HTML"
            )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка разархивации: {e}")


async def archived_command(message: Message, current_user):
    """Показывает архивные документы пользователя"""
    try:
        archive_service = ArchiveService()
        
        # Получаем архивные документы
        archived_docs = archive_service.get_archived_documents(
            user_id=message.from_user.id,
            limit=20
        )
        
        if not archived_docs:
            await message.answer("📦 У вас нет архивных документов.")
            return
        
        text = f"📦 <b>Архивные документы ({len(archived_docs)}):</b>\n\n"
        
        for i, doc in enumerate(archived_docs, 1):
            title = doc.get("title", "Без названия")
            kind = doc.get("kind", "other")
            archived_at = doc.get("archived_at")
            archive_reason = doc.get("archive_reason", "")
            version_id = doc.get("version_id")
            
            # Форматируем дату архивации
            date_str = ""
            if archived_at:
                date_str = archived_at.strftime("%d.%m.%Y") if hasattr(archived_at, 'strftime') else str(archived_at)
            
            text += f"{i}. 📦 <b>{title}</b>\n"
            text += f"   📁 {kind}"
            if date_str:
                text += f" • {date_str}"
            if archive_reason:
                text += f"\n   💬 {archive_reason}"
            text += "\n\n"
        
        # Добавляем кнопки для скачивания
        keyboard_buttons = []
        for doc in archived_docs[:5]:  # Показываем кнопки только для первых 5
            if doc.get("version_id"):
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"⬇️ {doc['title'][:20]}...",
                        callback_data=f"dl:{doc['version_id']}"
                    )
                ])
        
        if keyboard_buttons:
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения архивных документов: {e}")


async def archive_stats_command(message: Message, current_user):
    """Показывает статистику архива (только для админов)"""
    if not current_user.has_permission(Permission.VIEW_STATISTICS):
        await message.answer("❌ У вас нет прав на просмотр статистики архива.")
        return
    
    try:
        archive_service = ArchiveService()
        stats = archive_service.get_archive_stats()
        
        text = "📦 <b>Статистика архива</b>\n\n"
        
        # Общая информация
        text += f"📊 <b>Общая информация:</b>\n"
        text += f"• Всего архивных документов: {stats['total_archived']}\n\n"
        
        # По типам
        if stats['by_kind']:
            text += f"📁 <b>По типам:</b>\n"
            for kind, count in stats['by_kind'].items():
                kind_emoji = {
                    'order': '📋',
                    'memo': '📝',
                    'request': '📄',
                    'other': '📎'
                }.get(kind, '📎')
                text += f"• {kind_emoji} {kind}: {count}\n"
            text += "\n"
        
        # По месяцам
        if stats['by_month']:
            text += f"📈 <b>Архивация по месяцам:</b>\n"
            for month_data in stats['by_month'][-6:]:  # Последние 6 месяцев
                month = month_data['month']
                count = month_data['count']
                text += f"• {month}: {count} документов\n"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения статистики архива: {e}")


async def auto_archive_command(message: Message, current_user):
    """Автоматическая архивация старых документов (только для админов)"""
    if not current_user.has_permission(Permission.MANAGE_DOCUMENTS):
        await message.answer("❌ У вас нет прав на автоматическую архивацию.")
        return
    
    try:
        # Парсим аргументы команды
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        
        days_threshold = 365  # По умолчанию 1 год
        if args:
            try:
                days_threshold = int(args[0])
            except ValueError:
                await message.answer("❌ Неверный формат количества дней.")
                return
        
        archive_service = ArchiveService()
        
        # Выполняем автоматическую архивацию
        archived_count = archive_service.auto_archive_old_documents(days_threshold)
        
        await message.answer(
            f"✅ <b>Автоматическая архивация завершена</b>\n\n"
            f"📦 Заархивировано документов: {archived_count}\n"
            f"📅 Порог: старше {days_threshold} дней\n"
            f"⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode="HTML"
        )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка автоматической архивации: {e}")
