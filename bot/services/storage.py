from bot import config
from minio import Minio
from io import BytesIO
import hashlib
from datetime import timedelta

_client = Minio(
    config.MINIO_ENDPOINT,
    access_key=config.MINIO_ACCESS_KEY,
    secret_key=config.MINIO_SECRET_KEY,
    secure=config.MINIO_SECURE,
)
MINIO_BUCKET = config.MINIO_BUCKET


def ensure_bucket() -> None:
    if not _client.bucket_exists(MINIO_BUCKET):
        _client.make_bucket(MINIO_BUCKET)

def put_object_bytes(key: str, data: bytes, content_type: str) -> None:
    """Новая базовая функция: кладёт байты в MinIO по ключу."""
    bio = BytesIO(data)
    _client.put_object(
        MINIO_BUCKET,
        key,
        data=bio,
        length=len(data),
        content_type=content_type or "application/octet-stream",
    )

def get_object_bytes(key: str) -> bytes:
    resp = _client.get_object(MINIO_BUCKET, key)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()

def presigned_get_url(key: str, expires_seconds: int | float = 3600) -> str:
    # MinIO ограничивает TTL 1..7 дней
    secs = int(expires_seconds)
    secs = max(1, min(secs, 7 * 24 * 3600))
    return _client.presigned_get_object(
        MINIO_BUCKET,
        key,
        expires=timedelta(seconds=secs),  # <-- важно: timedelta
    )

# --------- СОВМЕСТИМАЯ ОБЁРТКА (оставь имя upload_bytes) ----------
def migrate_old_files():
    """
    Мигрирует старые файлы из структуры files/ в новую структуру documents/
    """
    try:
        print("Начинаем миграцию старых файлов...")
        
        # Получаем список всех объектов в папке files/
        objects = _client.list_objects(MINIO_BUCKET, prefix="files/", recursive=True)
        
        migrated_count = 0
        for obj in objects:
            if obj.is_dir:
                continue
                
            # Скачиваем файл
            data = get_object_bytes(obj.object_name)
            
            # Определяем user_id из БД (если возможно)
            # Пока что используем fallback структуру
            from datetime import datetime
            now = datetime.now()
            year = now.strftime("%Y")
            month = now.strftime("%m")
            
            # Создаем новый ключ в общей папке
            filename = obj.object_name.split('/')[-1]  # Последняя часть пути
            new_key = f"documents/{year}/{month}/migrated/{filename}"
            
            # Загружаем в новое место
            put_object_bytes(new_key, data, "application/octet-stream")
            
            print(f"Мигрирован: {obj.object_name} -> {new_key}")
            migrated_count += 1
        
        print(f"Миграция завершена. Обработано файлов: {migrated_count}")
        return migrated_count
        
    except Exception as e:
        print(f"Ошибка при миграции: {e}")
        return 0


def upload_bytes(*, user_id: int | None = None, title: str | None = None,
                 mime: str, ext: str = "", data: bytes) -> tuple[str, str, int]:
    """
    Загружает файл в MinIO с понятной структурой папок по именам пользователей.
    Возвращает (key, sha256, size).
    """
    size = len(data)
    sha256 = hashlib.sha256(data).hexdigest()
    
    # Создаем понятную структуру папок
    from datetime import datetime
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    
    # Формируем понятный ключ с именем пользователя
    if user_id:
        # Получаем имя пользователя из whitelist
        from bot.rbac import WhitelistStore
        store = WhitelistStore("access/whitelist.csv")
        user = store.get(user_id)
        
        if user:
            # Используем имя пользователя (заменяем пробелы на подчеркивания)
            user_name = user.full_name.replace(" ", "_")
            # Используем оригинальное имя файла или создаем понятное
            if title:
                # Убираем недопустимые символы для имени файла
                safe_title = "".join(c for c in title if c.isalnum() or c in "._- ").strip()
                safe_title = safe_title.replace(" ", "_")
                filename = f"{safe_title}_{sha256[:6]}{ext}"
            else:
                filename = f"document_{sha256[:6]}{ext}"
            key = f"documents/{year}/{month}/{user_name}/{filename}"
        else:
            # Fallback для пользователей не из whitelist
            filename = f"{sha256[:8]}{ext}"
            key = f"documents/{year}/{month}/user_{user_id}/{filename}"
    else:
        # Fallback для старых файлов
        key = f"files/{sha256[:2]}/{sha256[2:4]}/{sha256}"
    
    # Кладём в MinIO
    put_object_bytes(key, data, mime or "application/octet-stream")
    return key, sha256, size