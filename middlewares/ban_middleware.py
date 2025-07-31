from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Update, User as AiogramUser

from config_data.config import config
from database.models import User

class BanMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        
        # We need the user object, which is added by the UserMiddleware
        # This is why BanMiddleware must run AFTER UserMiddleware
        db_user: User | None = data.get("user")
        
        # If there's no user object, or if the user is an admin, let them pass
        if not db_user or db_user.user_id in config.admin_ids:
            return await handler(event, data)
        
        # If the user is banned, stop processing
        if db_user.is_banned:
            # We can optionally send a message, but for simplicity, we'll just ignore them.
            # You could add: await event.answer("You are banned.")
            return

        # If not banned, proceed to the next handler
        return await handler(event, data)