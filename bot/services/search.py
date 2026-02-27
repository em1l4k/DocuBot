"""
Сервис поиска и фильтрации документов
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from bot.db.session import engine


class SearchService:
    """Сервис для поиска и фильтрации документов"""
    
    def search_documents(
        self, 
        user_id: int,
        query: Optional[str] = None,
        status: Optional[str] = None,
        kind: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Поиск документов с фильтрацией
        
        Args:
            user_id: ID пользователя
            query: Поисковый запрос (по названию)
            status: Фильтр по статусу
            kind: Фильтр по типу документа
            date_from: Дата от
            date_to: Дата до
            limit: Лимит результатов
        """
        with engine.connect() as conn:
            # Базовый запрос
            sql = """
                SELECT 
                    d.id,
                    d.title,
                    d.kind,
                    d.status,
                    d.created_at,
                    d.updated_at,
                    dv.version_no,
                    dv.id as version_id
                FROM documents d
                LEFT JOIN document_versions dv ON d.current_version_id = dv.id
                WHERE d.owner_tg_id = :user_id
            """
            
            params = {"user_id": user_id}
            
            # Добавляем фильтры
            if query:
                sql += " AND d.title ILIKE :query"
                params["query"] = f"%{query}%"
            
            if status:
                sql += " AND d.status = :status"
                params["status"] = status
            
            if kind:
                sql += " AND d.kind = :kind"
                params["kind"] = kind
            
            if date_from:
                sql += " AND d.created_at >= :date_from"
                params["date_from"] = date_from
            
            if date_to:
                sql += " AND d.created_at <= :date_to"
                params["date_to"] = date_to
            
            # Сортировка и лимит
            sql += " ORDER BY d.created_at DESC LIMIT :limit"
            params["limit"] = limit
            
            result = conn.execute(text(sql), params)
            return [dict(row) for row in result.mappings()]
    
    def get_document_filters(self, user_id: int) -> Dict:
        """Получает доступные фильтры для пользователя"""
        with engine.connect() as conn:
            # Статусы документов пользователя
            statuses = conn.execute(text("""
                SELECT DISTINCT status, COUNT(*) as count
                FROM documents 
                WHERE owner_tg_id = :user_id
                GROUP BY status
                ORDER BY status
            """), {"user_id": user_id}).fetchall()
            
            # Типы документов пользователя
            kinds = conn.execute(text("""
                SELECT DISTINCT kind, COUNT(*) as count
                FROM documents 
                WHERE owner_tg_id = :user_id
                GROUP BY kind
                ORDER BY kind
            """), {"user_id": user_id}).fetchall()
            
            # Даты создания (для фильтра по периодам)
            date_ranges = conn.execute(text("""
                SELECT 
                    MIN(created_at) as earliest,
                    MAX(created_at) as latest
                FROM documents 
                WHERE owner_tg_id = :user_id
            """), {"user_id": user_id}).fetchone()
            
            return {
                "statuses": [{"value": row[0], "count": row[1]} for row in statuses],
                "kinds": [{"value": row[0], "count": row[1]} for row in kinds],
                "date_range": {
                    "earliest": date_ranges[0] if date_ranges[0] else None,
                    "latest": date_ranges[1] if date_ranges[1] else None
                }
            }
    
    def search_global(
        self,
        query: Optional[str] = None,
        status: Optional[str] = None,
        kind: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Глобальный поиск по всем документам (только для админов)
        """
        with engine.connect() as conn:
            sql = """
                SELECT 
                    d.id,
                    d.title,
                    d.kind,
                    d.status,
                    d.created_at,
                    d.updated_at,
                    d.owner_tg_id,
                    dv.version_no,
                    dv.id as version_id
                FROM documents d
                LEFT JOIN document_versions dv ON d.current_version_id = dv.id
                WHERE 1=1
            """
            
            params = {}
            
            # Добавляем фильтры
            if query:
                sql += " AND d.title ILIKE :query"
                params["query"] = f"%{query}%"
            
            if status:
                sql += " AND d.status = :status"
                params["status"] = status
            
            if kind:
                sql += " AND d.kind = :kind"
                params["kind"] = kind
            
            if date_from:
                sql += " AND d.created_at >= :date_from"
                params["date_from"] = date_from
            
            if date_to:
                sql += " AND d.created_at <= :date_to"
                params["date_to"] = date_to
            
            # Сортировка и лимит
            sql += " ORDER BY d.created_at DESC LIMIT :limit"
            params["limit"] = limit
            
            result = conn.execute(text(sql), params)
            return [dict(row) for row in result.mappings()]
    
    def get_recent_documents(self, user_id: int, days: int = 7) -> List[Dict]:
        """Получает недавние документы пользователя"""
        date_from = datetime.now() - timedelta(days=days)
        return self.search_documents(
            user_id=user_id,
            date_from=date_from,
            limit=20
        )
    
    def get_overdue_documents(self, user_id: int) -> List[Dict]:
        """Получает просроченные документы пользователя"""
        with engine.connect() as conn:
            sql = """
                SELECT DISTINCT
                    d.id,
                    d.title,
                    d.kind,
                    d.status,
                    d.created_at,
                    aw.deadline,
                    aw.step_order
                FROM documents d
                JOIN approval_workflows aw ON d.id = aw.document_id
                WHERE d.owner_tg_id = :user_id
                  AND aw.status = 'pending'
                  AND aw.deadline < NOW()
                ORDER BY aw.deadline ASC
            """
            
            result = conn.execute(text(sql), {"user_id": user_id})
            return [dict(row) for row in result.mappings()]
