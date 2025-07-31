from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.user_keyboards import build_main_menu_keyboard
from database.models import User
from utils.localization import translator

router = Router()

@router.message(Command("cancel"))
@router.callback_query(F.data == "global_cancel")
async def cmd_cancel(event: Message | CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    current_state = await state.get_state()
    lang = user.language_code
    
    if current_state is None:
        message_to_send = translator.get_string("cancel_nothing", lang)
    else:
        message_to_send = translator.get_string("cancel_success", lang)
    
    await state.clear()
    
    message_to_use = event if isinstance(event, Message) else event.message
    
    if isinstance(event, CallbackQuery):
        await event.answer("Cancelled.", show_alert=False)
        try:
            await event.message.delete()
        except:
            pass

    # --- THE FIX: We now have the `lang` from the user object ---
    await message_to_use.answer(message_to_send, reply_markup=build_main_menu_keyboard(lang))