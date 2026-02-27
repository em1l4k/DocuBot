"""
Сервис кэширования для DocuBot
"""
import asyncio
import time
from typing import Any, Dict, Optional, Callable, Union
from functools import wraps
import logging


class CacheService:
    """Сервис для кэширования данных"""
    
    def __init__(self, default_ttl: int = 300):
        """
        Инициализация сервиса кэширования
        
        Args:
            default_ttl: Время жизни кэша по умолчанию в секундах
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.logger = logging.getLogger(__name__)
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """Проверяет, истек ли срок действия кэша"""
        if 'expires_at' not in cache_entry:
            return True
        
        return time.time() > cache_entry['expires_at']
    
    def get(self, key: str) -> Optional[Any]:
        """
        Получает значение из кэша
        
        Args:
            key: Ключ кэша
            
        Returns:
            Значение из кэша или None если не найдено/истекло
        """
        if key not in self._cache:
            return None
        
        cache_entry = self._cache[key]
        
        if self._is_expired(cache_entry):
            del self._cache[key]
            return None
        
        return cache_entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Сохраняет значение в кэш
        
        Args:
            key: Ключ кэша
            value: Значение для сохранения
            ttl: Время жизни в секундах (по умолчанию используется default_ttl)
        """
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl
        
        self._cache[key] = {
            'value': value,
            'expires_at': expires_at,
            'created_at': time.time()
        }
        
        self.logger.debug(f"Cached key '{key}' with TTL {ttl}s")
    
    def delete(self, key: str) -> bool:
        """
        Удаляет значение из кэша
        
        Args:
            key: Ключ кэша
            
        Returns:
            True если ключ был удален, False если не найден
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Очищает весь кэш"""
        self._cache.clear()
        self.logger.info("Cache cleared")
    
    def cleanup_expired(self) -> int:
        """
        Удаляет истекшие записи из кэша
        
        Returns:
            Количество удаленных записей
        """
        expired_keys = []
        for key, cache_entry in self._cache.items():
            if self._is_expired(cache_entry):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику кэша
        
        Returns:
            Словарь со статистикой
        """
        total_entries = len(self._cache)
        expired_entries = sum(1 for entry in self._cache.values() if self._is_expired(entry))
        active_entries = total_entries - expired_entries
        
        return {
            'total_entries': total_entries,
            'active_entries': active_entries,
            'expired_entries': expired_entries,
            'memory_usage': len(str(self._cache))
        }
    
    def get_or_set(self, key: str, factory: Callable[[], Any], ttl: Optional[int] = None) -> Any:
        """
        Получает значение из кэша или создает его с помощью factory функции
        
        Args:
            key: Ключ кэша
            factory: Функция для создания значения
            ttl: Время жизни в секундах
            
        Returns:
            Значение из кэша или созданное значение
        """
        cached_value = self.get(key)
        if cached_value is not None:
            return cached_value
        
        value = factory()
        self.set(key, value, ttl)
        return value


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Декоратор для кэширования результатов функций
    
    Args:
        ttl: Время жизни кэша в секундах
        key_prefix: Префикс для ключа кэша
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Создаем ключ кэша на основе аргументов функции
            cache_key = f"{key_prefix}{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Получаем глобальный экземпляр кэша
            cache = get_cache_service()
            
            # Проверяем кэш
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Выполняем функцию и кэшируем результат
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Создаем ключ кэша на основе аргументов функции
            cache_key = f"{key_prefix}{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Получаем глобальный экземпляр кэша
            cache = get_cache_service()
            
            # Проверяем кэш
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Выполняем функцию и кэшируем результат
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            
            return result
        
        # Возвращаем правильную обертку в зависимости от типа функции
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Глобальный экземпляр кэша
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Получает глобальный экземпляр сервиса кэширования"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


def init_cache_service(default_ttl: int = 300) -> CacheService:
    """
    Инициализирует глобальный сервис кэширования
    
    Args:
        default_ttl: Время жизни кэша по умолчанию в секундах
        
    Returns:
        Экземпляр сервиса кэширования
    """
    global _cache_service
    _cache_service = CacheService(default_ttl)
    return _cache_service


async def cleanup_cache_periodically(interval: int = 60):
    """
    Периодически очищает истекшие записи из кэша
    
    Args:
        interval: Интервал очистки в секундах
    """
    cache = get_cache_service()
    
    while True:
        try:
            await asyncio.sleep(interval)
            cache.cleanup_expired()
        except Exception as e:
            logging.error(f"Error during cache cleanup: {e}")


# Специализированные кэши для разных типов данных
class UserCache:
    """Кэш для данных пользователей"""
    
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
        self.user_ttl = 600  # 10 минут
    
    def get_user_role(self, user_id: int) -> Optional[str]:
        """Получает роль пользователя из кэша"""
        return self.cache.get(f"user_role:{user_id}")
    
    def set_user_role(self, user_id: int, role: str) -> None:
        """Сохраняет роль пользователя в кэш"""
        self.cache.set(f"user_role:{user_id}", role, self.user_ttl)
    
    def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает информацию о пользователе из кэша"""
        return self.cache.get(f"user_info:{user_id}")
    
    def set_user_info(self, user_id: int, user_info: Dict[str, Any]) -> None:
        """Сохраняет информацию о пользователе в кэш"""
        self.cache.set(f"user_info:{user_id}", user_info, self.user_ttl)


class StatsCache:
    """Кэш для статистики"""
    
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
        self.stats_ttl = 300  # 5 минут
    
    def get_total_documents(self) -> Optional[int]:
        """Получает общее количество документов из кэша"""
        return self.cache.get("total_documents")
    
    def set_total_documents(self, count: int) -> None:
        """Сохраняет общее количество документов в кэш"""
        self.cache.set("total_documents", count, self.stats_ttl)
    
    def get_documents_by_status(self) -> Optional[Dict[str, int]]:
        """Получает количество документов по статусам из кэша"""
        return self.cache.get("documents_by_status")
    
    def set_documents_by_status(self, stats: Dict[str, int]) -> None:
        """Сохраняет количество документов по статусам в кэш"""
        self.cache.set("documents_by_status", stats, self.stats_ttl)
    
    def get_storage_usage(self) -> Optional[Dict[str, Any]]:
        """Получает статистику использования хранилища из кэша"""
        return self.cache.get("storage_usage")
    
    def set_storage_usage(self, usage: Dict[str, Any]) -> None:
        """Сохраняет статистику использования хранилища в кэш"""
        self.cache.set("storage_usage", usage, self.stats_ttl)
