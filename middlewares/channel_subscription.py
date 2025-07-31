from typing import Callable, Dict, Any, Awaitable, List
from aiogram import BaseMiddleware, Bot
from aiogram.types import Update
from keyboards.user_keyboards import build_subscription_keyboard

class ChannelSubscriptionMiddleware(BaseMiddleware):
    def __init__(self, required_channels: List[str], admin_ids: List[int]): super().__init__(); self.required_channels = required_channels; self.admin_ids = admin_ids
    async def __call__(self, handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]], event: Update, data: Dict[str, Any]) -> Any:
        if event.message: user = event.message.from_user
        elif event.callback_query: user = event.callback_query.from_user
        else: return await handler(event, data)
        if not user or user.id in self.admin_ids: return await handler(event, data)
        bot: Bot = data.get('bot'); unsubscribed = []
        for channel in self.required_channels:
            try:
                if (await bot.get_chat_member(chat_id=channel, user_id=user.id)).status not in ['creator', 'administrator', 'member']: unsubscribed.append(channel)
            except Exception: unsubscribed.append(channel)
        if unsubscribed:
            text = "🚨 <b>Access Denied</b>\n\nTo use this bot, you must join our channels:"; kbd = build_subscription_keyboard(unsubscribed)
            if event.message: await event.message.answer(text, reply_markup=kbd)
            elif event.callback_query: await event.callback_query.answer(); await event.callback_query.message.answer(text, reply_markup=kbd)
            return
        return await handler(event, data)