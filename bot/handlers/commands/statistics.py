"""
Команды для работы со статистикой
"""
from aiogram.types import Message
from bot.services.statistics import StatisticsService
from bot.rbac import Permission


async def stats_command(message: Message, current_user):
    """Показывает общую статистику системы"""
    if not current_user.has_permission(Permission.VIEW_STATISTICS):
        await message.answer("❌ У вас нет прав на просмотр статистики.")
        return
    
    try:
        stats_service = StatisticsService()
        stats = stats_service.get_comprehensive_stats()
        
        # Формируем сообщение
        text = "📊 <b>Статистика системы DocuBot</b>\n\n"
        
        # Документы
        doc_stats = stats["documents"]
        text += f"📄 <b>Документы:</b>\n"
        text += f"• Всего: {doc_stats['total_documents']}\n"
        text += f"• За 30 дней: {doc_stats['recent_documents']}\n"
        
        # Статусы документов
        status_dist = doc_stats['status_distribution']
        text += f"\n📋 <b>По статусам:</b>\n"
        for status, count in status_dist.items():
            status_emoji = {
                'draft': '📝',
                'in_review': '🔄',
                'approved': '✅',
                'rejected': '❌',
                'archived': '📦'
            }.get(status, '❓')
            text += f"• {status_emoji} {status}: {count}\n"
        
        # Пользователи
        user_stats = stats["users"]
        text += f"\n👥 <b>Пользователи:</b>\n"
        text += f"• Активных: {user_stats['active_users']}\n"
        
        role_dist = user_stats['role_distribution']
        text += f"• Сотрудников: {role_dist.get('employee', 0)}\n"
        text += f"• Менеджеров: {role_dist.get('manager', 0)}\n"
        text += f"• Админов: {role_dist.get('admin', 0)}\n"
        
        # Workflow
        workflow_stats = stats["workflows"]
        text += f"\n🔄 <b>Согласования:</b>\n"
        text += f"• Всего workflow: {workflow_stats['total_workflows']}\n"
        text += f"• Просрочено: {workflow_stats['overdue_documents']}\n"
        text += f"• Среднее время: {workflow_stats['average_approval_time_hours']:.1f} ч\n"
        
        # Хранилище
        storage_stats = stats["storage"]
        text += f"\n💾 <b>Хранилище:</b>\n"
        text += f"• Файлов: {storage_stats['total_files']}\n"
        text += f"• Размер: {storage_stats['total_size_mb']:.1f} МБ\n"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения статистики: {e}")


async def my_stats_command(message: Message, current_user):
    """Показывает персональную статистику пользователя"""
    try:
        stats_service = StatisticsService()
        
        # Получаем статистику пользователя
        from bot.services.repo import list_user_documents
        from bot.services.workflow import get_approval_history
        
        # Документы пользователя
        user_docs = list_user_documents(message.from_user.id, limit=1000)
        
        # Статистика по статусам
        status_counts = {}
        for doc in user_docs:
            status = doc.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # История согласований
        approval_history = []
        for doc in user_docs:
            if doc.get('document_id'):
                history = get_approval_history(doc['document_id'])
                approval_history.extend(history)
        
        # Формируем сообщение
        text = f"📊 <b>Ваша статистика</b>\n\n"
        text += f"👤 <b>Пользователь:</b> {current_user.full_name}\n"
        text += f"🎭 <b>Роль:</b> {current_user.role.value}\n\n"
        
        text += f"📄 <b>Документы ({len(user_docs)}):</b>\n"
        for status, count in status_counts.items():
            status_emoji = {
                'draft': '📝',
                'in_review': '🔄', 
                'approved': '✅',
                'rejected': '❌',
                'archived': '📦'
            }.get(status, '❓')
            text += f"• {status_emoji} {status}: {count}\n"
        
        if approval_history:
            text += f"\n🔄 <b>Согласования ({len(approval_history)}):</b>\n"
            # Группируем по действиям
            action_counts = {}
            for item in approval_history:
                action = item.get('action', 'unknown')
                action_counts[action] = action_counts.get(action, 0) + 1
            
            for action, count in action_counts.items():
                action_emoji = {
                    'approved': '✅',
                    'rejected': '❌',
                    'commented': '💬',
                    'delegated': '🔄'
                }.get(action, '❓')
                text += f"• {action_emoji} {action}: {count}\n"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения статистики: {e}")


async def storage_stats_command(message: Message, current_user):
    """Показывает детальную статистику хранилища"""
    if not current_user.has_permission(Permission.VIEW_STATISTICS):
        await message.answer("❌ У вас нет прав на просмотр статистики.")
        return
    
    try:
        stats_service = StatisticsService()
        storage_stats = stats_service.get_storage_stats()
        
        text = "💾 <b>Статистика хранилища</b>\n\n"
        
        # Общая информация
        text += f"📁 <b>Общая информация:</b>\n"
        text += f"• Файлов: {storage_stats['total_files']}\n"
        text += f"• Размер: {storage_stats['total_size_mb']:.1f} МБ\n\n"
        
        # По типам файлов
        text += f"📋 <b>По типам файлов:</b>\n"
        for file_type in storage_stats['file_types']:
            mime = file_type['mime']
            count = file_type['count']
            size_mb = file_type['size_mb']
            
            # Определяем тип файла
            if 'pdf' in mime:
                emoji = '📄'
                type_name = 'PDF'
            elif 'word' in mime or 'docx' in mime:
                emoji = '📝'
                type_name = 'DOCX'
            else:
                emoji = '📎'
                type_name = 'Другой'
            
            text += f"• {emoji} {type_name}: {count} файлов ({size_mb:.1f} МБ)\n"
        
        # Рост по месяцам
        if storage_stats['monthly_growth']:
            text += f"\n📈 <b>Рост за последние месяцы:</b>\n"
            for month_data in storage_stats['monthly_growth'][-6:]:  # Последние 6 месяцев
                month = month_data['month']
                file_count = month_data['file_count']
                size_mb = month_data['size_mb']
                text += f"• {month}: +{file_count} файлов (+{size_mb:.1f} МБ)\n"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения статистики: {e}")
