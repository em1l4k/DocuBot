"""
Сервис архивации документов
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import text
from bot.db.session import engine


class ArchiveService:
    """Сервис для работы с архивом документов"""
    
    def archive_document(self, document_id: str, user_id: int, reason: Optional[str] = None) -> bool:
        """
        Архивирует документ
        
        Args:
            document_id: ID документа
            user_id: ID пользователя, выполняющего архивацию
            reason: Причина архивации
        """
        try:
            with engine.begin() as conn:
                # Проверяем, что документ принадлежит пользователю или пользователь - админ
                doc_owner = conn.execute(text("""
                    SELECT owner_tg_id FROM documents WHERE id = :doc_id
                """), {"doc_id": document_id}).scalar()
                
                if not doc_owner:
                    return False
                
                # Проверяем права (владелец или админ)
                from bot.rbac import WhitelistStore
                store = WhitelistStore("access/whitelist.csv")
                user = store.get(user_id)
                
                if not user or (user_id != doc_owner and user.role.value != "admin"):
                    return False
                
                # Архивируем документ
                conn.execute(text("""
                    UPDATE documents 
                    SET status = 'archived', updated_at = now()
                    WHERE id = :doc_id
                """), {"doc_id": document_id})
                
                # Записываем в историю архивации
                conn.execute(text("""
                    INSERT INTO approval_history 
                    (id, document_id, approver_tg_id, action, comment)
                    VALUES (:id, :doc_id, :user_id, 'archived', :reason)
                """), {
                    "id": str(uuid4()),
                    "doc_id": document_id,
                    "user_id": user_id,
                    "reason": reason or "Документ отправлен в архив"
                })
                
                return True
                
        except Exception as e:
            print(f"Ошибка архивации документа: {e}")
            return False
    
    def unarchive_document(self, document_id: str, user_id: int) -> bool:
        """
        Разархивирует документ
        
        Args:
            document_id: ID документа
            user_id: ID пользователя
        """
        try:
            with engine.begin() as conn:
                # Проверяем права
                from bot.rbac import WhitelistStore
                store = WhitelistStore("access/whitelist.csv")
                user = store.get(user_id)
                
                if not user or user.role.value != "admin":
                    return False
                
                # Разархивируем документ
                conn.execute(text("""
                    UPDATE documents 
                    SET status = 'approved', updated_at = now()
                    WHERE id = :doc_id AND status = 'archived'
                """), {"doc_id": document_id})
                
                return True
                
        except Exception as e:
            print(f"Ошибка разархивации документа: {e}")
            return False
    
    def get_archived_documents(self, user_id: int, limit: int = 20) -> List[Dict]:
        """
        Получает список архивных документов пользователя
        
        Args:
            user_id: ID пользователя
            limit: Лимит результатов
        """
        with engine.connect() as conn:
            sql = """
                SELECT 
                    d.id,
                    d.title,
                    d.kind,
                    d.created_at,
                    d.updated_at,
                    dv.version_no,
                    dv.id as version_id,
                    ah.created_at as archived_at,
                    ah.comment as archive_reason
                FROM documents d
                LEFT JOIN document_versions dv ON d.current_version_id = dv.id
                LEFT JOIN approval_history ah ON d.id = ah.document_id 
                    AND ah.action = 'archived'
                WHERE d.owner_tg_id = :user_id 
                  AND d.status = 'archived'
                ORDER BY ah.created_at DESC
                LIMIT :limit
            """
            
            result = conn.execute(text(sql), {"user_id": user_id, "limit": limit})
            return [dict(row) for row in result.mappings()]
    
    def get_all_archived_documents(self, limit: int = 50) -> List[Dict]:
        """
        Получает все архивные документы (только для админов)
        
        Args:
            limit: Лимит результатов
        """
        with engine.connect() as conn:
            sql = """
                SELECT 
                    d.id,
                    d.title,
                    d.kind,
                    d.owner_tg_id,
                    d.created_at,
                    d.updated_at,
                    dv.version_no,
                    dv.id as version_id,
                    ah.created_at as archived_at,
                    ah.comment as archive_reason
                FROM documents d
                LEFT JOIN document_versions dv ON d.current_version_id = dv.id
                LEFT JOIN approval_history ah ON d.id = ah.document_id 
                    AND ah.action = 'archived'
                WHERE d.status = 'archived'
                ORDER BY ah.created_at DESC
                LIMIT :limit
            """
            
            result = conn.execute(text(sql), {"limit": limit})
            return [dict(row) for row in result.mappings()]
    
    def get_archive_stats(self) -> Dict:
        """Получает статистику архива"""
        with engine.connect() as conn:
            # Общее количество архивных документов
            total_archived = conn.execute(text("""
                SELECT COUNT(*) FROM documents WHERE status = 'archived'
            """)).scalar()
            
            # Архивные документы по типам
            archived_by_kind = conn.execute(text("""
                SELECT kind, COUNT(*) as count
                FROM documents 
                WHERE status = 'archived'
                GROUP BY kind
            """)).fetchall()
            
            # Архивные документы по месяцам
            archived_by_month = conn.execute(text("""
                SELECT 
                    DATE_TRUNC('month', ah.created_at) as month,
                    COUNT(*) as count
                FROM documents d
                JOIN approval_history ah ON d.id = ah.document_id
                WHERE d.status = 'archived' 
                  AND ah.action = 'archived'
                  AND ah.created_at >= NOW() - INTERVAL '12 months'
                GROUP BY DATE_TRUNC('month', ah.created_at)
                ORDER BY month
            """)).fetchall()
            
            return {
                "total_archived": total_archived,
                "by_kind": {row[0]: row[1] for row in archived_by_kind},
                "by_month": [
                    {
                        "month": row[0].strftime("%Y-%m"),
                        "count": row[1]
                    }
                    for row in archived_by_month
                ]
            }
    
    def auto_archive_old_documents(self, days_threshold: int = 365) -> int:
        """
        Автоматически архивирует старые документы
        
        Args:
            days_threshold: Количество дней для автоматической архивации
            
        Returns:
            Количество заархивированных документов
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_threshold)
            
            with engine.begin() as conn:
                # Находим старые одобренные документы
                old_docs = conn.execute(text("""
                    SELECT id FROM documents 
                    WHERE status = 'approved' 
                      AND created_at < :cutoff_date
                """), {"cutoff_date": cutoff_date}).fetchall()
                
                archived_count = 0
                
                for doc in old_docs:
                    doc_id = doc[0]
                    
                    # Архивируем документ
                    conn.execute(text("""
                        UPDATE documents 
                        SET status = 'archived', updated_at = now()
                        WHERE id = :doc_id
                    """), {"doc_id": doc_id})
                    
                    # Записываем в историю
                    conn.execute(text("""
                        INSERT INTO approval_history 
                        (id, document_id, approver_tg_id, action, comment)
                        VALUES (:id, :doc_id, :user_id, 'archived', :reason)
                    """), {
                        "id": str(uuid4()),
                        "doc_id": doc_id,
                        "user_id": 0,  # Системная архивация
                        "reason": f"Автоматическая архивация (старше {days_threshold} дней)"
                    })
                    
                    archived_count += 1
                
                return archived_count
                
        except Exception as e:
            print(f"Ошибка автоматической архивации: {e}")
            return 0
