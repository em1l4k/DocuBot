"""
Обработчики callback кнопок для системы согласования
"""
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.services.workflow import (
    approve_document, 
    reject_document,
    get_approval_history,
    get_document_workflow
)
from bot.rbac import Permission


async def handle_approve_callback(call: CallbackQuery, current_user):
    """Обработчик кнопки 'Согласовать'"""
    if not current_user.has_permission(Permission.APPROVE_DOCUMENTS):
        await call.answer("❌ У вас нет прав на согласование документов.", show_alert=True)
        return
    
    try:
        _, workflow_id = call.data.split(":", 1)
    except ValueError:
        await call.answer("❌ Некорректная ссылка", show_alert=True)
        return
    
    # Согласовываем документ с уведомлением
    from bot.services.workflow import approve_document
    from bot.rbac import WhitelistStore
    
    store = WhitelistStore("access/whitelist.csv")
    success = await approve_document(
        workflow_id, 
        current_user.telegram_id, 
        "Согласовано пользователем",
        bot=call.bot,
        whitelist_store=store
    )
    
    if success:
        await call.answer("✅ Документ согласован!")
        await call.message.edit_text(
            "✅ <b>Документ согласован</b>\n\n"
            "Автор документа получит уведомление о согласовании.",
            parse_mode="HTML"
        )
    else:
        await call.answer("❌ Ошибка при согласовании", show_alert=True)


async def handle_reject_callback(call: CallbackQuery, current_user):
    """Обработчик кнопки 'Отклонить'"""
    if not current_user.has_permission(Permission.REJECT_DOCUMENTS):
        await call.answer("❌ У вас нет прав на отклонение документов.", show_alert=True)
        return
    
    try:
        _, workflow_id = call.data.split(":", 1)
    except ValueError:
        await call.answer("❌ Некорректная ссылка", show_alert=True)
        return
    
    # Пока что отклоняем без комментария
    # TODO: Добавить форму для комментария
    from bot.services.workflow import reject_document
    from bot.rbac import WhitelistStore
    
    store = WhitelistStore("access/whitelist.csv")
    success = await reject_document(
        workflow_id, 
        current_user.telegram_id, 
        "Отклонено пользователем",
        bot=call.bot,
        whitelist_store=store
    )
    
    if success:
        await call.answer("❌ Документ отклонен!")
        await call.message.edit_text(
            "❌ <b>Документ отклонен</b>\n\n"
            "Автор документа получит уведомление о причинах отклонения.",
            parse_mode="HTML"
        )
    else:
        await call.answer("❌ Ошибка при отклонении", show_alert=True)


async def handle_history_callback(call: CallbackQuery, current_user):
    """Обработчик кнопки 'История'"""
    if not current_user.has_permission(Permission.VIEW_DOCUMENTS):
        await call.answer("❌ У вас нет прав на просмотр документов.", show_alert=True)
        return
    
    try:
        _, document_id = call.data.split(":", 1)
    except ValueError:
        await call.answer("❌ Некорректная ссылка", show_alert=True)
        return
    
    # Получаем историю согласования
    history = get_approval_history(document_id)
    
    if not history:
        await call.answer("📋 История согласований пуста", show_alert=True)
        return
    
    # Формируем текст истории
    history_text = "📋 <b>История согласования:</b>\n\n"
    
    for item in history:
        action = item.get("action", "unknown")
        comment = item.get("comment", "")
        created_at = item.get("created_at")
        approver_name = item.get("approver_name", "Неизвестно")
        
        # Эмодзи и русские названия для действий
        action_info = {
            "approved": ("✅", "Согласовал"),
            "rejected": ("❌", "Отклонил"), 
            "commented": ("💬", "Прокомментировал"),
            "delegated": ("🔄", "Делегировал")
        }.get(action, ("❓", "Неизвестное действие"))
        
        action_emoji, action_text = action_info
        
        # Форматируем дату
        date_str = created_at.strftime("%d.%m.%Y %H:%M") if created_at else "Неизвестно"
        
        history_text += (
            f"{action_emoji} <b>{approver_name}</b> - {action_text}\n"
            f"📅 {date_str}\n"
        )
        
        if comment:
            history_text += f"💬 {comment}\n"
        
        history_text += "\n"
    
    # Создаем кнопку "Назад"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_docs")]
    ])
    
    await call.message.edit_text(history_text, reply_markup=keyboard, parse_mode="HTML")
    await call.answer()


async def handle_details_callback(call: CallbackQuery, current_user):
    """Обработчик кнопки 'Подробнее'"""
    if not current_user.has_permission(Permission.VIEW_DOCUMENTS):
        await call.answer("❌ У вас нет прав на просмотр документов.", show_alert=True)
        return
    
    try:
        _, document_id = call.data.split(":", 1)
    except ValueError:
        await call.answer("❌ Некорректная ссылка", show_alert=True)
        return
    
    # Получаем workflow документа
    workflow = get_document_workflow(document_id)
    
    if not workflow:
        await call.answer("📋 Workflow не найден", show_alert=True)
        return
    
    # Формируем детальную информацию
    details_text = "📄 <b>Детали workflow:</b>\n\n"
    
    for step in workflow:
        step_order = step.get("step_order", 0)
        status = step.get("status", "unknown")
        approver_tg_id = step.get("approver_tg_id", 0)
        deadline = step.get("deadline")
        comment = step.get("comment", "")
        
        # Эмодзи и русские названия для статуса
        status_info = {
            "pending": ("⏳", "Ожидает согласования"),
            "approved": ("✅", "Согласован"),
            "rejected": ("❌", "Отклонен"),
            "skipped": ("⏭️", "Пропущен")
        }.get(status, ("❓", "Неизвестно"))
        
        status_emoji, status_text = status_info
        
        # Получаем имя согласующего из whitelist
        from bot.rbac import WhitelistStore
        store = WhitelistStore("access/whitelist.csv")
        approver = store.get(approver_tg_id)
        approver_name = approver.full_name if approver else f"Пользователь {approver_tg_id}"
        
        # Форматируем дедлайн
        deadline_str = ""
        if deadline:
            deadline_str = f" (до {deadline.strftime('%d.%m.%Y %H:%M')})"
        
        details_text += (
            f"{status_emoji} <b>Этап {step_order}</b>\n"
            f"👤 Согласующий: {approver_name}{deadline_str}\n"
            f"📊 Статус: {status_text}\n"
        )
        
        if comment:
            details_text += f"💬 Комментарий: {comment}\n"
        
        details_text += "\n"
    
    # Создаем кнопку "Назад"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_docs")]
    ])
    
    await call.message.edit_text(details_text, reply_markup=keyboard, parse_mode="HTML")
    await call.answer()
