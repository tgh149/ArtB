from typing import List, Dict
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardButton, KeyboardButton

from utils.localization import translator

def build_main_menu_keyboard(lang: str):
    b = ReplyKeyboardBuilder()
    b.row(KeyboardButton(text=translator.get_string("btn_check_stock", lang)))
    b.row(
        KeyboardButton(text=translator.get_string("btn_add_funds", lang)),
        KeyboardButton(text=translator.get_string("btn_my_account", lang))
    )
    b.row(
        KeyboardButton(text=translator.get_string("btn_help_faq", lang)),
        KeyboardButton(text=translator.get_string("btn_contact_support", lang))
    )
    b.row(KeyboardButton(text=translator.get_string("btn_settings", lang)))
    return b.as_markup(resize_keyboard=True)


def build_settings_keyboard(lang: str):
    b = InlineKeyboardBuilder()

    # --- THIS IS THE DEFINITIVE FIX ---
    # We will now handle English separately to guarantee it works,
    # while letting the working translator handle other languages.
    if lang == 'en':
        lang_text = "🌐 Select Language"
        currency_text = "💵 Select Currency"
    else:
        lang_text = f"🌐 {translator.get_string('select_language', lang)}"
        currency_text = f"💵 {translator.get_string('select_currency', lang)}"

    b.row(
        InlineKeyboardButton(text=lang_text, callback_data="settings_language"),
        InlineKeyboardButton(text=currency_text, callback_data="settings_currency")
    )
    b.row(InlineKeyboardButton(text="◀️ Back", callback_data="main_menu_start"))
    return b.as_markup()

def build_language_selection_keyboard():
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru"),
        InlineKeyboardButton(text="🇨🇳 中文", callback_data="set_lang_zh")
    )
    b.row(InlineKeyboardButton(text="◀️ Back", callback_data="open_settings"))
    return b.as_markup()

def build_currency_selection_keyboard():
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🇺🇸 USD ($)", callback_data="set_currency_USD"),
        InlineKeyboardButton(text="🇷🇺 RUB (₽)", callback_data="set_currency_RUB"),
        InlineKeyboardButton(text="🇨🇳 CNY (¥)", callback_data="set_currency_CNY")
    )
    b.row(InlineKeyboardButton(text="◀️ Back", callback_data="open_settings"))
    return b.as_markup()

def build_profile_keyboard():
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="💰 Top Up Balance", callback_data="add_funds_from_profile"),
        InlineKeyboardButton(text="💸 Withdraw Funds", callback_data="withdraw_funds")
    )
    b.row(InlineKeyboardButton(text="🗂️ My Accounts", callback_data="my_purchased_accounts"))
    return b.as_markup()


# --- Other keyboards ---
def build_subscription_keyboard(channels: List[str]):
    b = InlineKeyboardBuilder()
    [b.row(InlineKeyboardButton(text=f"🚀 Join {c.lstrip('@')}", url=f"https://t.me/{c.lstrip('@')}")) for c in channels]
    b.row(InlineKeyboardButton(text="🙌 I've Joined", callback_data="check_subscription"))
    return b.as_markup()

def build_payment_methods_keyboard(details: Dict):
    b = InlineKeyboardBuilder()
    methods = list(details.keys())
    for i in range(0, len(methods), 2):
        row = [InlineKeyboardButton(text=details[methods[i]]['name'], callback_data=f"deposit_{methods[i]}")]
        if i + 1 < len(methods):
            row.append(InlineKeyboardButton(text=details[methods[i+1]]['name'], callback_data=f"deposit_{methods[i+1]}"))
        b.row(*row)
    b.row(InlineKeyboardButton(text="◀️ Back", callback_data="main_menu_start"))
    return b.as_markup()

def build_deposit_confirmation_keyboard(key: str):
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="✅ Done", callback_data=f"deposit_done_{key}"), InlineKeyboardButton(text="❌ Cancel", callback_data="global_cancel"))
    return b.as_markup()

def build_crypto_bot_invoice_keyboard(pay_url: str, deposit_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="▶️ Pay Now", url=pay_url))
    builder.row(InlineKeyboardButton(text="✅ I Have Paid", callback_data=f"check_payment_{deposit_id}"))
    builder.row(InlineKeyboardButton(text="❌ Cancel", callback_data="global_cancel"))
    return builder.as_markup()