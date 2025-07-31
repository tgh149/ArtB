import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault, User as AiogramUser
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy.exc import IntegrityError

# --- Switch to Memory storage for Replit compatibility ---
from aiogram.fsm.storage.memory import MemoryStorage

from config_data.config import config
from database.engine import async_engine, async_session_factory, DbSessionMiddleware
from database.models import Base, User
from middlewares.channel_subscription import ChannelSubscriptionMiddleware
from middlewares.ban_middleware import BanMiddleware
from handlers import admin_handlers
from handlers.user_handlers import start, main_menu, purchase, common_handlers
from utils.currency_converter import currency_converter

# This new format creates clean, aligned columns for better readability.
log_format = '[%(asctime)s] [%(levelname)-8s] [%(name)-24s]  %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format, datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


class UserMiddleware(DbSessionMiddleware):
    async def __call__(self, handler, event, data):
        async with self.session_pool() as session:
            data["session"] = session

            from_user: AiogramUser | None = data.get("event_from_user")

            if not from_user:
                return await handler(event, data)

            db_user = await session.get(User, from_user.id)

            if not db_user:
                user_lang = from_user.language_code
                if user_lang not in ['en', 'ru', 'zh']:
                    user_lang = 'en'

                new_user = User(
                    user_id=from_user.id,
                    username=from_user.username,
                    first_name=from_user.first_name,
                    language_code=user_lang
                )
                session.add(new_user)
                try:
                    await session.commit()
                    await session.refresh(new_user)
                    db_user = new_user
                    logger.info(f"New user created: {db_user.user_id} (@{db_user.username})")
                except IntegrityError:
                    logger.warning(f"Race condition on user creation for ID {from_user.id}. Fetching existing user.")
                    await session.rollback()
                    db_user = await session.get(User, from_user.id)

            data["user"] = db_user

            return await handler(event, data)


async def set_bot_commands(bot: Bot):
    user_commands = [
        BotCommand(command='/start', description='🚀 Start/Reload the Bot'),
        BotCommand(command='/cancel', description='❌ Cancel current operation')
    ]
    await bot.set_my_commands(user_commands, BotCommandScopeDefault())

    admin_commands = user_commands + [
        BotCommand(command='/admin', description='👑 Open Admin Panel')
    ]
    for admin_id in config.admin_ids:
        try:
            await bot.set_my_commands(admin_commands, BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            logger.error(f"Could not set commands for admin {admin_id}: {e}")

async def on_startup(bot: Bot):
    await set_bot_commands(bot)
    logger.info("Scoped bot commands have been set.")
    currency_converter.start_background_update()

async def main():
    logger.info("Starting bot...")

    # --- Use Memory storage for Replit compatibility ---
    storage = MemoryStorage()

    dp = Dispatcher(storage=storage)

    dp.startup.register(on_startup)

    async with async_engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)

    # --- MIDDLEWARE ORDER IS CRITICAL ---
    dp.update.middleware(UserMiddleware(session_pool=async_session_factory))
    dp.update.middleware(BanMiddleware())
    dp.update.middleware(ChannelSubscriptionMiddleware(required_channels=config.required_channels, admin_ids=config.admin_ids))

    # Include routers (admin handlers first for priority)
    dp.include_router(admin_handlers.router)
    dp.include_router(start.router)
    dp.include_router(main_menu.router)
    dp.include_router(purchase.router)
    dp.include_router(common_handlers.router)

    default_properties = DefaultBotProperties(parse_mode=ParseMode.HTML)
    bot = Bot(token=config.bot_token.get_secret_value(), default=default_properties)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        currency_converter.stop_background_update()

if __name__ == '__main__':
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): logger.info("Bot stopped.")