import html
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from database.models import User
from keyboards.user_keyboards import build_main_menu_keyboard
from utils.localization import translator

router = Router()
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")

async def send_welcome_message(message: Message, user: User):
    """A dedicated function to send the welcome message."""
    user_name = html.escape(user.first_name)
    lang = user.language_code
    
    welcome_text = translator.get_string("welcome_message", lang, user_name=user_name)
    
    await message.answer(welcome_text, reply_markup=build_main_menu_keyboard(lang))


@router.message(CommandStart())
async def command_start_handler(message: Message, user: User):
    """
    Handles the /start command.
    The 'user' object is guaranteed to be present by the UserMiddleware.
    """
    await send_welcome_message(message, user)

@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(cb: CallbackQuery, user: User):
    """
    Handles the 'I've Joined' button click.
    The 'user' object is guaranteed to be present by the UserMiddleware.
    """
    await cb.message.delete()
    await cb.answer("Thank you for subscribing!", show_alert=True)
    await send_welcome_message(cb.message, user)