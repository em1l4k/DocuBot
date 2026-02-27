import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing in .env")

MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "20"))

ALLOWED_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
}
ALLOWED_EXT = {".pdf", ".docx"}

WHITELIST_PATH = os.getenv("WHITELIST_PATH", "access/whitelist.csv")

DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("DB_DSN")
    or "postgresql+psycopg2://user:pass@localhost:5432/db"
)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET     = os.getenv("MINIO_BUCKET", "docs")
MINIO_SECURE     = os.getenv("MINIO_SECURE", "false").lower() in ("1","true","yes","on")
PRESIGN_TTL_MIN = int(os.getenv("PRESIGN_TTL_MIN", "60"))