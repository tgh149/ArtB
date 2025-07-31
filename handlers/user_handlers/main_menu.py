import logging
import os
from aiogram import Router, F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from decimal import Decimal

from config_data.config import config
from database.models import *
from keyboards.user_keyboards import *
from keyboards.purchase_keyboards import *
from keyboards.admin_keyboards import build_deposit_management_keyboard
from utils.payment_texts import *
from utils.payment_texts import get_deposit_instructions
from utils.states import DepositStates, BrowsingStates, WithdrawalStates
from utils.crypto_bot_api import CryptoBotAPI
from utils.localization import translator
from utils.currency_converter import currency_converter
from utils.stock_manager import ACCOUNTS_DIR, get_live_stock

logger = logging.getLogger(__name__)

router = Router()
router.callback_query.filter(F.message.chat.type == "private")

# --- Enhanced Stock Management ---
def get_folder_structure():
    """Get hierarchical folder structure with stock counts"""
    if not os.path.exists(ACCOUNTS_DIR):
        os.makedirs(ACCOUNTS_DIR)
        return {}

    folder_info = {}
    try:
        for folder_name in os.listdir(ACCOUNTS_DIR):
            folder_path = os.path.join(ACCOUNTS_DIR, folder_name)
            if os.path.isdir(folder_path):
                session_files = [f for f in os.listdir(folder_path) 
                               if f.endswith('.session') and not f.startswith('sold')]
                if session_files:
                    folder_info[folder_name] = len(session_files)
    except Exception as e:
        logger.error(f"Error scanning folders: {e}")

    return folder_info

def get_products_in_folder(folder_name: str):
    """Get list of available products in a specific folder"""
    folder_path = os.path.join(ACCOUNTS_DIR, folder_name)
    if not os.path.exists(folder_path):
        return []

    try:
        return [f for f in os.listdir(folder_path) 
                if f.endswith('.session') and not f.startswith('sold')]
    except Exception:
        return []

# --- Handler Functions ---
async def add_funds_handler(message: Message, user: User, state: FSMContext, **kwargs):
    logger.info(f"User {user.user_id} (@{user.username}) -> Add Funds")
    await state.set_state(DepositStates.select_deposit_amount)
    await state.update_data(deposit_amount=1.0)

    text = (f"💰 <b>Top Up Balance</b>\n\n"
            f"Title: Top Up\n"
            f"Description: Add funds to your account\n"
            f"Price: 1 USD\n"
            f"Top Up: 1\n\n"
            f"Use +/- buttons to adjust amount")

    await message.answer(text, reply_markup=build_deposit_amount_keyboard(1.0))

async def check_stock_handler(message: Message, session: AsyncSession, user: User, state: FSMContext, **kwargs):
    logger.info(f"User {user.user_id} (@{user.username}) -> Browse Products")

    folder_info = get_folder_structure()

    if not folder_info:
        return await message.answer("📦 <b>No products available</b>\n\nOur store is currently restocking. Please check back later!")

    await state.set_state(BrowsingStates.viewing_categories)

    text = (f"🛍️ <b>Product Categories</b>\n\n"
            f"The following are product categories:\n\n"
            f"If you have not used our products, please buy a small amount for testing first to avoid unnecessary disputes!")

    await message.answer(text, reply_markup=build_categories_keyboard(folder_info))

async def my_account_handler(message: Message, session: AsyncSession, user: User, **kwargs):
    logger.info(f"User {user.user_id} (@{user.username}) -> My Account")
    sold_accounts_count = await session.scalar(select(func.count(Account.id)).where(Account.buyer_id == user.user_id))
    formatted_balance = await currency_converter.format_currency(Decimal(str(user.balance)), user.currency)
    text = translator.get_string(
        "profile_title",
        user.language_code,
        user_id=user.user_id,
        balance=formatted_balance,
        purchase_count=sold_accounts_count,
        reg_date=user.registration_date.strftime('%Y-%m-%d')
    )
    await message.answer(text, reply_markup=build_profile_keyboard())

async def support_handler(message: Message, user: User, **kwargs):
    logger.info(f"User {user.user_id} (@{user.username}) -> Contact Support")
    text = translator.get_string("support_message", user.language_code, support_contact=config.support_contact)
    await message.answer(text)

async def help_handler(message: Message, user: User, **kwargs):
    logger.info(f"User {user.user_id} (@{user.username}) -> Help & FAQ")
    lang = user.language_code
    text = translator.get_string(
        "help_message",
        lang,
        add_funds_btn=translator.get_string('btn_add_funds', lang),
        buy_accounts_btn=translator.get_string('btn_check_stock', lang)
    )
    await message.answer(text)

async def settings_handler(message: Message, user: User, **kwargs):
    logger.info(f"User {user.user_id} (@{user.username}) -> Settings")
    text = translator.get_string("settings_title", user.language_code)
    await message.answer(text, reply_markup=build_settings_keyboard(user.language_code))

# --- Central Text Router ---
@router.message(F.text)
async def main_menu_text_router(message: Message, session: AsyncSession, user: User, state: FSMContext, bot: Bot):
    lang = user.language_code
    text = message.text

    button_to_handler_map = {
        translator.get_string("btn_check_stock", lang): check_stock_handler,
        translator.get_string("btn_add_funds", lang): add_funds_handler,
        translator.get_string("btn_my_account", lang): my_account_handler,
        translator.get_string("btn_help_faq", lang): help_handler,
        translator.get_string("btn_contact_support", lang): support_handler,
        translator.get_string("btn_settings", lang): settings_handler,
    }

    handler_func = button_to_handler_map.get(text)

    if handler_func:
        # Silent cancel - clear any existing state when user clicks main menu buttons
        current_state = await state.get_state()
        if current_state is not None:
            await state.clear()
            logger.info(f"User {user.user_id} silently cancelled state {current_state}")

        await handler_func(message=message, session=session, user=user, state=state, bot=bot)
    else:
        logger.warning(f"User {user.user_id} sent unhandled text: '{text}'")

# --- Browse Products Callbacks ---
@router.callback_query(F.data.startswith("browse_category_"))
async def browse_category_handler(cb: CallbackQuery, state: FSMContext, user: User):
    folder_name = cb.data.replace("browse_category_", "")
    products = get_products_in_folder(folder_name)

    if not products:
        await cb.answer("❌ No products available in this category", show_alert=True)
        return

    await state.set_state(BrowsingStates.viewing_products)
    await state.update_data(current_folder=folder_name, product_list=products)

    # Extract country info for pricing (default $1.50)
    price_per_item = 1.5

    display_name = folder_name.replace('+', '').replace('_', ' ').title()
    text = (f"📱 <b>{display_name}</b>\n\n"
            f"The following is a list of products:\n\n"
            f"Select a product to configure your purchase:")

    await cb.message.edit_text(text, reply_markup=build_products_keyboard(folder_name, products, price_per_item))
    await cb.answer()

@router.callback_query(F.data.startswith("select_product_"))
async def select_product_handler(cb: CallbackQuery, state: FSMContext, user: User):
    parts = cb.data.replace("select_product_", "").split("_")
    folder_name = parts[0]
    product_idx = int(parts[1])

    data = await state.get_data()
    product_list = data.get('product_list', [])
    
    if product_idx >= len(product_list):
        await cb.answer("❌ Product not found", show_alert=True)
        return

    product_name = product_list[product_idx]

    await state.set_state(BrowsingStates.configuring_purchase)
    await state.update_data(
        current_folder=folder_name,
        current_product_idx=product_idx,
        current_product=product_name,
        quantity=1
    )

    # Get product details
    price_per_item = 1.5
    max_stock = len(get_products_in_folder(folder_name))

    display_name = folder_name.replace('+', '').replace('_', ' ').title()
    clean_product = product_name.replace('.session', '').replace('_', ' ')

    text = (f"🛒 <b>Title:</b> {display_name}\n"
            f"<b>Description:</b> Premium account\n"
            f"<b>Price:</b> {price_per_item} USD\n"
            f"<b>In Stock:</b> {max_stock}\n"
            f"<b>Buy Num:</b> 1\n"
            f"<b>Payment amount:</b> {price_per_item} USD\n\n"
            f"Use +/- to adjust quantity")

    await cb.message.edit_text(text, reply_markup=build_quantity_selector_keyboard(
        folder_name, product_idx, 1, max_stock, price_per_item, float(user.balance)
    ))
    await cb.answer()

# --- Quantity Management ---
@router.callback_query(F.data.startswith("qty_plus_"))
async def quantity_plus_handler(cb: CallbackQuery, state: FSMContext, user: User):
    parts = cb.data.replace("qty_plus_", "").split("_")
    folder_name = parts[0]
    product_idx = int(parts[1])
    current_qty = int(parts[2])

    max_stock = len(get_products_in_folder(folder_name))
    new_qty = min(current_qty + 1, max_stock)

    await state.update_data(quantity=new_qty)

    price_per_item = 1.5
    total_cost = new_qty * price_per_item

    display_name = folder_name.replace('+', '').replace('_', ' ').title()

    text = (f"🛒 <b>Title:</b> {display_name}\n"
            f"<b>Description:</b> Premium account\n"
            f"<b>Price:</b> {price_per_item} USD\n"
            f"<b>In Stock:</b> {max_stock}\n"
            f"<b>Buy Num:</b> {new_qty}\n"
            f"<b>Payment amount:</b> {total_cost} USD\n\n"
            f"Use +/- to adjust quantity")

    await cb.message.edit_text(text, reply_markup=build_quantity_selector_keyboard(
        folder_name, product_idx, new_qty, max_stock, price_per_item, float(user.balance)
    ))
    await cb.answer()

@router.callback_query(F.data.startswith("qty_minus_"))
async def quantity_minus_handler(cb: CallbackQuery, state: FSMContext, user: User):
    parts = cb.data.replace("qty_minus_", "").split("_")
    folder_name = parts[0]
    product_idx = int(parts[1])
    current_qty = int(parts[2])

    new_qty = max(current_qty - 1, 1)

    await state.update_data(quantity=new_qty)

    price_per_item = 1.5
    total_cost = new_qty * price_per_item
    max_stock = len(get_products_in_folder(folder_name))

    display_name = folder_name.replace('+', '').replace('_', ' ').title()

    text = (f"🛒 <b>Title:</b> {display_name}\n"
            f"<b>Description:</b> Premium account\n"
            f"<b>Price:</b> {price_per_item} USD\n"
            f"<b>In Stock:</b> {max_stock}\n"
            f"<b>Buy Num:</b> {new_qty}\n"
            f"<b>Payment amount:</b> {total_cost} USD\n\n"
            f"Use +/- to adjust quantity")

    await cb.message.edit_text(text, reply_markup=build_quantity_selector_keyboard(
        folder_name, product_idx, new_qty, max_stock, price_per_item, float(user.balance)
    ))
    await cb.answer()

@router.callback_query(F.data == "insufficient_balance")
async def insufficient_balance_handler(cb: CallbackQuery, user: User):
    balance = float(user.balance)
    await cb.answer(f"💰 Insufficient balance. Your balance: ${balance:.2f}", show_alert=True)

# --- Navigation Callbacks ---
@router.callback_query(F.data == "back_to_categories")
async def back_to_categories_handler(cb: CallbackQuery, state: FSMContext, user: User):
    folder_info = get_folder_structure()
    await state.set_state(BrowsingStates.viewing_categories)

    text = (f"🛍️ <b>Product Categories</b>\n\n"
            f"The following are product categories:\n\n"
            f"If you have not used our products, please buy a small amount for testing first to avoid unnecessary disputes!")

    await cb.message.edit_text(text, reply_markup=build_categories_keyboard(folder_info))
    await cb.answer()

@router.callback_query(F.data.startswith("back_to_products_"))
async def back_to_products_handler(cb: CallbackQuery, state: FSMContext, user: User):
    folder_name = cb.data.replace("back_to_products_", "")
    products = get_products_in_folder(folder_name)

    await state.set_state(BrowsingStates.viewing_products)

    display_name = folder_name.replace('+', '').replace('_', ' ').title()
    text = (f"📱 <b>{display_name}</b>\n\n"
            f"The following is a list of products:\n\n"
            f"Select a product to configure your purchase:")

    await cb.message.edit_text(text, reply_markup=build_products_keyboard(folder_name, products, 1.5))
    await cb.answer()

# --- Deposit Amount Handlers ---
@router.callback_query(F.data.startswith("deposit_plus_"))
async def deposit_plus_handler(cb: CallbackQuery, state: FSMContext, user: User):
    current_amount = float(cb.data.replace("deposit_plus_", ""))
    new_amount = current_amount + 1

    await state.update_data(deposit_amount=new_amount)

    text = (f"💰 <b>Top Up Balance</b>\n\n"
            f"Title: Top Up\n"
            f"Description: Add funds to your account\n"
            f"Price: 1 USD\n"
            f"Top Up: {new_amount:.0f}\n\n"
            f"Use +/- buttons to adjust amount")

    await cb.message.edit_text(text, reply_markup=build_deposit_amount_keyboard(new_amount))
    await cb.answer()

@router.callback_query(F.data.startswith("deposit_minus_"))
async def deposit_minus_handler(cb: CallbackQuery, state: FSMContext, user: User):
    current_amount = float(cb.data.replace("deposit_minus_", ""))
    new_amount = max(current_amount - 1, 1)

    # Only update if amount actually changed to avoid Telegram error
    if new_amount != current_amount:
        await state.update_data(deposit_amount=new_amount)

        text = (f"💰 <b>Top Up Balance</b>\n\n"
                f"Title: Top Up\n"
                f"Description: Add funds to your account\n"
                f"Price: 1 USD\n"
                f"Top Up: {new_amount:.0f}\n\n"
                f"Use +/- buttons to adjust amount")

        await cb.message.edit_text(text, reply_markup=build_deposit_amount_keyboard(new_amount))

    await cb.answer()

@router.callback_query(F.data.startswith("deposit_checkout_"))
async def deposit_checkout_handler(cb: CallbackQuery, state: FSMContext, user: User):
    amount = float(cb.data.replace("deposit_checkout_", ""))
    await state.update_data(deposit_amount=amount)

    text = (f"💰 <b>Top Up Balance</b>\n\n"
            f"Title: Top Up\n"
            f"Description: Add funds to your account\n"
            f"Price: 1 USD\n"
            f"Top Up: {amount:.0f}\n\n"
            f"Please select a payment method to create your order")

    await cb.message.edit_text(text, reply_markup=build_payment_methods_keyboard(PAYMENT_DETAILS))
    await cb.answer()

# --- Keep existing callback handlers ---
@router.callback_query(F.data == "profile_menu")
async def profile_menu_callback(cb: CallbackQuery, session: AsyncSession, user: User):
    await cb.message.delete()
    await my_account_handler(message=cb.message, session=session, user=user)
    await cb.answer()

@router.callback_query(F.data == "open_settings")
async def open_settings_callback(cb: CallbackQuery, user: User):
    logger.info(f"User {user.user_id} (@{user.username}) opened settings via callback.")
    text = translator.get_string("settings_title", user.language_code)
    await cb.message.edit_text(text, reply_markup=build_settings_keyboard(user.language_code))
    await cb.answer()

@router.callback_query(F.data == "settings_language")
async def settings_language_callback(cb: CallbackQuery, user: User):
    logger.info(f"User {user.user_id} (@{user.username}) -> Settings -> Language")
    text = translator.get_string("select_language", user.language_code)
    await cb.message.edit_text(text, reply_markup=build_language_selection_keyboard())
    await cb.answer()

@router.callback_query(F.data.startswith("set_lang_"))
async def set_language_callback(cb: CallbackQuery, session: AsyncSession, user: User):
    lang_code = cb.data.split('_')[-1]
    user.language_code = lang_code
    await session.commit()
    logger.info(f"User {user.user_id} (@{user.username}) set language to: {lang_code}")
    await cb.answer(translator.get_string("lang_set", lang_code), show_alert=True)
    text = translator.get_string("settings_title", user.language_code)
    await cb.message.edit_text(text, reply_markup=build_settings_keyboard(user.language_code))

@router.callback_query(F.data == "settings_currency")
async def settings_currency_callback(cb: CallbackQuery, user: User):
    logger.info(f"User {user.user_id} (@{user.username}) -> Settings -> Currency")
    text = translator.get_string("select_currency", user.language_code)
    await cb.message.edit_text(text, reply_markup=build_currency_selection_keyboard())
    await cb.answer()

@router.callback_query(F.data.startswith("set_currency_"))
async def set_currency_callback(cb: CallbackQuery, session: AsyncSession, user: User):
    currency_code = cb.data.split('_')[-1]
    user.currency = currency_code
    await session.commit()
    logger.info(f"User {user.user_id} (@{user.username}) set currency to: {currency_code}")
    await cb.answer(translator.get_string("currency_set", user.language_code, currency=currency_code), show_alert=True)
    text = translator.get_string("settings_title", user.language_code)
    await cb.message.edit_text(text, reply_markup=build_settings_keyboard(user.language_code))

@router.callback_query(F.data == "main_menu_start")
async def back_to_main_menu_handler(cb: CallbackQuery, user: User, state: FSMContext):
    logger.info(f"User {user.user_id} (@{user.username}) returned to main menu.")
    await state.clear()
    try: await cb.message.delete()
    except: pass
    await cb.message.answer(translator.get_string("back_to_main", user.language_code), reply_markup=build_main_menu_keyboard(user.language_code))
    await cb.answer()

@router.callback_query(F.data == "add_funds_from_profile")
async def add_funds_from_profile_handler(cb: CallbackQuery, user: User, state: FSMContext, **kwargs):
    await cb.message.delete()
    await add_funds_handler(message=cb.message, user=user, state=state)
    await cb.answer()

@router.callback_query(F.data == "withdraw_funds")
async def withdraw_funds_handler(cb: CallbackQuery, state: FSMContext, user: User):
    logger.info(f"User {user.user_id} (@{user.username}) started withdrawal process")
    await state.set_state(WithdrawalStates.waiting_for_amount)
    
    lang = user.language_code
    balance_text = translator.get_string("current_balance", lang, balance=f"${float(user.balance):.2f}")
    withdraw_prompt = translator.get_string("enter_withdraw_amount", lang)
    
    text = f"{balance_text}\n\n{withdraw_prompt}"
    await cb.message.edit_text(text)
    await cb.answer()

@router.callback_query(F.data == "my_purchased_accounts")
async def my_purchased_accounts_handler(cb: CallbackQuery, user: User):
    logger.info(f"User {user.user_id} (@{user.username}) clicked 'My Accounts'")
    text = translator.get_string("my_accounts_info", user.language_code)
    await cb.answer(text, show_alert=True)

# --- Deposit Flow (keep existing) ---
crypto_bot = CryptoBotAPI(token=config.crypto_bot_token.get_secret_value())

@router.callback_query(F.data.startswith("deposit_") & ~F.data.startswith("deposit_done_") & ~F.data.startswith("deposit_plus_") & ~F.data.startswith("deposit_minus_") & ~F.data.startswith("deposit_checkout_"))
async def select_payment_method_handler(cb: CallbackQuery, state: FSMContext, user: User):
    method_key = cb.data.split("_", 1)[1]
    logger.info(f"User {user.user_id} (@{user.username}) selected deposit method: {method_key}")

    if method_key == "crypto_bot":
        data = await state.get_data()
        amount = data.get('deposit_amount', 1.0)
        await cb.message.edit_text(f"💰 <b>Crypto Bot Payment</b>\n\nAmount: ${amount:.2f} USDT")
        await state.set_state(DepositStates.waiting_for_crypto_amount)
        await cb.answer()
        return

    # For manual methods, first ask for amount
    await state.update_data(payment_method=method_key)
    await state.set_state(DepositStates.waiting_for_amount)
    
    lang = user.language_code
    text = translator.get_string("enter_deposit_amount", lang)
    await cb.message.edit_text(text)
    await cb.answer()

@router.message(DepositStates.waiting_for_crypto_amount, F.text)
async def process_crypto_amount(msg: Message, state: FSMContext, session: AsyncSession, user: User):
    data = await state.get_data()
    amount = data.get('deposit_amount', 1.0)

    logger.info(f"User {user.user_id} creating CryptoBot invoice for ${amount:.2f}")
    await msg.answer("⏳ Creating your invoice, please wait...")

    invoice = await crypto_bot.create_invoice(amount=amount, asset="USDT")

    if not invoice or "invoice_id" not in invoice:
        logger.error(f"Failed to create CryptoBot invoice for user {user.user_id}")
        await msg.answer("❗️ Sorry, I couldn't create a payment invoice. Please try again later or contact support.")
        await state.clear()
        return

    invoice_id = invoice['invoice_id']
    pay_url = invoice['pay_url']

    new_deposit = Deposit(
        user_id=msg.from_user.id,
        amount=amount,
        payment_method="Crypto Bot",
        status="waiting",
        invoice_id=invoice_id
    )
    session.add(new_deposit)
    await session.commit()

    text = (f"✅ Your invoice has been created for <b>${amount:.2f} USDT</b>.\n\n"
            f"1️⃣ Click '▶️ Pay Now' to open the payment page.\n"
            f"2️⃣ After you complete the payment, click '✅ I Have Paid' below.")

    await msg.answer(text, reply_markup=build_crypto_bot_invoice_keyboard(pay_url, new_deposit.id))
    await state.clear()

@router.callback_query(F.data.startswith("check_payment_"))
async def check_crypto_payment_handler(cb: CallbackQuery, session: AsyncSession, bot: Bot):
    deposit_id = int(cb.data.split('_')[-1])

    deposit = await session.get(Deposit, deposit_id)
    if not deposit or deposit.status != 'waiting':
        await cb.answer("❗️ This payment has already been processed or cancelled.", show_alert=True)
        return

    logger.info(f"User {deposit.user_id} checking CryptoBot payment for deposit #{deposit_id}")
    await cb.answer("Checking payment status...", show_alert=False)

    invoices = await crypto_bot.get_invoices(invoice_ids=str(deposit.invoice_id))

    if not invoices or not isinstance(invoices, list) or not invoices:
        await cb.message.edit_text("Could not verify payment status. Please try again in a minute.")
        return

    invoice_status = invoices[0].get('status')

    if invoice_status == 'paid':
        user = await session.get(User, deposit.user_id)
        user.balance = Decimal(str(user.balance)) + Decimal(str(deposit.amount))
        deposit.status = 'approved'
        await session.commit()

        logger.info(f"CryptoBot payment for deposit #{deposit.id} CONFIRMED. User {user.user_id} balance updated.")
        await cb.message.edit_text(f"✅ <b>Payment Confirmed!</b>\n\n${deposit.amount:.2f} has been added to your balance.")

        user_mention = f"@{user.username}" if user.username else f"<code>{user.first_name}</code> (ID: <code>{user.user_id}</code>)"
        caption = (f"✅ <b>Crypto Bot Deposit Approved</b>\n\n"
                   f"👤 <b>User:</b> {user_mention}\n"
                   f"💵 <b>Amount:</b> ${float(deposit.amount):.2f}\n"
                   f"🆔 Invoice ID: <code>{deposit.invoice_id}</code>")
        try:
            await bot.send_message(chat_id=config.admin_channel_id, text=caption)
        except Exception as e:
            logger.error(f"Error sending to admin channel: {e}")

    elif invoice_status == 'expired':
        deposit.status = 'rejected'
        await session.commit()
        logger.warning(f"CryptoBot invoice for deposit #{deposit.id} expired.")
        await cb.message.edit_text("❌ This payment invoice has expired and was cancelled.")
    else:
        await cb.answer("⏳ Payment not confirmed yet. Please wait a moment and try again.", show_alert=True)

@router.callback_query(F.data.startswith("deposit_done_"))
async def deposit_done_handler(cb: CallbackQuery, state: FSMContext, user: User):
    method_key = cb.data.split('_')[-1]
    logger.info(f"User {user.user_id} confirmed payment instructions for method {method_key}")
    
    # Now ask for screenshot proof
    await state.set_state(DepositStates.waiting_for_screenshot)
    
    lang = user.language_code
    text = translator.get_string("screenshot_required_error", lang)
    await cb.message.edit_text("✅ <b>Payment Instructions Confirmed</b>\n\n📸 Please upload a screenshot of your payment as proof.\n\n⚠️ Only photo/image files are accepted.")
    await cb.answer()

@router.message(DepositStates.waiting_for_amount, F.text)
async def process_deposit_amount(msg: Message, state: FSMContext, user: User):
    try:
        amount = float(msg.text.replace(',', '.').strip())
        if amount < 1.0:
            lang = user.language_code
            error_text = translator.get_string("min_deposit_error", lang)
            await msg.answer(error_text)
            return
    except ValueError:
        lang = user.language_code
        error_text = translator.get_string("invalid_amount_error", lang)
        await msg.answer(error_text)
        return

    await state.update_data(deposit_amount=amount)
    data = await state.get_data()
    method_key = data.get('payment_method', 'manual')

    logger.info(f"User {user.user_id} entered manual deposit amount: ${amount:.2f}")

    # Show payment instructions with Done button
    instructions = get_deposit_instructions(method_key, user.language_code)
    amount_text = translator.get_string("deposit_amount_confirmed", user.language_code, amount=f"${amount:.2f}")
    
    await msg.answer(f"{instructions}\n\n{amount_text}", reply_markup=build_deposit_confirmation_keyboard(method_key))
    await state.set_state(DepositStates.waiting_for_done_confirmation)

@router.message(DepositStates.waiting_for_screenshot, F.photo)
async def process_screenshot_handler(msg: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    dep = Deposit(user_id=msg.from_user.id, amount=data.get("deposit_amount", 0.0), payment_method=PAYMENT_DETAILS.get(data.get("payment_method"), {}).get("name", "N/A"), status='pending', screenshot_file_id=msg.photo[-1].file_id)
    session.add(dep); await session.commit(); await session.refresh(dep)

    user = await session.get(User, msg.from_user.id)
    logger.info(f"User {user.user_id} submitted manual deposit request #{dep.id} for ${dep.amount:.2f}")
    user_mention = f"@{user.username}" if user.username else f"<code>{user.first_name}</code> (ID: <code>{user.user_id}</code>)"
    caption = f"<b>⚠️ New Deposit Request #{dep.id}</b>\n\n👤 <b>User:</b> {user_mention}\n💵 <b>Amount Claimed:</b> ${dep.amount:.2f}\n💳 <b>Method:</b> {dep.payment_method}"

    try:
        admin_msg = await bot.send_photo(chat_id=config.admin_channel_id, photo=msg.photo[-1].file_id, caption=caption, reply_markup=build_deposit_management_keyboard(dep.id))
        dep.admin_channel_message_id = admin_msg.message_id
        await session.commit()
    except Exception as e: 
        logger.error(f"Error sending to admin channel: {e}")

    await msg.answer("✅ <b>Request Submitted!</b>"); await state.clear()

@router.message(DepositStates.waiting_for_screenshot)
async def process_invalid_screenshot_handler(msg: Message, user: User):
    lang = user.language_code
    error_text = translator.get_string("screenshot_required_error", lang)
    await msg.answer(error_text)

@router.message(WithdrawalStates.waiting_for_amount, F.text)
async def process_withdrawal_amount(msg: Message, state: FSMContext, user: User):
    try:
        amount = float(msg.text.replace(',', '.').strip())
        if amount < 1.0:
            lang = user.language_code
            error_text = translator.get_string("min_withdraw_error", lang)
            await msg.answer(error_text)
            return
        if amount > float(user.balance):
            lang = user.language_code
            error_text = translator.get_string("insufficient_balance_withdraw", lang, 
                                              balance=f"${float(user.balance):.2f}", 
                                              requested=f"${amount:.2f}")
            await msg.answer(error_text)
            return
    except ValueError:
        lang = user.language_code
        error_text = translator.get_string("invalid_amount_error", lang)
        await msg.answer(error_text)
        return

    await state.update_data(withdraw_amount=amount)
    await state.set_state(WithdrawalStates.waiting_for_address)
    
    lang = user.language_code
    binance_prompt = translator.get_string("enter_binance_id", lang, amount=f"${amount:.2f}")
    await msg.answer(binance_prompt)

@router.message(WithdrawalStates.waiting_for_address, F.text)
async def process_withdrawal_address(msg: Message, state: FSMContext, session: AsyncSession, user: User, bot: Bot):
    data = await state.get_data()
    amount = data.get('withdraw_amount')
    binance_id = msg.text.strip()
    
    # Create withdrawal request
    withdrawal = Withdrawal(
        user_id=msg.from_user.id,
        amount=amount,
        binance_id=binance_id,
        status='pending'
    )
    session.add(withdrawal)
    await session.commit()
    await session.refresh(withdrawal)
    
    logger.info(f"User {user.user_id} submitted withdrawal request #{withdrawal.id} for ${amount:.2f}")
    
    # Send to admin channel
    user_mention = f"@{user.username}" if user.username else f"<code>{user.first_name}</code> (ID: <code>{user.user_id}</code>)"
    lang = user.language_code
    
    admin_caption = (f"💸 <b>New Withdrawal Request #{withdrawal.id}</b>\n\n"
                    f"👤 <b>User:</b> {user_mention}\n"
                    f"💰 <b>Amount:</b> ${withdrawal.amount:.2f}\n"
                    f"🏦 <b>Binance ID:</b> <code>{withdrawal.binance_id}</code>\n"
                    f"💳 <b>User Balance:</b> ${float(user.balance):.2f}")
    
    try:
        from keyboards.admin_keyboards import build_withdrawal_management_keyboard
        admin_msg = await bot.send_message(
            chat_id=config.admin_channel_id, 
            text=admin_caption, 
            reply_markup=build_withdrawal_management_keyboard(withdrawal.id)
        )
        withdrawal.admin_channel_message_id = admin_msg.message_id
        await session.commit()
    except Exception as e:
        logger.error(f"Error sending withdrawal to admin channel: {e}")
    
    # Confirm to user
    confirmation_text = translator.get_string("withdrawal_submitted", lang)
    await msg.answer(confirmation_text)
    await state.clear()

