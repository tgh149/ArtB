from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from database.models import Country, User

def build_admin_panel_keyboard():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📊 Bot Statistics", callback_data="admin_stats"), InlineKeyboardButton(text="💰 View Deposits", callback_data="admin_view_deposits"))
    b.row(InlineKeyboardButton(text="👤 User Management", callback_data="admin_user_management"), InlineKeyboardButton(text="🌍 Country Management", callback_data="admin_country_management"))
    b.row(InlineKeyboardButton(text="📦 Account Management", callback_data="admin_account_management"), InlineKeyboardButton(text="💬 Messaging", callback_data="admin_messaging"))
    return b.as_markup()

def build_deposit_management_keyboard(deposit_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Approve", callback_data=f"admin_approve_deposit_{deposit_id}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"admin_reject_deposit_{deposit_id}")
    )
    return builder.as_markup()

def build_withdrawal_management_keyboard(withdrawal_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Approve Withdrawal", callback_data=f"admin_approve_withdrawal_{withdrawal_id}"),
        InlineKeyboardButton(text="❌ Reject Withdrawal", callback_data=f"admin_reject_withdrawal_{withdrawal_id}")
    )
    return builder.as_markup()

def build_country_management_keyboard():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="➕ Add Country", callback_data="admin_add_country"))
    b.row(InlineKeyboardButton(text="🗑️ Delete Country", callback_data="admin_delete_country"))
    b.row(InlineKeyboardButton(text="📋 View Countries", callback_data="admin_view_countries"))
    b.row(InlineKeyboardButton(text="⬅️ Back to Admin Panel", callback_data="admin_panel"))
    return b.as_markup()

def build_account_management_keyboard():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🔄 Sync Accounts from Folders", callback_data="admin_sync_from_folders"))
    b.row(InlineKeyboardButton(text="⬅️ Back to Admin Panel", callback_data="admin_panel"))
    return b.as_markup()

def build_delete_country_keyboard(countries: list[Country]):
    b = InlineKeyboardBuilder()
    for c in countries:
        b.row(InlineKeyboardButton(text=f"{c.flag_emoji} {c.name}", callback_data=f"admin_delete_country_select_{c.id}"))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="admin_country_management"))
    return b.as_markup()

def build_delete_country_confirmation_keyboard(country_id: int):
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="✅ Yes, I am sure. Delete it.", callback_data=f"admin_delete_country_confirm_{country_id}"),
        InlineKeyboardButton(text="❌ No, Cancel", callback_data="admin_country_management")
    )
    return b.as_markup()

def build_user_management_keyboard():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🔍 Find User", callback_data="admin_find_user"))
    b.row(InlineKeyboardButton(text="⬅️ Back to Admin Panel", callback_data="admin_panel"))
    return b.as_markup()

# --- THIS KEYBOARD IS MODIFIED ---
def build_user_profile_keyboard(user: User):
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="➕ Add Balance", callback_data=f"admin_add_balance_{user.user_id}"),
        InlineKeyboardButton(text="➖ Remove Balance", callback_data=f"admin_remove_balance_{user.user_id}")
    )
    # Dynamically show Ban or Unban button
    if user.is_banned:
        ban_button = InlineKeyboardButton(text="✅ Unban User", callback_data=f"admin_unban_{user.user_id}")
    else:
        ban_button = InlineKeyboardButton(text="🚫 Ban User", callback_data=f"admin_ban_{user.user_id}")

    b.row(ban_button)
    b.row(InlineKeyboardButton(text="⬅️ Back to User Management", callback_data="admin_user_management"))
    return b.as_markup()

def build_messaging_keyboard():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📣 Broadcast to ALL Users", callback_data="admin_broadcast_all"))
    b.row(InlineKeyboardButton(text="🎯 Broadcast to Specific Users", callback_data="admin_broadcast_specific"))
    b.row(InlineKeyboardButton(text="⬅️ Back to Admin Panel", callback_data="admin_panel"))
    return b.as_markup()

def build_broadcast_targeting_keyboard():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🆔 By User IDs", callback_data="admin_target_by_id"))
    b.row(InlineKeyboardButton(text="🛍 By Country Purchased", callback_data="admin_target_by_country"))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="admin_messaging"))
    return b.as_markup()

def build_broadcast_country_select_keyboard(countries: list[Country]):
    b = InlineKeyboardBuilder()
    for c in countries:
        b.row(InlineKeyboardButton(text=f"{c.flag_emoji} {c.name}", callback_data=f"admin_broadcast_select_country_{c.id}"))
    b.row(InlineKeyboardButton(text="⬅️ Back", callback_data="admin_broadcast_specific"))
    return b.as_markup()

def build_broadcast_confirmation_keyboard(user_count: int):
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text=f"✅ Send to {user_count} User(s)", callback_data="admin_confirm_broadcast"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="admin_cancel_broadcast")
    )
    return b.as_markup()