import datetime
import os
import shutil
import io
import zipfile
import re
import asyncio
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from decimal import Decimal
from telethon import TelegramClient, errors

from config_data.config import config
from database.models import Country, User, Account
from database.engine import async_session_factory
from keyboards.purchase_keyboards import *
from utils.states import BrowsingStates
from utils.delivery import create_session_zip_file
from utils.stock_manager import ACCOUNTS_DIR, get_country_name
from utils.localization import translator
from utils.currency_converter import currency_converter

router = Router()
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")

TEMP_SESSIONS_DIR = "temp_sessions"
if not os.path.exists(TEMP_SESSIONS_DIR):
    os.makedirs(TEMP_SESSIONS_DIR)

def parse_phone_from_string(data_string: str) -> str:
    """Extracts a clean phone number from various combined formats like 'ID_PHONE'."""
    if data_string.startswith('+'):
        return data_string

    phone_part = data_string

    if '_' in data_string:
        phone_part = data_string.split('_')[-1]
    elif ':' in data_string:
        phone_part = data_string.split(':')[-1]

    cleaned_phone = re.sub(r'[^\d]', '', phone_part)
    if cleaned_phone:
        return f"+{cleaned_phone}"

    return data_string

async def move_sold_file(folder_name: str, product_name: str):
    """Move sold file to sold folder"""
    try:
        folder_path = os.path.join(ACCOUNTS_DIR, folder_name)
        sold_path = os.path.join(folder_path, "sold")

        if not os.path.exists(sold_path):
            os.makedirs(sold_path)

        source_file = os.path.join(folder_path, product_name)
        destination_file = os.path.join(sold_path, product_name)

        if os.path.exists(source_file):
            await asyncio.to_thread(shutil.move, source_file, destination_file)
            return True
        else:
            print(f"Source file not found: {source_file}")
            return False
    except Exception as e:
        print(f"Error moving file {product_name}: {e}")
        return False

def get_session_file_content(folder_name: str, product_name: str) -> bytes:
    """Get session file content"""
    try:
        file_path = os.path.join(ACCOUNTS_DIR, folder_name, product_name)
        with open(file_path, 'rb') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading session file {product_name}: {e}")
        return b""

@router.callback_query(F.data.startswith("confirm_purchase_"))
async def confirm_purchase_handler(cb: CallbackQuery, state: FSMContext, session: AsyncSession, user: User, bot: Bot):
    try:
        parts = cb.data.replace("confirm_purchase_", "").split("_")
        folder_name = parts[0]
        product_idx = int(parts[1])
        quantity = int(parts[2])

        data = await state.get_data()
        product_list = data.get('product_list', [])
        
        if product_idx >= len(product_list):
            await cb.answer("❌ Product not found", show_alert=True)
            return

        product_name = product_list[product_idx]

        price_per_item = 1.5
        total_cost = Decimal(str(price_per_item * quantity))

        # Check user balance
        if Decimal(str(user.balance)) < total_cost:
            await cb.answer("❌ Insufficient balance!", show_alert=True)
            return

        # Get available products
        folder_path = os.path.join(ACCOUNTS_DIR, folder_name)
        available_products = [f for f in os.listdir(folder_path) 
                             if f.endswith('.session') and not f.startswith('sold')]

        if len(available_products) < quantity:
            await cb.answer("❌ Not enough stock available!", show_alert=True)
            return

        # Process purchase
        await cb.message.edit_text("⏳ Processing your purchase...")

        # Deduct balance
        user.balance = Decimal(str(user.balance)) - total_cost
        await session.commit()

        # Select products to deliver
        products_to_deliver = available_products[:quantity]

        # Create ZIP file with products
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for product in products_to_deliver:
                try:
                    session_content = get_session_file_content(folder_name, product)
                    if session_content:
                        zip_file.writestr(product, session_content)
                except Exception as e:
                    print(f"Error adding {product} to ZIP: {e}")

        # Send ZIP file to user
        zip_buffer.seek(0)
        display_name = folder_name.replace('+', '').replace('_', ' ').title()
        input_file = BufferedInputFile(
            zip_buffer.read(), 
            filename=f"{display_name}_x{quantity}.zip"
        )

        await bot.send_document(
            chat_id=cb.from_user.id,
            document=input_file,
            caption=f"✅ <b>Purchase Complete!</b>\n\n"
                   f"📦 Product: {display_name}\n"
                   f"📊 Quantity: {quantity}\n"
                   f"💰 Total: ${total_cost}\n\n"
                   f"Thank you for your purchase!"
        )

        # Move sold files
        move_tasks = [move_sold_file(folder_name, product) for product in products_to_deliver]
        await asyncio.gather(*move_tasks)

        await cb.message.edit_text(
            f"✅ <b>Purchase Successful!</b>\n\n"
            f"Your {quantity} account(s) have been delivered.\n"
            f"Check your files above! 👆"
        )

        await state.clear()
        await cb.answer()

    except Exception as e:
        print(f"Error in purchase: {e}")
        await cb.message.edit_text("❌ An error occurred during purchase. Please contact support.")
        await cb.answer()