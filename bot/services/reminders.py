"""
Сервис уведомлений о просрочках и напоминаний
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from bot.db.session import engine


class ReminderService:
    """Сервис для работы с напоминаниями и уведомлениями"""
    
    def get_overdue_documents(self) -> List[Dict]:
        """Получает все просроченные документы"""
        with engine.connect() as conn:
            sql = """
                SELECT 
                    d.id as document_id,
                    d.title,
                    d.owner_tg_id,
                    aw.id as workflow_id,
                    aw.step_order,
                    aw.approver_tg_id,
                    aw.deadline,
                    aw.created_at as workflow_created_at
                FROM documents d
                JOIN approval_workflows aw ON d.id = aw.document_id
                WHERE aw.status = 'pending'
                  AND aw.deadline < NOW()
                ORDER BY aw.deadline ASC
            """
            
            result = conn.execute(text(sql))
            return [dict(row) for row in result.mappings()]
    
    def get_documents_approaching_deadline(self, hours_before: int = 24) -> List[Dict]:
        """Получает документы, приближающиеся к дедлайну"""
        deadline_threshold = datetime.now() + timedelta(hours=hours_before)
        
        with engine.connect() as conn:
            sql = """
                SELECT 
                    d.id as document_id,
                    d.title,
                    d.owner_tg_id,
                    aw.id as workflow_id,
                    aw.step_order,
                    aw.approver_tg_id,
                    aw.deadline,
                    aw.created_at as workflow_created_at
                FROM documents d
                JOIN approval_workflows aw ON d.id = aw.document_id
                WHERE aw.status = 'pending'
                  AND aw.deadline BETWEEN NOW() AND :deadline_threshold
                ORDER BY aw.deadline ASC
            """
            
            result = conn.execute(text(sql), {"deadline_threshold": deadline_threshold})
            return [dict(row) for row in result.mappings()]
    
    def get_user_overdue_documents(self, user_id: int) -> List[Dict]:
        """Получает просроченные документы конкретного пользователя"""
        with engine.connect() as conn:
            sql = """
                SELECT 
                    d.id as document_id,
                    d.title,
                    aw.id as workflow_id,
                    aw.step_order,
                    aw.deadline,
                    aw.created_at as workflow_created_at
                FROM documents d
                JOIN approval_workflows aw ON d.id = aw.document_id
                WHERE aw.approver_tg_id = :user_id
                  AND aw.status = 'pending'
                  AND aw.deadline < NOW()
                ORDER BY aw.deadline ASC
            """
            
            result = conn.execute(text(sql), {"user_id": user_id})
            return [dict(row) for row in result.mappings()]
    
    def get_user_approaching_deadline(self, user_id: int, hours_before: int = 24) -> List[Dict]:
        """Получает документы пользователя, приближающиеся к дедлайну"""
        deadline_threshold = datetime.now() + timedelta(hours=hours_before)
        
        with engine.connect() as conn:
            sql = """
                SELECT 
                    d.id as document_id,
                    d.title,
                    aw.id as workflow_id,
                    aw.step_order,
                    aw.deadline,
                    aw.created_at as workflow_created_at
                FROM documents d
                JOIN approval_workflows aw ON d.id = aw.document_id
                WHERE aw.approver_tg_id = :user_id
                  AND aw.status = 'pending'
                  AND aw.deadline BETWEEN NOW() AND :deadline_threshold
                ORDER BY aw.deadline ASC
            """
            
            result = conn.execute(text(sql), {
                "user_id": user_id,
                "deadline_threshold": deadline_threshold
            })
            return [dict(row) for row in result.mappings()]
    
    def get_reminder_stats(self) -> Dict:
        """Получает статистику по напоминаниям"""
        with engine.connect() as conn:
            # Просроченные документы
            overdue_count = conn.execute(text("""
                SELECT COUNT(*) 
                FROM approval_workflows 
                WHERE status = 'pending' AND deadline < NOW()
            """)).scalar()
            
            # Документы, приближающиеся к дедлайну (24 часа)
            approaching_count = conn.execute(text("""
                SELECT COUNT(*) 
                FROM approval_workflows 
                WHERE status = 'pending' 
                  AND deadline BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
            """)).scalar()
            
            # Документы, приближающиеся к дедлайну (7 дней)
            week_approaching_count = conn.execute(text("""
                SELECT COUNT(*) 
                FROM approval_workflows 
                WHERE status = 'pending' 
                  AND deadline BETWEEN NOW() AND NOW() + INTERVAL '7 days'
            """)).scalar()
            
            # Среднее время просрочки
            avg_overdue_hours = conn.execute(text("""
                SELECT AVG(EXTRACT(EPOCH FROM (NOW() - deadline)) / 3600)
                FROM approval_workflows 
                WHERE status = 'pending' AND deadline < NOW()
            """)).scalar()
            
            return {
                "overdue_count": overdue_count,
                "approaching_24h": approaching_count,
                "approaching_7d": week_approaching_count,
                "avg_overdue_hours": avg_overdue_hours if avg_overdue_hours else 0
            }
    
    def get_user_reminder_stats(self, user_id: int) -> Dict:
        """Получает статистику напоминаний для пользователя"""
        with engine.connect() as conn:
            # Просроченные документы пользователя
            user_overdue = conn.execute(text("""
                SELECT COUNT(*) 
                FROM approval_workflows 
                WHERE approver_tg_id = :user_id 
                  AND status = 'pending' 
                  AND deadline < NOW()
            """), {"user_id": user_id}).scalar()
            
            # Документы пользователя, приближающиеся к дедлайну
            user_approaching = conn.execute(text("""
                SELECT COUNT(*) 
                FROM approval_workflows 
                WHERE approver_tg_id = :user_id 
                  AND status = 'pending' 
                  AND deadline BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
            """), {"user_id": user_id}).scalar()
            
            # Среднее время просрочки для пользователя
            user_avg_overdue = conn.execute(text("""
                SELECT AVG(EXTRACT(EPOCH FROM (NOW() - deadline)) / 3600)
                FROM approval_workflows 
                WHERE approver_tg_id = :user_id 
                  AND status = 'pending' 
                  AND deadline < NOW()
            """), {"user_id": user_id}).scalar()
            
            return {
                "overdue_count": user_overdue,
                "approaching_count": user_approaching,
                "avg_overdue_hours": user_avg_overdue if user_avg_overdue else 0
            }
