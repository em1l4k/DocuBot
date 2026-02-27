from pathlib import Path
from sqlalchemy import text
from bot.db.session import engine

def init_schema() -> None:
    """Initialize database schema using existing engine from session.py"""
    sql = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.execute(text(sql))
