
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from database.models import Country
from typing import Dict, List
import os

def build_categories_keyboard(folders_info: Dict[str, int]):
    """Build keyboard showing product categories with stock counts"""
    builder = InlineKeyboardBuilder()
    
    for folder_name, stock_count in folders_info.items():
        # Extract meaningful display name from folder
        display_name = folder_name.replace('+', '').replace('_', ' ').title()
        if stock_count > 0:
            builder.row(InlineKeyboardButton(
                text=f"🗂️ {display_name} [stock: {stock_count}]",
                callback_data=f"browse_category_{folder_name}"
            ))
    
    builder.row(InlineKeyboardButton(text="◀️ Back to Main Menu", callback_data="main_menu_start"))
    return builder.as_markup()

def build_products_keyboard(folder_name: str, products: List[str], price_per_item: float = 1.0):
    """Build keyboard showing individual products in a category"""
    builder = InlineKeyboardBuilder()
    
    for idx, product in enumerate(products):
        # Clean product name for display
        display_name = product.replace('.session', '').replace('_', ' ')
        # Use index instead of full product name to avoid callback data length limit
        builder.row(InlineKeyboardButton(
            text=f"📱 {display_name} - ${price_per_item:.2f}",
            callback_data=f"select_product_{folder_name}_{idx}"
        ))
    
    builder.row(InlineKeyboardButton(text="◀️ Back to Categories", callback_data="back_to_categories"))
    return builder.as_markup()

def build_quantity_selector_keyboard(folder_name: str, product_idx: int, current_qty: int, max_stock: int, price_per_item: float, user_balance: float):
    """Build quantity selector with +/- buttons and purchase options"""
    builder = InlineKeyboardBuilder()
    
    total_cost = current_qty * price_per_item
    
    # Quantity controls
    builder.row(
        InlineKeyboardButton(text="➖", callback_data=f"qty_minus_{folder_name}_{product_idx}_{current_qty}"),
        InlineKeyboardButton(text=f"Enter Qty: {current_qty}", callback_data=f"qty_manual_{folder_name}_{product_idx}"),
        InlineKeyboardButton(text="➕", callback_data=f"qty_plus_{folder_name}_{product_idx}_{current_qty}")
    )
    
    # Balance or Buy button
    if user_balance < total_cost:
        builder.row(InlineKeyboardButton(
            text=f"💰 Balance (${user_balance:.2f} < ${total_cost:.2f})",
            callback_data="insufficient_balance"
        ))
    else:
        builder.row(InlineKeyboardButton(
            text=f"🛒 Buy Now (${total_cost:.2f})",
            callback_data=f"confirm_purchase_{folder_name}_{product_idx}_{current_qty}"
        ))
    
    # Navigation
    builder.row(
        InlineKeyboardButton(text="📋 Menu", callback_data="main_menu_start"),
        InlineKeyboardButton(text="◀️ GoBack", callback_data=f"back_to_products_{folder_name}")
    )
    
    builder.row(InlineKeyboardButton(text="❌ Cancel", callback_data="global_cancel"))
    return builder.as_markup()

def build_deposit_amount_keyboard(current_amount: float = 1.0):
    """Build deposit amount selector with +/- buttons"""
    builder = InlineKeyboardBuilder()
    
    # Amount controls
    builder.row(
        InlineKeyboardButton(text="➖", callback_data=f"deposit_minus_{current_amount}"),
        InlineKeyboardButton(text=f"Enter Qty: {current_amount:.0f}", callback_data="deposit_manual"),
        InlineKeyboardButton(text="➕", callback_data=f"deposit_plus_{current_amount}")
    )
    
    # Checkout button
    builder.row(InlineKeyboardButton(
        text="💳 Checkout",
        callback_data=f"deposit_checkout_{current_amount}"
    ))
    
    builder.row(InlineKeyboardButton(text="❌ Cancel", callback_data="global_cancel"))
    return builder.as_markup()

def build_delivery_method_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📦 ZIP File (.session)", callback_data="delivery_zip"),
        InlineKeyboardButton(text="📲 Manual OTP", callback_data="delivery_manual")
    )
    builder.row(InlineKeyboardButton(text="❌ Cancel", callback_data="global_cancel"))
    return builder.as_markup()

def build_manual_delivery_keyboard(account_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🧩 Check for OTP", callback_data=f"manual_otp_{account_id}"),
        InlineKeyboardButton(text="➡️ Next Account", callback_data=f"manual_next_{account_id}")
    )
    builder.row(InlineKeyboardButton(text="❌ Cancel & Stop Delivery", callback_data="global_cancel"))
    return builder.as_markup()
