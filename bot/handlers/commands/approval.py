"""
Обработчики для системы согласования документов
"""
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from bot.services.workflow import (
    get_pending_approvals, 
    approve_document, 
    reject_document,
    get_approval_history,
    get_document_workflow
)
from bot.rbac import Permission


async def pending_approvals_command(message: Message, current_user):
    """Команда /pending - документы, ожидающие согласования"""
    if not current_user.has_permission(Permission.APPROVE_DOCUMENTS):
        await message.answer("❌ У вас нет прав на согласование документов.")
        return
    
    approvals = get_pending_approvals(current_user.telegram_id)
    
    if not approvals:
        await message.answer("✅ У вас нет документов, ожидающих согласования.")
        return
    
    await message.answer(f"📋 <b>Документы для согласования ({len(approvals)}):</b>")
    
    for approval in approvals:
        title = approval.get("title", "Без названия")
        deadline = approval.get("deadline")
        
        # Форматируем дедлайн
        deadline_text = ""
        if deadline:
            deadline_text = f"\n⏰ Дедлайн: {deadline.strftime('%d.%m.%Y %H:%M')}"
        
        text = (
            f"📄 <b>{title}</b>{deadline_text}"
        )
        
        # Создаем кнопки для согласования
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Согласовать", 
                    callback_data=f"approve:{approval['workflow_id']}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить", 
                    callback_data=f"reject:{approval['workflow_id']}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 История", 
                    callback_data=f"history:{approval['document_id']}"
                ),
                InlineKeyboardButton(
                    text="📄 Подробнее", 
                    callback_data=f"details:{approval['document_id']}"
                )
            ]
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


async def approval_history_command(message: Message, current_user):
    """Команда /approval_history - история согласований"""
    if not current_user.has_permission(Permission.VIEW_DOCUMENTS):
        await message.answer("❌ У вас нет прав на просмотр документов.")
        return
    
    # Получаем ID документа из сообщения или используем последний
    # Пока что показываем общую статистику
    await message.answer(
        "📊 <b>История согласований</b>\n\n"
        "Используйте кнопки в документах для просмотра истории конкретного документа."
    )


async def approval_stats_command(message: Message, current_user):
    """Команда /approval_stats - статистика согласований"""
    if not current_user.has_permission(Permission.VIEW_STATISTICS):
        await message.answer("❌ У вас нет прав на просмотр статистики.")
        return
    
    # TODO: Реализовать статистику
    await message.answer(
        "📈 <b>Статистика согласований</b>\n\n"
        "Функция в разработке..."
    )

