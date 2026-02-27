"""
Утилиты для DocuBot
"""
from typing import Union
from pathlib import Path


def bytes_to_human(n: int) -> str:
    """
    Конвертирует размер в байтах в человекочитаемый формат
    
    Args:
        n: Размер в байтах
        
    Returns:
        Строка с размером (например, "1.5 MB")
    """
    if n == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    
    if i == 0:
        return f"{n} {units[i]}"
    else:
        return f"{n:.1f} {units[i]}"


def format_date(date_obj) -> str:
    """
    Форматирует дату в читаемый вид
    
    Args:
        date_obj: Объект даты (datetime, date, str)
        
    Returns:
        Отформатированная строка даты
    """
    if not date_obj:
        return "Не указано"
    
    if hasattr(date_obj, 'strftime'):
        return date_obj.strftime("%d.%m.%Y %H:%M")
    else:
        return str(date_obj)


def truncate_text(text: str, max_length: int = 50) -> str:
    """
    Обрезает текст до указанной длины
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
        
    Returns:
        Обрезанный текст с многоточием
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."


def validate_file_size(size_bytes: int, max_mb: int = 20) -> bool:
    """
    Проверяет размер файла
    
    Args:
        size_bytes: Размер файла в байтах
        max_mb: Максимальный размер в МБ
        
    Returns:
        True если размер допустим
    """
    max_bytes = max_mb * 1024 * 1024
    return size_bytes <= max_bytes


def validate_file_extension(filename: str, allowed_extensions: set) -> bool:
    """
    Проверяет расширение файла
    
    Args:
        filename: Имя файла
        allowed_extensions: Множество допустимых расширений
        
    Returns:
        True если расширение допустимо
    """
    if not filename:
        return False
    
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    return ext in allowed_extensions


def short_type(file_name: str | None, mime: str | None) -> str:
    """
    Определяет короткий тип файла по имени и MIME
    
    Args:
        file_name: Имя файла
        mime: MIME тип
        
    Returns:
        Короткий тип файла (pdf, docx, unknown)
    """
    ext = (Path(file_name or "").suffix or "").lower()
    if ext in {".pdf", ".docx"}:
        return ext.lstrip(".")            # -> "pdf" | "docx"
    # fallback по MIME
    if (mime or "").lower().startswith("application/pdf"):
        return "pdf"
    if (mime or "") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return "docx"
    return "unknown"


def safe_int(value: Union[str, int, None], default: int = 0) -> int:
    """
    Безопасно конвертирует значение в int
    
    Args:
        value: Значение для конвертации
        default: Значение по умолчанию
        
    Returns:
        Целое число или значение по умолчанию
    """
    if value is None:
        return default
    
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_str(value: Union[str, int, None], default: str = "") -> str:
    """
    Безопасно конвертирует значение в строку
    
    Args:
        value: Значение для конвертации
        default: Значение по умолчанию
        
    Returns:
        Строка или значение по умолчанию
    """
    if value is None:
        return default
    
    try:
        return str(value)
    except (ValueError, TypeError):
        return default
