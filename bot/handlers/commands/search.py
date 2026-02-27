"""
Команды для поиска и фильтрации документов
"""
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from bot.services.search import SearchService
from bot.rbac import Permission


async def search_command(message: Message, current_user):
    """Команда поиска документов"""
    try:
        # Парсим аргументы команды
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        
        if not args:
            await message.answer(
                "🔍 <b>Поиск документов</b>\n\n"
                "Использование:\n"
                "• <code>/search текст</code> - поиск по названию\n"
                "• <code>/search status:approved</code> - по статусу\n"
                "• <code>/search kind:order</code> - по типу\n"
                "• <code>/search</code> - показать все документы\n\n"
                "Примеры:\n"
                "• <code>/search отчет</code>\n"
                "• <code>/search status:in_review</code>\n"
                "• <code>/search kind:order status:approved</code>",
                parse_mode="HTML"
            )
            return
        
        search_service = SearchService()
        
        # Парсим параметры поиска
        query = None
        status = None
        kind = None
        
        for arg in args:
            if arg.startswith("status:"):
                status = arg.split(":", 1)[1]
            elif arg.startswith("kind:"):
                kind = arg.split(":", 1)[1]
            else:
                query = arg
        
        # Выполняем поиск
        results = search_service.search_documents(
            user_id=message.from_user.id,
            query=query,
            status=status,
            kind=kind,
            limit=10
        )
        
        if not results:
            await message.answer("🔍 Документы не найдены.")
            return
        
        # Формируем результаты
        text = f"🔍 <b>Результаты поиска ({len(results)}):</b>\n\n"
        
        for i, doc in enumerate(results, 1):
            title = doc.get("title", "Без названия")
            status = doc.get("status", "unknown")
            kind = doc.get("kind", "other")
            created_at = doc.get("created_at")
            version_id = doc.get("version_id")
            
            # Эмодзи для статуса
            status_emoji = {
                'draft': '📝',
                'in_review': '🔄',
                'approved': '✅',
                'rejected': '❌',
                'archived': '📦'
            }.get(status, '❓')
            
            # Форматируем дату
            date_str = ""
            if created_at:
                date_str = created_at.strftime("%d.%m.%Y") if hasattr(created_at, 'strftime') else str(created_at)
            
            text += f"{i}. {status_emoji} <b>{title}</b>\n"
            text += f"   📊 {status} • {kind}"
            if date_str:
                text += f" • {date_str}"
            text += "\n\n"
        
        # Добавляем кнопки для скачивания
        keyboard_buttons = []
        for doc in results[:5]:  # Показываем кнопки только для первых 5
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
        await message.answer(f"❌ Ошибка поиска: {e}")


async def filters_command(message: Message, current_user):
    """Показывает доступные фильтры"""
    try:
        search_service = SearchService()
        filters = search_service.get_document_filters(message.from_user.id)
        
        text = "🔍 <b>Доступные фильтры</b>\n\n"
        
        # Статусы
        if filters["statuses"]:
            text += "📊 <b>По статусам:</b>\n"
            for status_info in filters["statuses"]:
                status = status_info["value"]
                count = status_info["count"]
                
                status_emoji = {
                    'draft': '📝',
                    'in_review': '🔄',
                    'approved': '✅',
                    'rejected': '❌',
                    'archived': '📦'
                }.get(status, '❓')
                
                text += f"• {status_emoji} {status}: {count}\n"
            text += "\n"
        
        # Типы
        if filters["kinds"]:
            text += "📁 <b>По типам:</b>\n"
            for kind_info in filters["kinds"]:
                kind = kind_info["value"]
                count = kind_info["count"]
                
                kind_emoji = {
                    'order': '📋',
                    'memo': '📝',
                    'request': '📄',
                    'other': '📎'
                }.get(kind, '📎')
                
                text += f"• {kind_emoji} {kind}: {count}\n"
            text += "\n"
        
        # Период
        date_range = filters["date_range"]
        if date_range["earliest"] and date_range["latest"]:
            earliest = date_range["earliest"]
            latest = date_range["latest"]
            
            if hasattr(earliest, 'strftime'):
                earliest_str = earliest.strftime("%d.%m.%Y")
            else:
                earliest_str = str(earliest)
            
            if hasattr(latest, 'strftime'):
                latest_str = latest.strftime("%d.%m.%Y")
            else:
                latest_str = str(latest)
            
            text += f"📅 <b>Период:</b> {earliest_str} - {latest_str}\n\n"
        
        text += "💡 <b>Примеры использования:</b>\n"
        text += "• <code>/search status:approved</code>\n"
        text += "• <code>/search kind:order</code>\n"
        text += "• <code>/search отчет</code>\n"
        text += "• <code>/search status:in_review kind:order</code>"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения фильтров: {e}")


async def recent_command(message: Message, current_user):
    """Показывает недавние документы"""
    try:
        search_service = SearchService()
        
        # Получаем недавние документы за последние 7 дней
        recent_docs = search_service.get_recent_documents(
            user_id=message.from_user.id,
            days=7
        )
        
        if not recent_docs:
            await message.answer("📅 У вас нет документов за последние 7 дней.")
            return
        
        text = f"📅 <b>Недавние документы ({len(recent_docs)}):</b>\n\n"
        
        for i, doc in enumerate(recent_docs, 1):
            title = doc.get("title", "Без названия")
            status = doc.get("status", "unknown")
            created_at = doc.get("created_at")
            version_id = doc.get("version_id")
            
            # Эмодзи для статуса
            status_emoji = {
                'draft': '📝',
                'in_review': '🔄',
                'approved': '✅',
                'rejected': '❌',
                'archived': '📦'
            }.get(status, '❓')
            
            # Форматируем дату
            date_str = ""
            if created_at:
                date_str = created_at.strftime("%d.%m.%Y") if hasattr(created_at, 'strftime') else str(created_at)
            
            text += f"{i}. {status_emoji} <b>{title}</b>\n"
            if date_str:
                text += f"   📅 {date_str}\n"
            text += "\n"
        
        # Добавляем кнопки для скачивания
        keyboard_buttons = []
        for doc in recent_docs[:5]:  # Показываем кнопки только для первых 5
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
        await message.answer(f"❌ Ошибка получения недавних документов: {e}")


async def search_overdue_command(message: Message, current_user):
    """Показывает просроченные документы"""
    try:
        search_service = SearchService()
        
        # Получаем просроченные документы
        overdue_docs = search_service.get_overdue_documents(message.from_user.id)
        
        if not overdue_docs:
            await message.answer("✅ У вас нет просроченных документов.")
            return
        
        text = f"⚠️ <b>Просроченные документы ({len(overdue_docs)}):</b>\n\n"
        
        for i, doc in enumerate(overdue_docs, 1):
            title = doc.get("title", "Без названия")
            deadline = doc.get("deadline")
            step_order = doc.get("step_order", 0)
            
            # Форматируем дедлайн
            deadline_str = ""
            if deadline:
                deadline_str = deadline.strftime("%d.%m.%Y %H:%M") if hasattr(deadline, 'strftime') else str(deadline)
            
            text += f"{i}. ⚠️ <b>{title}</b>\n"
            text += f"   📊 Этап: {step_order}"
            if deadline_str:
                text += f" • Дедлайн: {deadline_str}"
            text += "\n\n"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения просроченных документов: {e}")
