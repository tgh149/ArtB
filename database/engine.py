from typing import Callable, Awaitable, Dict, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from config_data.config import config

async_engine = create_async_engine(config.db_url)
async_session_factory = async_sessionmaker(async_engine, expire_on_commit=False)

class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker): super().__init__(); self.session_pool = session_pool
    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: Dict[str, Any]) -> Any:
        async with self.session_pool() as session: data["session"] = session; return await handler(event, data)