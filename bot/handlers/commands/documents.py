from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.services.repo import list_user_documents


async def my_docs_command(message: Message, current_user):
    """Обработчик команды /my_docs"""
    docs = list_user_documents(message.from_user.id, limit=10)
    if not docs:
        await message.answer("У вас пока нет документов.")
        return

    # Формируем единое сообщение со списком документов
    text = "📄 <b>Ваши документы:</b>\n\n"
    keyboard_buttons = []
    
    for i, d in enumerate(docs, 1):
        title = d.get("title") or "Без названия"
        vnum = d.get("version_no")
        created_at = d.get("created_at")
        
        # Форматируем дату
        date_str = ""
        if created_at:
            date_str = created_at.strftime("%d.%m.%Y") if hasattr(created_at, 'strftime') else str(created_at)
        
        # Формируем текст документа
        doc_text = f"{i}. 📄 <b>{title}</b>"
        if vnum:
            doc_text += f" (v{vnum})"
        if date_str:
            doc_text += f" - {date_str}"
        
        text += doc_text + "\n"
        
        # Добавляем кнопку скачивания если есть version_id
        if d.get("version_id"):
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"⬇️ {title[:20]}{'...' if len(title) > 20 else ''}", 
                    callback_data=f"dl:{d['version_id']}"
                )
            ])
    
    # Отправляем единое сообщение с кнопками
    if keyboard_buttons:
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")
