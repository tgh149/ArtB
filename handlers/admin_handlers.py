import io
import os
import shutil
import zipfile
import asyncio
import datetime
import logging
import time
import re
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, Document
from aiogram.enums import ContentType
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from config_data.config import config
from database.models import *
from keyboards.admin_keyboards import *
from utils.states import AdminStates
from utils.stock_manager import get_country_name, ACCOUNTS_DIR

router = Router()
logger = logging.getLogger(__name__)

admin_id_filter = F.from_user.id.in_(config.admin_ids)

# --- Main Admin Panel & Navigation ---
@router.message(Command("admin"), F.chat.type == "private", admin_id_filter)
async def admin_panel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer("Current operation cancelled.")
    
    await message.answer("👑 <b>Admin Panel</b>", reply_markup=build_admin_panel_keyboard())

@router.callback_query(F.data == "admin_panel", admin_id_filter)
async def admin_panel_callback(cb: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        
    await cb.message.edit_text("👑 <b>Admin Panel</b>", reply_markup=build_admin_panel_keyboard())
    await cb.answer()

# --- Bot Statistics ---
@router.callback_query(F.data == "admin_stats", admin_id_filter)
async def admin_stats_callback(cb: CallbackQuery, session: AsyncSession):
    total_users = await session.scalar(select(func.count(User.user_id)))
    today = datetime.datetime.now(datetime.timezone.utc).date()
    new_users_today = await session.scalar(select(func.count(User.user_id)).where(func.date(User.registration_date) == today))
    
    total_income_result = await session.execute(select(func.sum(Deposit.amount)).where(Deposit.status == 'approved'))
    total_income = total_income_result.scalar_one_or_none() or 0.0
    
    sold_accounts = await session.scalar(select(func.count(Account.id)).where(Account.is_sold == True))
    total_accounts = await session.scalar(select(func.count(Account.id)))
    
    stats_text = (
        "<b>📊 Bot Statistics</b>\n\n"
        f"👥 <b>Total Users:</b> <code>{total_users}</code>\n"
        f"✨ <b>New Users Today:</b> <code>{new_users_today}</code>\n"
        f"---"
        f"💰 <b>Total Approved Income:</b> <code>${float(total_income):.2f}</code>\n"
        f"---"
        f"🛒 <b>Accounts Sold:</b> <code>{sold_accounts}</code>\n"
        f"📦 <b>Total Accounts in DB:</b> <code>{total_accounts}</code>"
    )
    await cb.message.edit_text(stats_text)
    await cb.answer()

# --- View Deposits ---
@router.callback_query(F.data == "admin_view_deposits", admin_id_filter)
async def admin_view_deposits_callback(cb: CallbackQuery):
    await cb.answer("💰 Manual deposit requests appear in the admin channel.", show_alert=True)

# --- User Management (with Ban/Unban) ---
@router.callback_query(F.data == "admin_user_management", admin_id_filter)
async def admin_user_management_callback(cb: CallbackQuery):
    await cb.message.edit_text("👤 <b>User Management</b>\n\nFind a user to view their profile, adjust their balance, or manage their ban status.", reply_markup=build_user_management_keyboard())
    await cb.answer()

@router.callback_query(F.data == "admin_find_user", admin_id_filter)
async def admin_find_user_callback(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("Please send the User's Telegram ID or username (with @).\n\nUse /cancel to abort.")
    await state.set_state(AdminStates.find_user)
    await cb.answer()

@router.message(AdminStates.find_user, F.text, admin_id_filter)
async def admin_process_find_user(message: Message, state: FSMContext, session: AsyncSession):
    user_input = message.text.strip()
    user: User | None = None

    if user_input.startswith('@'):
        user = (await session.execute(select(User).where(User.username == user_input[1:]))).scalar_one_or_none()
    elif user_input.isdigit():
        user = await session.get(User, int(user_input))
    
    if not user:
        await message.answer("❌ User not found. Please try again.")
        return

    await state.clear()
    
    ban_status = "Banned 🚫" if user.is_banned else "Active ✅"
    user_profile = (
        f"👤 <b>User Profile</b>\n\n"
        f"<b>ID:</b> <code>{user.user_id}</code>\n"
        f"<b>Username:</b> @{user.username}\n"
        f"<b>Name:</b> {user.first_name}\n"
        f"<b>Balance:</b> <code>${float(user.balance):.2f}</code>\n"
        f"<b>Status:</b> {ban_status}\n"
        f"<b>Registered:</b> {user.registration_date.strftime('%Y-%m-%d')}"
    )
    await message.answer(user_profile, reply_markup=build_user_profile_keyboard(user))

@router.callback_query(F.data.startswith("admin_ban_"), admin_id_filter)
async def admin_ban_user_callback(cb: CallbackQuery, session: AsyncSession):
    user_id = int(cb.data.split('_')[-1])
    
    if user_id in config.admin_ids:
        await cb.answer("You cannot ban an admin.", show_alert=True)
        return

    user_to_ban = await session.get(User, user_id)
    if not user_to_ban:
        await cb.answer("User not found.", show_alert=True)
        return
        
    user_to_ban.is_banned = True
    await session.commit()
    
    await cb.answer(f"User {user_to_ban.first_name} has been banned.", show_alert=True)
    
    ban_status = "Banned 🚫"
    user_profile = (
        f"👤 <b>User Profile</b>\n\n"
        f"<b>ID:</b> <code>{user_to_ban.user_id}</code>\n"
        f"<b>Username:</b> @{user_to_ban.username}\n"
        f"<b>Name:</b> {user_to_ban.first_name}\n"
        f"<b>Balance:</b> <code>${float(user_to_ban.balance):.2f}</code>\n"
        f"<b>Status:</b> {ban_status}\n"
        f"<b>Registered:</b> {user_to_ban.registration_date.strftime('%Y-%m-%d')}"
    )
    await cb.message.edit_text(user_profile, reply_markup=build_user_profile_keyboard(user_to_ban))

@router.callback_query(F.data.startswith("admin_unban_"), admin_id_filter)
async def admin_unban_user_callback(cb: CallbackQuery, session: AsyncSession):
    user_id = int(cb.data.split('_')[-1])
    user_to_unban = await session.get(User, user_id)

    if not user_to_unban:
        await cb.answer("User not found.", show_alert=True)
        return
        
    user_to_unban.is_banned = False
    await session.commit()
    
    await cb.answer(f"User {user_to_unban.first_name} has been unbanned.", show_alert=True)
    
    ban_status = "Active ✅"
    user_profile = (
        f"👤 <b>User Profile</b>\n\n"
        f"<b>ID:</b> <code>{user_to_unban.user_id}</code>\n"
        f"<b>Username:</b> @{user_to_unban.username}\n"
        f"<b>Name:</b> {user_to_unban.first_name}\n"
        f"<b>Balance:</b> <code>${float(user_to_unban.balance):.2f}</code>\n"
        f"<b>Status:</b> {ban_status}\n"
        f"<b>Registered:</b> {user_to_unban.registration_date.strftime('%Y-%m-%d')}"
    )
    await cb.message.edit_text(user_profile, reply_markup=build_user_profile_keyboard(user_to_unban))

@router.callback_query(F.data.startswith("admin_add_balance_") | F.data.startswith("admin_remove_balance_"), admin_id_filter)
async def admin_adjust_balance_callback(cb: CallbackQuery, state: FSMContext):
    user_id = int(cb.data.split('_')[-1])
    action = "add" if "add" in cb.data else "remove"
    await state.update_data(managed_user_id=user_id, balance_action=action)
    
    await cb.message.edit_text(f"Enter the amount to {action} (e.g., 10.50):\n\nUse /cancel to abort.")
    await state.set_state(AdminStates.adjust_balance_amount)
    await cb.answer()

@router.message(AdminStates.adjust_balance_amount, F.text, admin_id_filter)
async def admin_process_adjust_balance(message: Message, state: FSMContext, session: AsyncSession):
    try:
        amount = Decimal(message.text.strip())
        if amount <= 0: raise ValueError
    except:
        await message.answer("❌ Invalid amount. Please enter a positive number.")
        return

    data = await state.get_data()
    user = await session.get(User, data['managed_user_id'])
    
    if data['balance_action'] == 'add':
        user.balance += amount
        feedback = f"✅ Successfully added ${amount:.2f} to the balance of {user.first_name}."
    else: # remove
        if amount > user.balance:
            await message.answer(f"❌ Cannot remove ${amount:.2f}. User's balance is only ${user.balance:.2f}.")
            return
        user.balance -= amount
        feedback = f"✅ Successfully removed ${amount:.2f} from the balance of {user.first_name}."
    
    await session.commit()
    await state.clear()
    await message.answer(f"{feedback}\n\nNew Balance: <code>${user.balance:.2f}</code>")
    await message.answer("👤 <b>User Management</b>", reply_markup=build_user_management_keyboard())

# --- Messaging (BROADCAST) - ADVANCED ---
@router.callback_query(F.data == "admin_messaging", admin_id_filter)
async def admin_messaging_callback(cb: CallbackQuery):
    await cb.message.edit_text(
        "💬 <b>Messaging</b>\n\nChoose your broadcast audience.",
        reply_markup=build_messaging_keyboard()
    )
    await cb.answer()

@router.callback_query(F.data == "admin_broadcast_all", admin_id_filter)
async def admin_broadcast_all_callback(cb: CallbackQuery, state: FSMContext):
    await state.update_data(target_all=True)
    await cb.message.edit_text(
        "Please send the message you want to broadcast to ALL users.\n\n"
        "You can use formatting, photos, videos, etc.\n\nUse /cancel to abort."
    )
    await state.set_state(AdminStates.get_broadcast_message)
    await cb.answer()

@router.callback_query(F.data == "admin_broadcast_specific", admin_id_filter)
async def admin_broadcast_specific_callback(cb: CallbackQuery):
    await cb.message.edit_text(
        "🎯 <b>Targeted Broadcast</b>\n\nSelect a method to target users.",
        reply_markup=build_broadcast_targeting_keyboard()
    )
    await cb.answer()

@router.callback_query(F.data == "admin_target_by_id", admin_id_filter)
async def admin_target_by_id_callback(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text(
        "Please send the User IDs you want to message.\n\n"
        "You can send them one per line, or separated by commas, spaces, or tabs."
    )
    await state.set_state(AdminStates.get_targeted_user_ids)
    await cb.answer()

@router.message(AdminStates.get_targeted_user_ids, F.text, admin_id_filter)
async def process_targeted_user_ids(message: Message, state: FSMContext, session: AsyncSession):
    raw_ids = re.findall(r'\d+', message.text)
    if not raw_ids:
        await message.answer("❌ No valid User IDs found. Please try again.")
        return

    user_ids = [int(uid) for uid in raw_ids]
    result = await session.execute(select(User.user_id).where(User.user_id.in_(user_ids)))
    valid_user_ids = result.scalars().all()
    
    if not valid_user_ids:
        await message.answer("❌ None of the provided User IDs were found in the database. Please try again.")
        return

    await state.update_data(targeted_ids=valid_user_ids)
    
    await message.answer(
        f"✅ Found {len(valid_user_ids)} valid user(s).\n\n"
        "Now, please send the message you want to broadcast to them."
    )
    await state.set_state(AdminStates.get_broadcast_message)

@router.callback_query(F.data == "admin_target_by_country", admin_id_filter)
async def admin_target_by_country_callback(cb: CallbackQuery, session: AsyncSession):
    result = await session.execute(
        select(Country).join(Account).where(Account.is_sold == True).distinct().order_by(Country.name)
    )
    countries = result.scalars().all()

    if not countries:
        await cb.answer("No accounts have been sold yet from any country.", show_alert=True)
        return

    await cb.message.edit_text(
        "🛍 <b>Select Country</b>\n\nChoose a country to message all users who have purchased an account from it.",
        reply_markup=build_broadcast_country_select_keyboard(countries)
    )
    await cb.answer()

@router.callback_query(F.data.startswith("admin_broadcast_select_country_"), admin_id_filter)
async def process_broadcast_country_selection(cb: CallbackQuery, state: FSMContext, session: AsyncSession):
    country_id = int(cb.data.split('_')[-1])
    
    result = await session.execute(
        select(User.user_id).join(Account, User.user_id == Account.buyer_id).where(Account.country_id == country_id).distinct()
    )
    user_ids = result.scalars().all()
    
    if not user_ids:
        await cb.answer("No users found for this country.", show_alert=True)
        return

    await state.update_data(targeted_ids=user_ids)
    
    await cb.message.edit_text(
        f"✅ Found {len(user_ids)} user(s) who purchased from this country.\n\n"
        "Now, please send the message you want to broadcast to them."
    )
    await state.set_state(AdminStates.get_broadcast_message)
    await cb.answer()

@router.message(
    AdminStates.get_broadcast_message,
    F.content_type.in_({
        ContentType.TEXT, ContentType.PHOTO, ContentType.VIDEO, ContentType.DOCUMENT,
        ContentType.STICKER, ContentType.ANIMATION, ContentType.VOICE
    }),
    admin_id_filter
)
async def admin_get_broadcast_message(message: Message, state: FSMContext, bot: Bot, session: AsyncSession):
    data = await state.get_data()
    
    if data.get('target_all'):
        user_count = await session.scalar(select(func.count(User.user_id)))
    else:
        user_count = len(data.get('targeted_ids', []))

    if user_count == 0:
        await message.answer("Error: No users to send to. Please start over.")
        await state.clear()
        return

    await state.update_data(
        broadcast_chat_id=message.chat.id,
        broadcast_message_id=message.message_id
    )
    await bot.copy_message(
        chat_id=message.chat.id,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        reply_markup=build_broadcast_confirmation_keyboard(user_count)
    )
    await state.set_state(AdminStates.confirm_broadcast)

@router.callback_query(F.data == "admin_confirm_broadcast", AdminStates.confirm_broadcast, admin_id_filter)
async def admin_confirm_broadcast_callback(cb: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    
    broadcast_chat_id = data.get('broadcast_chat_id')
    broadcast_message_id = data.get('broadcast_message_id')

    if not broadcast_chat_id or not broadcast_message_id:
        return

    if data.get('target_all'):
        users_result = await session.execute(select(User.user_id))
        user_ids = users_result.scalars().all()
    elif data.get('targeted_ids'):
        user_ids = data.get('targeted_ids')
    else:
        await cb.message.answer("Error: No target audience specified. Please start over.")
        await state.clear()
        return

    await cb.message.edit_reply_markup(None)
    await cb.answer("🚀 Starting broadcast...", show_alert=False)
    
    sent_count = 0
    failed_count = 0
    start_time = time.monotonic()
    
    for user_id in user_ids:
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=broadcast_chat_id,
                message_id=broadcast_message_id
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Broadcast failed for user {user_id}: {type(e).__name__} - {e}")
            failed_count += 1
        await asyncio.sleep(0.04)
        
    end_time = time.monotonic()
    duration = round(end_time - start_time, 2)
    
    await cb.message.answer(
        f"✅ <b>Broadcast Complete!</b>\n\n"
        f"Sent: {sent_count}\n"
        f"Failed: {failed_count}\n"
        f"Total Users: {len(user_ids)}\n"
        f"Duration: {duration}s"
    )
    await state.clear()

@router.message(AdminStates.get_broadcast_message, admin_id_filter)
async def admin_get_broadcast_unsupported_message(message: Message):
    await message.answer("❌ This message type cannot be broadcasted. Please send text, a photo, video, sticker, etc.")

@router.callback_query(F.data == "admin_cancel_broadcast", AdminStates.confirm_broadcast, admin_id_filter)
async def admin_cancel_broadcast_callback(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.delete()
    await cb.message.answer("Broadcast cancelled.")
    await cb.answer()
    
# --- Country & Account Management ---
@router.callback_query(F.data == "admin_country_management", admin_id_filter)
async def admin_country_management_callback(cb: CallbackQuery):
    await cb.message.edit_text("🌍 <b>Country Management</b>", reply_markup=build_country_management_keyboard())
    await cb.answer()

@router.callback_query(F.data == "admin_account_management", admin_id_filter)
async def admin_account_management_callback(cb: CallbackQuery):
    await cb.message.edit_text("📦 <b>Account Management</b>", reply_markup=build_account_management_keyboard())
    await cb.answer()

@router.callback_query(F.data == "admin_add_country", admin_id_filter)
async def admin_add_country_callback(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("📝 Enter country name:\n\nUse /cancel to abort.")
    await state.set_state(AdminStates.add_country_name)
    await cb.answer()

@router.callback_query(F.data == "admin_view_countries", admin_id_filter)
async def admin_view_countries_callback(cb: CallbackQuery, session: AsyncSession):
    countries = (await session.execute(select(Country).order_by(Country.name))).scalars().all()
    text = "<b>📋 All Countries:</b>\n\n" + ("\n".join([f"• {c.flag_emoji} {c.name} (${float(c.price_per_account):.2f}) | Stock: {c.stock_count}" for c in countries]) if countries else "No countries found.")
    await cb.message.edit_text(text, reply_markup=build_country_management_keyboard())
    await cb.answer()

@router.callback_query(F.data == "admin_delete_country", admin_id_filter)
async def admin_delete_country_callback(cb: CallbackQuery, session: AsyncSession):
    countries = (await session.execute(select(Country).order_by(Country.name))).scalars().all()
    if not countries:
        await cb.answer("There are no countries to delete.", show_alert=True)
        return
    await cb.message.edit_text(
        "🗑️ <b>Select a country to delete</b>\n\n"
        "Please choose a country from the list below. This action will proceed to a confirmation step.",
        reply_markup=build_delete_country_keyboard(countries)
    )
    await cb.answer()

@router.callback_query(F.data.startswith("admin_delete_country_select_"), admin_id_filter)
async def admin_delete_country_select_callback(cb: CallbackQuery, session: AsyncSession):
    country_id = int(cb.data.split('_')[-1])
    country = await session.get(Country, country_id)
    if not country:
        await cb.answer("Country not found. It might have been deleted already.", show_alert=True)
        await cb.message.delete()
        return
    sold_count = await session.scalar(select(func.count(Account.id)).where(Account.country_id == country_id, Account.is_sold == True))
    unsold_count = country.stock_count
    await cb.message.edit_text(
        f"⚠️ <b>Confirm Deletion</b>\n\n"
        f"Are you absolutely sure you want to delete <b>{country.flag_emoji} {country.name}</b>?\n\n"
        f"This will permanently delete:\n"
        f"  - The country entry itself.\n"
        f"  - <code>{unsold_count}</code> unsold account(s).\n"
        f"  - <code>{sold_count}</code> sold account record(s).\n\n"
        f"<b>This action is irreversible.</b>",
        reply_markup=build_delete_country_confirmation_keyboard(country_id)
    )
    await cb.answer()

@router.callback_query(F.data.startswith("admin_delete_country_confirm_"), admin_id_filter)
async def admin_delete_country_confirm_callback(cb: CallbackQuery, session: AsyncSession):
    country_id = int(cb.data.split('_')[-1])
    country = await session.get(Country, country_id, options=[selectinload(Country.accounts)])
    if not country:
        await cb.answer("Country not found, cannot delete.", show_alert=True)
        await cb.message.edit_text("🌍 <b>Country Management</b>", reply_markup=build_country_management_keyboard())
        return
    country_name = country.name
    country_flag = country.flag_emoji
    await session.execute(delete(Account).where(Account.country_id == country_id))
    await session.delete(country)
    await session.commit()
    await cb.message.edit_text(
        f"✅ <b>Deletion Successful</b>\n\n"
        f"The country <b>{country_flag} {country.name}</b> and all its associated accounts have been removed from the database.",
        reply_markup=build_country_management_keyboard()
    )
    await cb.answer(f"{country_name} deleted successfully.", show_alert=True)

@router.message(AdminStates.add_country_name, F.text, admin_id_filter)
async def add_country_name_received(m: Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("📞 Enter phone code (e.g., +95):")
    await state.set_state(AdminStates.add_country_code)

@router.message(AdminStates.add_country_code, F.text, admin_id_filter)
async def add_country_code_received(m: Message, state: FSMContext):
    await state.update_data(code=m.text)
    await m.answer("🇮🇳 Send flag emoji (e.g., 🇲🇲):")
    await state.set_state(AdminStates.add_country_flag)

@router.message(AdminStates.add_country_flag, F.text, admin_id_filter)
async def add_country_flag_received(m: Message, state: FSMContext):
    await state.update_data(flag_emoji=m.text)
    await m.answer("💲 Enter price per account (e.g., 0.25):")
    await state.set_state(AdminStates.add_country_price)

@router.message(AdminStates.add_country_price, F.text, admin_id_filter)
async def add_country_price_received(m: Message, state: FSMContext, session: AsyncSession):
    try:
        price = float(m.text.replace(',', '.'))
        data = await state.get_data()
        new_country = Country(name=data['name'], code=data['code'], flag_emoji=data['flag_emoji'], price_per_account=price)
        session.add(new_country)
        await session.commit()
        await state.clear()
        await m.answer(f"✅ Country '<b>{data['name']}</b>' added successfully!")
        await admin_panel_handler(m, state)
    except ValueError:
        await m.answer("❌ Invalid price. Please enter a number.")
        
@router.callback_query(F.data == "admin_sync_from_folders", admin_id_filter)
async def admin_sync_from_folders_callback(cb: CallbackQuery, session: AsyncSession):
    await cb.message.edit_text("⏳ Starting full synchronization... This may take a moment.")
    await cb.answer()

    def sync_logic(all_countries, all_db_phones):
        countries_map_sync = {c.name: c for c in all_countries}
        disk_phones_sync = set()
        accounts_to_add_sync = []
        unmatched_folders_sync = set()
        added_count_sync = 0
        if not os.path.isdir(ACCOUNTS_DIR):
            os.makedirs(ACCOUNTS_DIR)
            return None, "created_dir", None, None
        for folder_name in os.listdir(ACCOUNTS_DIR):
            if folder_name.lower() == 'sold': continue
            folder_path = os.path.join(ACCOUNTS_DIR, folder_name)
            if not os.path.isdir(folder_path): continue
            country_name = get_country_name(folder_name)
            if country_name not in countries_map_sync:
                unmatched_folders_sync.add(folder_name)
                continue
            country = countries_map_sync[country_name]
            for file_name in os.listdir(folder_path):
                if file_name.lower() == 'sold' or not file_name.lower().endswith('.session'):
                    continue
                phone_number = os.path.splitext(file_name)[0]
                disk_phones_sync.add(phone_number)
                if phone_number not in all_db_phones:
                    file_path = os.path.join(folder_path, file_name)
                    try:
                        with open(file_path, 'rb') as f:
                            session_data = f.read()
                        accounts_to_add_sync.append({
                            'country_id': country.id,
                            'phone_number': phone_number,
                            'session_file': session_data
                        })
                        added_count_sync += 1
                    except Exception as e:
                        logger.error(f"Error reading file {file_path}: {e}")
        return disk_phones_sync, accounts_to_add_sync, unmatched_folders_sync, added_count_sync

    all_countries_res = await session.execute(select(Country))
    all_countries = all_countries_res.scalars().all()
    all_db_phones_res = await session.execute(select(Account.phone_number))
    all_db_phones = {phone[0] for phone in all_db_phones_res.fetchall()}

    disk_phones, accounts_to_add_data, unmatched_folders, added_count = await asyncio.to_thread(
        sync_logic, all_countries, all_db_phones
    )

    if disk_phones is None and accounts_to_add_data == "created_dir":
        await cb.message.edit_text(
            f"⚠️ Warning: Directory `{ACCOUNTS_DIR}` not found. I've created it. "
            "Please add account folders and files, then sync again.",
            reply_markup=build_account_management_keyboard()
        )
        return

    if accounts_to_add_data:
        new_accounts = [Account(**data) for data in accounts_to_add_data]
        session.add_all(new_accounts)

    db_unsold_phones_res = await session.execute(select(Account.phone_number).where(Account.is_sold == False))
    db_unsold_phones = {phone[0] for phone in db_unsold_phones_res.fetchall()}
    
    phones_to_delete = db_unsold_phones - disk_phones
    deleted_count = len(phones_to_delete)
    if phones_to_delete:
        await session.execute(delete(Account).where(Account.phone_number.in_(phones_to_delete)))

    await session.commit()

    for country in all_countries:
        count_res = await session.execute(select(func.count(Account.id)).where(Account.country_id == country.id, Account.is_sold == False))
        country.stock_count = count_res.scalar_one()
    
    await session.commit()

    report_lines = [f"✅ <b>Synchronization Complete!</b>", f"  - New Accounts Added: {added_count}", f"  - Stale Accounts Removed: {deleted_count}"]
    if unmatched_folders:
        report_lines.append("\n⚠️ <b>Unmatched Folders:</b>")
        report_lines.append("These folders do not have a matching country in the database. Please add them via 'Country Management'.")
        report_lines.extend([f"  - <code>{f}</code>" for f in unmatched_folders])
    
    await cb.message.edit_text("\n".join(report_lines), reply_markup=build_account_management_keyboard())

# --- Deposit Channel Handler ---
@router.callback_query(F.message.chat.id == config.admin_channel_id)
async def channel_deposit_callbacks(cb: CallbackQuery, session: AsyncSession, bot: Bot):
    dep_id = int(cb.data.split("_")[-1])
    is_approve = cb.data.startswith("deposit_approve_")
    dep = await session.get(Deposit, dep_id)
    if not dep or dep.status != 'pending':
        await cb.answer("❌ Already processed.", True)
        return

    user = await session.get(User, dep.user_id)
    feedback, failed = "", False
    if is_approve:
        user.balance = Decimal(str(float(user.balance or 0.0) + float(dep.amount)))
        dep.status, status, icon = 'approved', "APPROVED", "✅"
        notify_text = f"🎉 <b>Deposit Approved!</b>\n<b>${float(dep.amount):.2f}</b> added to your balance."
        feedback = f"Deposit #{dep.id} approved."
    else:
        dep.status, status, icon = 'rejected', "REJECTED", "❌"
        notify_text = "❗️ <b>Deposit Rejected</b>"
        feedback = f"Deposit #{dep.id} rejected."
    
    await session.commit()
    
    try:
        await bot.send_message(user.user_id, notify_text)
    except Exception as e:
        failed = True
        print(f"CRITICAL: Could not notify {user.user_id}. {e}")
        feedback += " ⚠️ User notification FAILED."
        
    try:
        caption = f"<b>{icon} DEPOSIT #{dep.id} {status}</b>\n\n- User: @{user.username or user.user_id}\n- Amount: ${float(dep.amount):.2f}\n- Action by: {cb.from_user.full_name}"
        if failed:
            caption += "\n\n<b>⚠️ User could not be notified!</b>"
        await cb.message.edit_caption(caption=caption, reply_markup=None)
    except Exception as e:
        print(f"Error channel edit: {e}")
        
    await cb.answer(feedback, show_alert=failed)