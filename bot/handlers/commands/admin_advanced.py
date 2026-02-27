"""
Расширенные админские команды
"""
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from bot.rbac import Permission, WhitelistStore
from bot.services.statistics import StatisticsService
from bot.services.reminders import ReminderService
from bot.services.archive import ArchiveService


async def admin_panel_command(message: Message, current_user):
    """Главная админ-панель"""
    if not current_user.has_permission(Permission.MANAGE_USERS):
        await message.answer("❌ У вас нет прав на доступ к админ-панели.")
        return
    
    try:
        # Получаем статистику системы
        stats_service = StatisticsService()
        stats = stats_service.get_comprehensive_stats()
        
        # Получаем статистику напоминаний
        reminder_service = ReminderService()
        reminder_stats = reminder_service.get_reminder_stats()
        
        text = "🛠️ <b>Админ-панель DocuBot</b>\n\n"
        
        # Общая статистика
        doc_stats = stats["documents"]
        text += f"📊 <b>Общая статистика:</b>\n"
        text += f"• Документов: {doc_stats['total_documents']}\n"
        text += f"• За 30 дней: {doc_stats['recent_documents']}\n"
        text += f"• Просрочено: {reminder_stats['overdue_count']}\n"
        text += f"• Приближается к дедлайну: {reminder_stats['approaching_24h']}\n\n"
        
        # Пользователи
        user_stats = stats["users"]
        text += f"👥 <b>Пользователи:</b>\n"
        text += f"• Активных: {user_stats['active_users']}\n"
        role_dist = user_stats['role_distribution']
        text += f"• Сотрудников: {role_dist.get('employee', 0)}\n"
        text += f"• Менеджеров: {role_dist.get('manager', 0)}\n"
        text += f"• Админов: {role_dist.get('admin', 0)}\n\n"
        
        # Хранилище
        storage_stats = stats["storage"]
        text += f"💾 <b>Хранилище:</b>\n"
        text += f"• Файлов: {storage_stats['total_files']}\n"
        text += f"• Размер: {storage_stats['total_size_mb']:.1f} МБ\n\n"
        
        # Доступные команды
        text += f"🔧 <b>Доступные команды:</b>\n"
        text += f"• <code>/users</code> - управление пользователями\n"
        text += f"• <code>/system_stats</code> - детальная статистика\n"
        text += f"• <code>/overdue_all</code> - все просроченные документы\n"
        text += f"• <code>/archive_stats</code> - статистика архива\n"
        text += f"• <code>/auto_archive</code> - автоматическая архивация\n"
        text += f"• <code>/reload_whitelist</code> - перезагрузка whitelist"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка админ-панели: {e}")


async def users_command(message: Message, current_user):
    """Управление пользователями"""
    if not current_user.has_permission(Permission.MANAGE_USERS):
        await message.answer("❌ У вас нет прав на управление пользователями.")
        return
    
    try:
        # Получаем список пользователей
        store = WhitelistStore("access/whitelist.csv")
        
        text = "👥 <b>Управление пользователями</b>\n\n"
        
        # Группируем по ролям
        users_by_role = {"employee": [], "manager": [], "admin": []}
        
        for user in store.users.values():
            if user.is_active:
                users_by_role[user.role.value].append(user)
        
        # Показываем по ролям
        for role, users in users_by_role.items():
            if users:
                role_emoji = {
                    "employee": "👷",
                    "manager": "👔", 
                    "admin": "👑"
                }.get(role, "👤")
                
                text += f"{role_emoji} <b>{role.upper()} ({len(users)}):</b>\n"
                
                for user in users[:10]:  # Показываем только первых 10
                    text += f"• {user.full_name} (ID: {user.telegram_id})\n"
                
                if len(users) > 10:
                    text += f"• ... и еще {len(users) - 10} пользователей\n"
                
                text += "\n"
        
        # Общая статистика
        total_users = sum(len(users) for users in users_by_role.values())
        text += f"📊 <b>Всего активных пользователей:</b> {total_users}\n\n"
        
        text += f"💡 <b>Команды:</b>\n"
        text += f"• <code>/reload_whitelist</code> - перезагрузить whitelist\n"
        text += f"• <code>/user_stats</code> - статистика по пользователям"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка управления пользователями: {e}")


async def system_stats_command(message: Message, current_user):
    """Детальная статистика системы"""
    if not current_user.has_permission(Permission.VIEW_STATISTICS):
        await message.answer("❌ У вас нет прав на просмотр статистики.")
        return
    
    try:
        stats_service = StatisticsService()
        stats = stats_service.get_comprehensive_stats()
        
        text = "📊 <b>Детальная статистика системы</b>\n\n"
        
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
        
        # Типы документов
        kind_dist = doc_stats['kind_distribution']
        text += f"\n📁 <b>По типам:</b>\n"
        for kind, count in kind_dist.items():
            kind_emoji = {
                'order': '📋',
                'memo': '📝',
                'request': '📄',
                'other': '📎'
            }.get(kind, '📎')
            text += f"• {kind_emoji} {kind}: {count}\n"
        
        # Workflow
        workflow_stats = stats["workflows"]
        text += f"\n🔄 <b>Согласования:</b>\n"
        text += f"• Всего workflow: {workflow_stats['total_workflows']}\n"
        text += f"• Просрочено: {workflow_stats['overdue_documents']}\n"
        text += f"• Среднее время: {workflow_stats['average_approval_time_hours']:.1f} ч\n"
        
        # Статусы workflow
        workflow_status_dist = workflow_stats['status_distribution']
        text += f"\n📊 <b>Workflow по статусам:</b>\n"
        for status, count in workflow_status_dist.items():
            status_emoji = {
                'pending': '⏳',
                'approved': '✅',
                'rejected': '❌',
                'skipped': '⏭️'
            }.get(status, '❓')
            text += f"• {status_emoji} {status}: {count}\n"
        
        # Хранилище
        storage_stats = stats["storage"]
        text += f"\n💾 <b>Хранилище:</b>\n"
        text += f"• Файлов: {storage_stats['total_files']}\n"
        text += f"• Размер: {storage_stats['total_size_mb']:.1f} МБ\n"
        
        # Типы файлов
        file_types = storage_stats['file_types']
        text += f"\n📁 <b>По типам файлов:</b>\n"
        for file_type in file_types:
            mime = file_type['mime']
            count = file_type['count']
            size_mb = file_type['size_mb']
            
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
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения статистики: {e}")


async def overdue_all_command(message: Message, current_user):
    """Показывает все просроченные документы в системе"""
    if not current_user.has_permission(Permission.VIEW_STATISTICS):
        await message.answer("❌ У вас нет прав на просмотр всех просроченных документов.")
        return
    
    try:
        reminder_service = ReminderService()
        overdue_docs = reminder_service.get_overdue_documents()
        
        if not overdue_docs:
            await message.answer("✅ В системе нет просроченных документов.")
            return
        
        text = f"⚠️ <b>Все просроченные документы ({len(overdue_docs)}):</b>\n\n"
        
        for i, doc in enumerate(overdue_docs, 1):
            title = doc.get("title", "Без названия")
            owner_tg_id = doc.get("owner_tg_id")
            approver_tg_id = doc.get("approver_tg_id")
            step_order = doc.get("step_order", 0)
            deadline = doc.get("deadline")
            
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
            text += f"   👤 Владелец: {owner_tg_id}\n"
            text += f"   👤 Согласующий: {approver_tg_id}\n"
            text += f"   📊 Этап: {step_order}"
            if deadline_str:
                text += f" • Дедлайн: {deadline_str}"
            if overdue_hours > 0:
                text += f"\n   ⏰ Просрочено: {overdue_hours:.1f} ч"
            text += "\n\n"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения всех просроченных документов: {e}")


async def user_stats_command(message: Message, current_user):
    """Статистика по пользователям"""
    if not current_user.has_permission(Permission.VIEW_STATISTICS):
        await message.answer("❌ У вас нет прав на просмотр статистики пользователей.")
        return
    
    try:
        stats_service = StatisticsService()
        user_stats = stats_service.get_user_stats()
        
        text = "👥 <b>Статистика пользователей</b>\n\n"
        
        # Общая информация
        text += f"📊 <b>Общая информация:</b>\n"
        text += f"• Активных пользователей: {user_stats['active_users']}\n\n"
        
        # По ролям
        role_dist = user_stats['role_distribution']
        text += f"🎭 <b>По ролям:</b>\n"
        text += f"• Сотрудников: {role_dist.get('employee', 0)}\n"
        text += f"• Менеджеров: {role_dist.get('manager', 0)}\n"
        text += f"• Админов: {role_dist.get('admin', 0)}\n\n"
        
        # Топ пользователей
        top_users = user_stats['top_users']
        if top_users:
            text += f"🏆 <b>Топ пользователей по документам:</b>\n"
            for i, user in enumerate(top_users[:10], 1):
                user_id = user['user_id']
                doc_count = user['doc_count']
                text += f"{i}. ID {user_id}: {doc_count} документов\n"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка получения статистики пользователей: {e}")
