from uuid import uuid4
from typing import Optional
from sqlalchemy import text
from bot.db.session import engine


def ensure_file(*, minio_key: str, sha256: str, mime: str, ext: str, size_bytes: int) -> str:
    with engine.begin() as conn:
        row = conn.execute(text("SELECT id FROM files WHERE sha256=:h"), {"h": sha256}).fetchone()
        if row:
            return row[0]
        fid = str(uuid4())
        conn.execute(text("""
            INSERT INTO files (id, minio_key, sha256, mime, ext, size_bytes)
            VALUES (:id, :k, :h, :m, :e, :s)
        """), {"id": fid, "k": minio_key, "h": sha256, "m": mime, "e": ext, "s": size_bytes})
        return fid

def create_document(*, title: str, kind: str, owner_tg_id: int) -> str:
    did = str(uuid4())
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO documents (id, title, kind, owner_tg_id)
            VALUES (:id, :t, :k, :o)
        """), {"id": did, "t": title, "k": kind, "o": owner_tg_id})
    return did

def add_version(*, document_id: str, file_id: str, author_tg_id: int, note: Optional[str] = None) -> tuple[str, int]:
    with engine.begin() as conn:
        last = conn.execute(text(
            "SELECT COALESCE(MAX(version_no), 0) FROM document_versions WHERE document_id=:d"
        ), {"d": document_id}).scalar_one()
        next_no = int(last) + 1
        vid = str(uuid4())
        conn.execute(text("""
            INSERT INTO document_versions (id, document_id, file_id, version_no, author_tg_id, note)
            VALUES (:id, :d, :f, :n, :a, :note)
        """), {"id": vid, "d": document_id, "f": file_id, "n": next_no, "a": author_tg_id, "note": note})
        conn.execute(text("UPDATE documents SET current_version_id=:v WHERE id=:d"),
                     {"v": vid, "d": document_id})
        return vid, next_no

def get_version_info_by_id(version_id: str) -> dict | None:
    sql = text("""
        SELECT
          v.id,
          v.version_no,
          v.document_id,
          d.title,
          f.minio_key,
          f.mime   AS mime_type,
          f.ext,
          f.size_bytes
        FROM document_versions v
        JOIN documents d ON d.id = v.document_id
        JOIN files     f ON f.id = v.file_id
        WHERE v.id = CAST(:vid AS UUID)               -- <-- важный каст
        LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(sql, {"vid": version_id}).mappings().first()
        return dict(row) if row else None



def list_user_documents(tg_id: int, limit: int = 10) -> list[dict]:
    sql = text("""
        SELECT
          d.id,
          d.title,
          d.created_at,
          d.current_version_id,
          v.version_no,
          v.id               AS version_id,
          f.minio_key,
          f.mime             AS mime_type,
          f.ext,
          f.size_bytes
        FROM documents d
        LEFT JOIN document_versions v
               ON v.id = d.current_version_id
        LEFT JOIN files f
               ON f.id = v.file_id
        WHERE d.owner_tg_id = :tg_id
        ORDER BY d.created_at DESC
        LIMIT :limit
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"tg_id": tg_id, "limit": limit}).mappings().all()
        return [dict(r) for r in rows]

