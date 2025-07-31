from aiogram.fsm.state import State, StatesGroup

class PurchaseStates(StatesGroup):
    browse_categories = State()
    browse_products = State()
    select_quantity = State()
    select_delivery_method = State()
    manual_delivery = State()

class DepositStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_manual_amount = State()
    waiting_for_crypto_amount = State()
    waiting_for_done_confirmation = State()
    waiting_for_screenshot = State()
    select_deposit_amount = State()
    select_payment_method = State()

class BrowsingStates(StatesGroup):
    viewing_categories = State()
    viewing_products = State()
    configuring_purchase = State()

class AdminStates(StatesGroup):
    # Country Management
    add_country_name = State()
    add_country_code = State()
    add_country_flag = State()
    add_country_price = State()
    
    # User Management
    find_user = State()
    adjust_balance_amount = State()

    # Messaging
    get_broadcast_message = State()
    confirm_broadcast = State()
    get_targeted_user_ids = State()

# --- NEW STATES FOR WITHDRAWAL ---
class WithdrawalStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_address = State()