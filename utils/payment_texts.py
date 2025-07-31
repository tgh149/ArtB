def get_deposit_instructions(method_key: str, lang: str = "en") -> str:
    """Get enhanced payment instructions for a specific method with multi-language support"""
    from utils.localization import translator
    
    method_info = PAYMENT_DETAILS.get(method_key, {})
    method_name = method_info.get("name", "Manual Payment")
    
    # Enhanced instruction text with eye-catching emojis
    title = f"💰 <b>{translator.get_string('deposit_instructions_title', lang)} – {method_name}</b>"
    
    warning = f"⚠️ <b>{translator.get_string('important_warning', lang)}</b>"
    instructions_header = f"📋 <b>{translator.get_string('payment_steps', lang)}</b>"
    
    step1 = f"1️⃣ {translator.get_string('step_send_payment', lang)}"
    step2 = f"2️⃣ {translator.get_string('step_click_done', lang)}"
    step3 = f"3️⃣ {translator.get_string('step_provide_screenshot', lang)}"
    
    min_deposit = f"💵 <b>{translator.get_string('minimum_deposit', lang)}: ${MINIMUM_DEPOSIT:.2f}</b>"
    
    # Payment details section
    details_section = ""
    if "address" in method_info:
        details_section += f"📍 <b>{translator.get_string('payment_address', lang)}:</b>\n<code>{method_info['address']}</code>\n\n"
    if "pay_id" in method_info:
        details_section += f"🆔 <b>{translator.get_string('payment_id', lang)}:</b>\n<code>{method_info['pay_id']}</code>\n\n"
    if "memo" in method_info and method_info["memo"]:
        details_section += f"🚨 <b>{translator.get_string('memo_required', lang)}:</b>\n<code>{method_info['memo']}</code>\n\n"
    
    separator = "━━━━━━━━━━━━━━━━━━━━━━"
    
    return f"{title}\n\n{warning}\n{instructions_header}\n{step1}\n{step2}\n{step3}\n\n{separator}\n{details_section}{separator}\n\n{min_deposit}"

PAYMENT_DETAILS = {
    "binance_pay": {"name": "💳 Binance Pay", "pay_id": "765610848"},
    "usdt_trc20": {"name": " USDT (TRC-20)", "address": "TAX8TJQdaJeMXvk15EdVLABY7doUus4SP7"},
    "solana": {"name": "⚡ Solana (SOL)", "address": "8vDWVEMCjYE9P8FSBs3jmbmHmR3kJUdtY7GDPRppvkWi"},
    "trx": {"name": " TRX (TRON)", "address": "TAX8TJQdaJeMXvk15EdVLABY7doUus4SP7"},
    "bnb_bep20": {"name": " BNB (BEP-20)", "address": "0xdf5c00e99ee8f42fd7cb2c72d6198d7e45e0f17a"},
    "ton": {"name": "💎 Toncoin (TON)", "address": "EQD5mxRgCuRNLxKxeOjG6r14iSroLF5FtomPnet-sgP5xNJb", "memo": "104001804"},
    "crypto_bot": {"name": "🤖 Crypto Bot API"}
}
MINIMUM_DEPOSIT = 1.00

def get_deposit_instructions(method_key: str) -> str:
    details = PAYMENT_DETAILS.get(method_key, {})
    text = (f"💰 <b>Add Funds – {details.get('name', 'N/A')}</b>\n\n1️⃣ Send payment to the address/ID below.\n2️⃣ Click '✅ Done' after sending.\n3️⃣ Provide the amount and screenshot.\n---\n<b>Minimum Deposit:</b> ${MINIMUM_DEPOSIT:.2f}\n\n")
    if "address" in details: text += f"<b>Address:</b>\n<code>{details['address']}</code>\n\n"
    if "pay_id" in details: text += f"<b>Pay ID:</b>\n<code>{details['pay_id']}</code>\n\n"
    if "memo" in details and details["memo"]: text += f"❗️ <b>MUST INCLUDE MEMO:</b>\n<code>{details['memo']}</code>\n\n"
    return text