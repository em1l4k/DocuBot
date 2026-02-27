from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import csv
from typing import Dict, Optional
import time
from bot.services.cache import get_cache_service

class Role(str, Enum):
    employee = "employee"
    manager = "manager"
    admin = "admin"


class Permission(str, Enum):
    # Базовые права
    VIEW_DOCUMENTS = "view_documents"
    UPLOAD_DOCUMENTS = "upload_documents"
    DOWNLOAD_DOCUMENTS = "download_documents"
    
    # Права согласования
    APPROVE_DOCUMENTS = "approve_documents"
    REJECT_DOCUMENTS = "reject_documents"
    DELEGATE_APPROVAL = "delegate_approval"
    
    # Административные права
    MANAGE_USERS = "manage_users"
    MANAGE_WORKFLOWS = "manage_workflows"
    VIEW_STATISTICS = "view_statistics"

@dataclass
class UserEntry:
    telegram_id: int
    role: Role
    full_name: str
    is_active: bool
    
    def has_permission(self, permission: Permission) -> bool:
        """Проверяет, есть ли у пользователя указанное право"""
        role_permissions = {
            Role.employee: {
                Permission.VIEW_DOCUMENTS,
                Permission.UPLOAD_DOCUMENTS,
                Permission.DOWNLOAD_DOCUMENTS,
            },
            Role.manager: {
                Permission.VIEW_DOCUMENTS,
                Permission.UPLOAD_DOCUMENTS,
                Permission.DOWNLOAD_DOCUMENTS,
                Permission.APPROVE_DOCUMENTS,
                Permission.REJECT_DOCUMENTS,
                Permission.DELEGATE_APPROVAL,
            },
            Role.admin: {
                Permission.VIEW_DOCUMENTS,
                Permission.UPLOAD_DOCUMENTS,
                Permission.DOWNLOAD_DOCUMENTS,
                Permission.APPROVE_DOCUMENTS,
                Permission.REJECT_DOCUMENTS,
                Permission.DELEGATE_APPROVAL,
                Permission.MANAGE_USERS,
                Permission.MANAGE_WORKFLOWS,
                Permission.VIEW_STATISTICS,
            }
        }
        
        return permission in role_permissions.get(self.role, set())
    
    def can_approve_document(self, document_owner_tg_id: int) -> bool:
        """Проверяет, может ли пользователь согласовывать документ"""
        if not self.has_permission(Permission.APPROVE_DOCUMENTS):
            return False
        
        # Менеджеры могут согласовывать документы сотрудников
        if self.role == Role.manager:
            return True
        
        # Админы могут согласовывать любые документы
        if self.role == Role.admin:
            return True
        
        return False

def _to_bool(v: str) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}

def load_whitelist(path: Path) -> Dict[int, UserEntry]:
    users: Dict[int, UserEntry] = {}
    if not path.exists():
        return users
    
    # Пробуем разные кодировки
    encodings = ['utf-8', 'utf-8-sig', 'cp1251', 'latin1']
    
    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        tid = int(row["telegram_id"])
                        role = Role(row["role"].strip())
                        full_name = (row.get("full_name") or "").strip()
                        is_active = _to_bool(row.get("is_active", "true"))
                        users[tid] = UserEntry(telegram_id=tid, role=role, full_name=full_name, is_active=is_active)
                    except Exception as e:
                        print(f"Ошибка обработки строки: {row}, ошибка: {e}")
                        continue
                break  # Если успешно прочитали, выходим из цикла
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"Ошибка чтения файла с кодировкой {encoding}: {e}")
            continue
    
    return users

# Глобальный экземпляр store
_global_store = None

class WhitelistStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.users: Dict[int, UserEntry] = {}
        self.cache = get_cache_service()
        self.last_reload = 0
        self.reload()
        # Сохраняем как глобальный экземпляр
        global _global_store
        _global_store = self

    def reload(self) -> int:
        """Перезагружает whitelist с принудительной очисткой кэша"""
        # Очищаем кэш принудительно
        cache_key = f"whitelist:{self.path}"
        self.cache.delete(cache_key)
        
        # Очищаем кэш пользователей
        for user_id in list(self.users.keys()):
            user_cache_key = f"user:{user_id}"
            self.cache.delete(user_cache_key)
        
        # Принудительно обновляем время модификации файла
        import os
        if self.path.exists():
            os.utime(self.path, None)
        
        # Загружаем из файла
        self.users = load_whitelist(self.path)
        self.last_reload = time.time()
        
        # Сохраняем в кэш
        self.cache.set(cache_key, {
            'users': self.users,
            'last_modified': self.last_reload
        }, ttl=600)  # 10 минут
        
        return len(self.users)

    def get(self, telegram_id: int) -> Optional[UserEntry]:
        """Получает пользователя с кэшированием"""
        # Проверяем кэш пользователя
        user_cache_key = f"user:{telegram_id}"
        cached_user = self.cache.get(user_cache_key)
        
        if cached_user:
            return cached_user
        
        # Получаем из основного кэша
        user = self.users.get(telegram_id)
        
        if user:
            # Кэшируем пользователя отдельно
            self.cache.set(user_cache_key, user, ttl=300)  # 5 минут
        
        return user

def get_global_store() -> Optional['WhitelistStore']:
    """Получает глобальный экземпляр WhitelistStore"""
    return _global_store
