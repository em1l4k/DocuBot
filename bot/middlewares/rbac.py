from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable, Optional

from bot.rbac import WhitelistStore, UserEntry

class RBACMiddleware(BaseMiddleware):
    def __init__(self, store: WhitelistStore):
        super().__init__()
        self.store = store

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Optional[Any]:
        from_user = getattr(event, "from_user", None)
        telegram_id = getattr(from_user, "id", None)
        # если нет отправителя (например, сервисные апдейты) — пропускаем
        if telegram_id is None:
            return await handler(event, data)

        entry: Optional[UserEntry] = self.store.get(telegram_id)
        if not entry or not entry.is_active:
            # мягко откажем и не пропустим дальше
            answer = getattr(event, "answer", None)
            if callable(answer):
                await answer("Доступ только для сотрудников. Обратитесь к администратору.")
            return None

        # кладём пользователя в контекст, чтобы хэндлеры знали его роль
        data["current_user"] = entry
        return await handler(event, data)
