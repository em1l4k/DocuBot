"""
Сервис статистики и аналитики для DocuBot
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from bot.db.session import engine
from bot.services.cache import cached, StatsCache, get_cache_service


class StatisticsService:
    """Сервис для получения статистики по документам и пользователям"""
    
    def __init__(self):
        self.cache = StatsCache(get_cache_service())
    
    @cached(ttl=300, key_prefix="stats:")
    def get_document_stats(self) -> Dict:
        """Получает общую статистику по документам"""
        with engine.connect() as conn:
            # Общее количество документов
            total_docs = conn.execute(text("""
                SELECT COUNT(*) as count FROM documents
            """)).scalar()
            
            # Документы по статусам
            status_stats = conn.execute(text("""
                SELECT status, COUNT(*) as count 
                FROM documents 
                GROUP BY status
            """)).fetchall()
            
            # Документы по типам
            kind_stats = conn.execute(text("""
                SELECT kind, COUNT(*) as count 
                FROM documents 
                GROUP BY kind
            """)).fetchall()
            
            # Документы за последние 30 дней
            recent_docs = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM documents 
                WHERE created_at >= NOW() - INTERVAL '30 days'
            """)).scalar()
            
            return {
                "total_documents": total_docs,
                "status_distribution": {row[0]: row[1] for row in status_stats},
                "kind_distribution": {row[0]: row[1] for row in kind_stats},
                "recent_documents": recent_docs
            }
    
    @cached(ttl=300, key_prefix="stats:")
    def get_user_stats(self) -> Dict:
        """Получает статистику по пользователям"""
        with engine.connect() as conn:
            # Активные пользователи (загружали документы)
            active_users = conn.execute(text("""
                SELECT COUNT(DISTINCT owner_tg_id) as count 
                FROM documents
            """)).scalar()
            
            # Пользователи по ролям (из whitelist)
            from bot.rbac import WhitelistStore
            store = WhitelistStore("access/whitelist.csv")
            
            role_stats = {"employee": 0, "manager": 0, "admin": 0}
            for user in store.users.values():
                if user.is_active:
                    role_stats[user.role.value] += 1
            
            # Топ пользователей по количеству документов
            top_users = conn.execute(text("""
                SELECT owner_tg_id, COUNT(*) as doc_count
                FROM documents 
                GROUP BY owner_tg_id 
                ORDER BY doc_count DESC 
                LIMIT 10
            """)).fetchall()
            
            return {
                "active_users": active_users,
                "role_distribution": role_stats,
                "top_users": [{"user_id": row[0], "doc_count": row[1]} for row in top_users]
            }
    
    def get_workflow_stats(self) -> Dict:
        """Получает статистику по workflow согласования"""
        with engine.connect() as conn:
            # Общее количество workflow
            total_workflows = conn.execute(text("""
                SELECT COUNT(DISTINCT document_id) as count 
                FROM approval_workflows
            """)).scalar()
            
            # Workflow по статусам
            workflow_status = conn.execute(text("""
                SELECT status, COUNT(*) as count 
                FROM approval_workflows 
                GROUP BY status
            """)).fetchall()
            
            # Среднее время согласования
            avg_approval_time = conn.execute(text("""
                SELECT AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) as avg_seconds
                FROM approval_workflows 
                WHERE completed_at IS NOT NULL
            """)).scalar()
            
            # Просроченные документы
            overdue_docs = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM approval_workflows 
                WHERE status = 'pending' 
                  AND deadline < NOW()
            """)).scalar()
            
            return {
                "total_workflows": total_workflows,
                "status_distribution": {row[0]: row[1] for row in workflow_status},
                "average_approval_time_hours": avg_approval_time / 3600 if avg_approval_time else 0,
                "overdue_documents": overdue_docs
            }
    
    def get_storage_stats(self) -> Dict:
        """Получает статистику по хранилищу"""
        with engine.connect() as conn:
            # Общее количество файлов
            total_files = conn.execute(text("""
                SELECT COUNT(*) as count FROM files
            """)).scalar()
            
            # Общий размер файлов
            total_size = conn.execute(text("""
                SELECT SUM(size_bytes) as total_bytes FROM files
            """)).scalar()
            
            # Файлы по типам
            file_types = conn.execute(text("""
                SELECT mime, COUNT(*) as count, SUM(size_bytes) as total_size
                FROM files 
                GROUP BY mime
            """)).fetchall()
            
            # Размер по месяцам
            monthly_size = conn.execute(text("""
                SELECT 
                    DATE_TRUNC('month', created_at) as month,
                    COUNT(*) as file_count,
                    SUM(size_bytes) as total_size
                FROM files 
                WHERE created_at >= NOW() - INTERVAL '12 months'
                GROUP BY DATE_TRUNC('month', created_at)
                ORDER BY month
            """)).fetchall()
            
            return {
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024) if total_size else 0,
                "file_types": [
                    {
                        "mime": row[0], 
                        "count": row[1], 
                        "size_mb": row[2] / (1024 * 1024) if row[2] else 0
                    } 
                    for row in file_types
                ],
                "monthly_growth": [
                    {
                        "month": row[0].strftime("%Y-%m"),
                        "file_count": row[1],
                        "size_mb": row[2] / (1024 * 1024) if row[2] else 0
                    }
                    for row in monthly_size
                ]
            }
    
    def get_comprehensive_stats(self) -> Dict:
        """Получает комплексную статистику"""
        return {
            "documents": self.get_document_stats(),
            "users": self.get_user_stats(),
            "workflows": self.get_workflow_stats(),
            "storage": self.get_storage_stats(),
            "generated_at": datetime.now().isoformat()
        }
