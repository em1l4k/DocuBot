"""
Команды для работы с напоминаниями и уведомлениями
"""
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from bot.services.reminders import ReminderService
from bot.rbac import Permission


async def reminders_overdue_command(message: Message, current_user):
    """Показывает просроченные документы пользователя"""
    try:
        reminder_service = ReminderService()
        
        # Получаем просроченные документы пользователя
        overdue_docs = reminder_service.get_user_overdue_documents(message.from_user.id)
        
        if not overdue_docs:
            await message.answer("✅ У вас нет просроченных документов.")
            return
        
        text = f"⚠️ <b>Просроченные документы ({len(overdue_docs)}):</b>\n\n"
        
        for i, doc in enumerate(overdue_docs, 1):
            title = doc.get("title", "Без названия")
            step_order = doc.get("step_order", 0)
            deadline = doc.get("deadline")
            workflow_id = doc.get("workflow_id")
            
            # Форматируем дедлайн
            deadline_str = ""
            if deadline:
                deadline_str = deadline.strftime("%d.%m.%Y %H:%M") if hasattr(deadline, 'strftime') else str(deadline)
            
            # Вычисляем просрочку
            overdue_hours = 0
            if deadline:
                from datetime import datetime
                now = datetime.now()
                if hasattr(deadline, 'timestamp'):
                    overdue_hours = (now - deadline).total_seconds() / 3600
                else:
                    overdue_hours = (now - deadline).total_seconds() / 3600
            
            text += f"{i}. ⚠️ <b>{title}</b>\n"
            text += f"   📊 Этап: {step_order}"
            if deadline_str:
                text += f" • Дедлайн: {deadline_str}"
            if overdue_hours > 0:
                text += f"\n   ⏰ Просрочено: {overdue_hours:.1f} ч"
            text += "\n\n"
        
        # Добавляем кнопки для быстрого согласования
        keyboard_buttons = []
        for doc in overdue_docs[:5]:  # Показываем кнопки только для первых 5
            workflow_id = doc.get("workflow_id")
            if workflow_id:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"✅ Согласовать {doc['title'][:15]}...",
                        callback_data=f"approve:{workflow_id}"
                    ),
                    InlineKeyboardButton(
                        text=f"❌ Отклонить",
                        callback_data=f"reject:{workflow_id}"
                    )
                ])
        
        if keyboard_buttons:
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения просроченных документов: {e}")


async def approaching_command(message: Message, current_user):
    """Показывает документы, приближающиеся к дедлайну"""
    try:
        reminder_service = ReminderService()
        
        # Получаем документы, приближающиеся к дедлайну
        approaching_docs = reminder_service.get_user_approaching_deadline(
            user_id=message.from_user.id,
            hours_before=24
        )
        
        if not approaching_docs:
            await message.answer("✅ У вас нет документов, приближающихся к дедлайну.")
            return
        
        text = f"⏰ <b>Документы, приближающиеся к дедлайну ({len(approaching_docs)}):</b>\n\n"
        
        for i, doc in enumerate(approaching_docs, 1):
            title = doc.get("title", "Без названия")
            step_order = doc.get("step_order", 0)
            deadline = doc.get("deadline")
            workflow_id = doc.get("workflow_id")
            
            # Форматируем дедлайн
            deadline_str = ""
            if deadline:
                deadline_str = deadline.strftime("%d.%m.%Y %H:%M") if hasattr(deadline, 'strftime') else str(deadline)
            
            # Вычисляем оставшееся время
            remaining_hours = 0
            if deadline:
                from datetime import datetime
                now = datetime.now()
                if hasattr(deadline, 'timestamp'):
                    remaining_hours = (deadline - now).total_seconds() / 3600
                else:
                    remaining_hours = (deadline - now).total_seconds() / 3600
            
            text += f"{i}. ⏰ <b>{title}</b>\n"
            text += f"   📊 Этап: {step_order}"
            if deadline_str:
                text += f" • Дедлайн: {deadline_str}"
            if remaining_hours > 0:
                text += f"\n   ⏰ Осталось: {remaining_hours:.1f} ч"
            text += "\n\n"
        
        # Добавляем кнопки для быстрого согласования
        keyboard_buttons = []
        for doc in approaching_docs[:5]:  # Показываем кнопки только для первых 5
            workflow_id = doc.get("workflow_id")
            if workflow_id:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"✅ Согласовать {doc['title'][:15]}...",
                        callback_data=f"approve:{workflow_id}"
                    ),
                    InlineKeyboardButton(
                        text=f"❌ Отклонить",
                        callback_data=f"reject:{workflow_id}"
                    )
                ])
        
        if keyboard_buttons:
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения документов, приближающихся к дедлайну: {e}")


async def reminder_stats_command(message: Message, current_user):
    """Показывает статистику напоминаний (только для админов)"""
    if not current_user.has_permission(Permission.VIEW_STATISTICS):
        await message.answer("❌ У вас нет прав на просмотр статистики напоминаний.")
        return
    
    try:
        reminder_service = ReminderService()
        stats = reminder_service.get_reminder_stats()
        
        text = "⏰ <b>Статистика напоминаний</b>\n\n"
        
        # Общая информация
        text += f"📊 <b>Общая информация:</b>\n"
        text += f"• Просрочено: {stats['overdue_count']}\n"
        text += f"• Приближается к дедлайну (24ч): {stats['approaching_24h']}\n"
        text += f"• Приближается к дедлайну (7д): {stats['approaching_7d']}\n"
        text += f"• Средняя просрочка: {stats['avg_overdue_hours']:.1f} ч\n\n"
        
        # Рекомендации
        if stats['overdue_count'] > 0:
            text += f"⚠️ <b>Внимание:</b> Есть просроченные документы!\n"
            text += f"Рекомендуется проверить и обработать их.\n\n"
        
        if stats['approaching_24h'] > 0:
            text += f"⏰ <b>Срочно:</b> {stats['approaching_24h']} документов приближается к дедлайну!\n"
            text += f"Необходимо срочно обработать.\n\n"
        
        if stats['overdue_count'] == 0 and stats['approaching_24h'] == 0:
            text += f"✅ <b>Отлично!</b> Нет просроченных документов и срочных задач.\n"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения статистики напоминаний: {e}")


async def my_reminder_stats_command(message: Message, current_user):
    """Показывает персональную статистику напоминаний"""
    try:
        reminder_service = ReminderService()
        stats = reminder_service.get_user_reminder_stats(message.from_user.id)
        
        text = f"⏰ <b>Ваши напоминания</b>\n\n"
        text += f"👤 <b>Пользователь:</b> {current_user.full_name}\n\n"
        
        # Статистика
        text += f"📊 <b>Статистика:</b>\n"
        text += f"• Просрочено: {stats['overdue_count']}\n"
        text += f"• Приближается к дедлайну: {stats['approaching_count']}\n"
        text += f"• Средняя просрочка: {stats['avg_overdue_hours']:.1f} ч\n\n"
        
        # Рекомендации
        if stats['overdue_count'] > 0:
            text += f"⚠️ <b>Внимание:</b> У вас есть просроченные документы!\n"
            text += f"Используйте команду /overdue для просмотра.\n\n"
        
        if stats['approaching_count'] > 0:
            text += f"⏰ <b>Срочно:</b> {stats['approaching_count']} документов приближается к дедлайну!\n"
            text += f"Используйте команду /approaching для просмотра.\n\n"
        
        if stats['overdue_count'] == 0 and stats['approaching_count'] == 0:
            text += f"✅ <b>Отлично!</b> У вас нет просроченных документов и срочных задач.\n"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения персональной статистики: {e}")
