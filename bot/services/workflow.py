"""
Сервис для работы с workflow согласования документов
"""
from uuid import uuid4
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import text
from bot.db.session import engine


def create_approval_workflow(
    document_id: str, 
    approvers: List[int], 
    deadlines: Optional[List[datetime]] = None
) -> str:
    """
    Создает workflow согласования для документа
    
    Args:
        document_id: ID документа
        approvers: Список Telegram ID согласующих (по порядку)
        deadlines: Список дедлайнов для каждого этапа (опционально)
    
    Returns:
        ID созданного workflow
    """
    workflow_id = str(uuid4())
    
    with engine.begin() as conn:
        # Создаем этапы согласования
        for i, approver_tg_id in enumerate(approvers):
            deadline = deadlines[i] if deadlines and i < len(deadlines) else None
            
            conn.execute(text("""
                INSERT INTO approval_workflows 
                (id, document_id, step_order, approver_tg_id, deadline)
                VALUES (:id, :doc_id, :order, :approver, :deadline)
            """), {
                "id": str(uuid4()),
                "doc_id": document_id,
                "order": i + 1,
                "approver": approver_tg_id,
                "deadline": deadline
            })
    
    return workflow_id


def get_document_workflow(document_id: str) -> List[Dict]:
    """
    Получает workflow согласования для документа
    
    Returns:
        Список этапов согласования
    """
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                w.id,
                w.step_order,
                w.approver_tg_id,
                w.status,
                w.comment,
                w.created_at,
                w.completed_at,
                w.deadline
            FROM approval_workflows w
            WHERE w.document_id = :doc_id
            ORDER BY w.step_order
        """), {"doc_id": document_id})
        
        return [dict(row) for row in result.mappings()]


def get_pending_approvals(approver_tg_id: int) -> List[Dict]:
    """
    Получает документы, ожидающие согласования пользователем
    
    Returns:
        Список документов для согласования
    """
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                d.id as document_id,
                d.title,
                d.kind,
                d.status as doc_status,
                d.created_at as doc_created_at,
                w.id as workflow_id,
                w.step_order,
                w.deadline,
                w.created_at as workflow_created_at,
                d.owner_tg_id
            FROM approval_workflows w
            JOIN documents d ON d.id = w.document_id
            WHERE w.approver_tg_id = :approver_id
              AND w.status = 'pending'
            ORDER BY w.deadline ASC NULLS LAST, w.created_at ASC
        """), {"approver_id": approver_tg_id})
        
        rows = [dict(row) for row in result.mappings()]
        
        # Получаем имена пользователей из whitelist
        from bot.rbac import WhitelistStore
        store = WhitelistStore("access/whitelist.csv")
        
        for row in rows:
            owner = store.get(row["owner_tg_id"])
            row["author_name"] = owner.full_name if owner else f"Пользователь {row['owner_tg_id']}"
        
        return rows


async def approve_document(
    workflow_id: str, 
    approver_tg_id: int, 
    comment: Optional[str] = None,
    bot=None,
    whitelist_store=None
) -> bool:
    """
    Согласовывает документ на текущем этапе
    
    Returns:
        True если согласование прошло успешно
    """
    with engine.begin() as conn:
        # Обновляем статус текущего этапа
        result = conn.execute(text("""
            UPDATE approval_workflows 
            SET status = 'approved', 
                comment = :comment,
                completed_at = now()
            WHERE id = :workflow_id 
              AND approver_tg_id = :approver_id
              AND status = 'pending'
            RETURNING document_id, step_order
        """), {
            "workflow_id": workflow_id,
            "approver_id": approver_tg_id,
            "comment": comment
        })
        
        row = result.fetchone()
        if not row:
            return False
        
        document_id, step_order = row
        
        # Записываем в историю
        conn.execute(text("""
            INSERT INTO approval_history 
            (id, document_id, approver_tg_id, action, comment)
            VALUES (:id, :doc_id, :approver, 'approved', :comment)
        """), {
            "id": str(uuid4()),
            "doc_id": document_id,
            "approver": approver_tg_id,
            "comment": comment
        })
        
        # Проверяем, есть ли следующие этапы
        next_step = conn.execute(text("""
            SELECT id FROM approval_workflows 
            WHERE document_id = :doc_id 
              AND step_order = :next_order
        """), {
            "doc_id": document_id,
            "next_order": step_order + 1
        }).fetchone()
        
        if not next_step:
            # Это был последний этап - документ полностью согласован
            conn.execute(text("""
                UPDATE documents 
                SET status = 'approved' 
                WHERE id = :doc_id
            """), {"doc_id": document_id})
            
            # Отправляем уведомление автору о полном согласовании
            if bot and whitelist_store:
                doc_info = conn.execute(text("""
                    SELECT title, owner_tg_id FROM documents WHERE id = :doc_id
                """), {"doc_id": document_id}).fetchone()
                
                if doc_info:
                    title, owner_tg_id = doc_info
                    approver = whitelist_store.get(approver_tg_id)
                    approver_name = approver.full_name if approver else f"Пользователь {approver_tg_id}"
                    
                    # Отправляем уведомление автору документа
                    try:
                        doc_id_str = str(document_id)[:8]
                        await bot.send_message(
                            owner_tg_id,
                            f"✅ <b>Документ согласован!</b>\n\n"
                            f"📄 <b>Название:</b> {title}\n"
                            f"👤 <b>Согласовал:</b> {approver_name}\n"
                            f"🆔 <b>ID документа:</b> <code>{doc_id_str}</code>",
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        print(f"Ошибка отправки уведомления: {e}")
        
        return True


async def reject_document(
    workflow_id: str, 
    approver_tg_id: int, 
    comment: str,
    bot=None,
    whitelist_store=None
) -> bool:
    """
    Отклоняет документ
    
    Returns:
        True если отклонение прошло успешно
    """
    with engine.begin() as conn:
        # Обновляем статус текущего этапа
        result = conn.execute(text("""
            UPDATE approval_workflows 
            SET status = 'rejected', 
                comment = :comment,
                completed_at = now()
            WHERE id = :workflow_id 
              AND approver_tg_id = :approver_id
              AND status = 'pending'
            RETURNING document_id
        """), {
            "workflow_id": workflow_id,
            "approver_id": approver_tg_id,
            "comment": comment
        })
        
        row = result.fetchone()
        if not row:
            return False
        
        document_id = row[0]
        
        # Записываем в историю
        conn.execute(text("""
            INSERT INTO approval_history 
            (id, document_id, approver_tg_id, action, comment)
            VALUES (:id, :doc_id, :approver, 'rejected', :comment)
        """), {
            "id": str(uuid4()),
            "doc_id": document_id,
            "approver": approver_tg_id,
            "comment": comment
        })
        
        # Обновляем статус документа
        conn.execute(text("""
            UPDATE documents 
            SET status = 'rejected' 
            WHERE id = :doc_id
        """), {"doc_id": document_id})
        
        # Отправляем уведомление автору документа
        if bot and whitelist_store:
            # Получаем информацию о документе и авторе
            doc_info = conn.execute(text("""
                SELECT title, owner_tg_id FROM documents WHERE id = :doc_id
            """), {"doc_id": document_id}).fetchone()
            
            if doc_info:
                title, owner_tg_id = doc_info
                approver = whitelist_store.get(approver_tg_id)
                approver_name = approver.full_name if approver else f"Пользователь {approver_tg_id}"
                
                # Отправляем уведомление автору документа
                try:
                    doc_id_str = str(document_id)[:8]
                    await bot.send_message(
                        owner_tg_id,
                        f"❌ <b>Документ отклонен</b>\n\n"
                        f"📄 <b>Название:</b> {title}\n"
                        f"👤 <b>Отклонил:</b> {approver_name}\n"
                        f"💬 <b>Причина:</b> {comment}\n"
                        f"🆔 <b>ID документа:</b> <code>{doc_id_str}</code>",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Ошибка отправки уведомления: {e}")
        
        return True


def get_approval_history(document_id: str) -> List[Dict]:
    """
    Получает историю согласования документа
    
    Returns:
        Список действий по документу
    """
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                h.action,
                h.comment,
                h.created_at,
                h.approver_tg_id
            FROM approval_history h
            WHERE h.document_id = :doc_id
            ORDER BY h.created_at ASC
        """), {"doc_id": document_id})
        
        rows = [dict(row) for row in result.mappings()]
        
        # Получаем имена пользователей из whitelist
        from bot.rbac import WhitelistStore
        store = WhitelistStore("access/whitelist.csv")
        
        for row in rows:
            approver = store.get(row["approver_tg_id"])
            row["approver_name"] = approver.full_name if approver else f"Пользователь {row['approver_tg_id']}"
        
        return rows


def get_overdue_approvals() -> List[Dict]:
    """
    Получает просроченные согласования
    
    Returns:
        Список просроченных документов
    """
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                d.id as document_id,
                d.title,
                w.approver_tg_id,
                w.deadline,
                w.created_at
            FROM approval_workflows w
            JOIN documents d ON d.id = w.document_id
            WHERE w.status = 'pending'
              AND w.deadline < now()
            ORDER BY w.deadline ASC
        """))
        
        return [dict(row) for row in result.mappings()]

