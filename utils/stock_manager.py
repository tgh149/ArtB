import os
import re

ACCOUNTS_DIR = "accounts"

# This dictionary maps the numeric country code to its flag emoji.
# You can easily add more countries here as needed.
COUNTRY_CODE_TO_FLAG = {
    '1': '🇺🇸', '7': '🇷🇺', '20': '🇪🇬', '27': '🇿🇦', '30': '🇬🇷', '31': '🇳🇱', '32': '🇧🇪', '33': '🇫🇷', '34': '🇪🇸',
    '36': '🇭🇺', '39': '🇮🇹', '40': '🇷🇴', '41': '🇨🇭', '43': '🇦🇹', '44': '🇬🇧', '45': '🇩🇰', '46': '🇸🇪', '47': '🇳🇴',
    '48': '🇵🇱', '49': '🇩🇪', '52': '🇲🇽', '55': '🇧🇷', '56': '🇨🇱', '60': '🇲🇾', '62': '🇮🇩', '63': '🇵🇭', '64': '🇳🇿',
    '65': '🇸🇬', '66': '🇹🇭', '81': '🇯🇵', '82': '🇰🇷', '84': '🇻🇳', '86': '🇨🇳', '90': '🇹🇷', '91': '🇮🇳', '92': '🇵🇰',
    '94': '🇱🇰', '95': '🇲🇲', '98': '🇮🇷', '212': '🇲🇦', '213': '🇩🇿', '216': '🇹🇳', '220': '🇬🇲', '221': '🇸🇳', '225': '🇨🇮',
    '234': '🇳🇬', '251': '🇪🇹', '254': '🇰🇪', '255': '🇹🇿', '267': '🇧🇼', '351': '🇵🇹', '353': '🇮🇪', '358': '🇫🇮', '370': '🇱🇹',
    '371': '🇱🇻', '372': '🇪🇪', '375': '🇧🇾', '380': '🇺🇦', '420': '🇨🇿', '852': '🇭🇰', '880': '🇧🇩', '964': '🇮🇶', '971': '🇦🇪',
    '998': '🇺🇿',
}

def get_country_code_str(folder_name: str) -> str:
    """Extracts just the numeric part of the country code (e.g., '95')."""
    match = re.search(r'\+(\d+)', folder_name)
    return match.group(1) if match else ""

def get_country_name(folder_name: str) -> str:
    """Extracts the country name like 'Myanmar' from a folder name."""
    name = re.sub(r'\+\d+\s*', '', folder_name).strip()
    return name if name else "Unknown"

def get_flag_emoji(country_code_str: str) -> str:
    """Returns a flag emoji for a given country code string, or a default."""
    return COUNTRY_CODE_TO_FLAG.get(country_code_str, '🏳️') # Default to white flag

def get_live_stock() -> dict:
    """
    Scans the live filesystem in the /accounts directory and returns a dictionary 
    of {folder_name: count} for all folders that contain .session files.
    """
    if not os.path.isdir(ACCOUNTS_DIR):
        print(f"Warning: Stock directory '{ACCOUNTS_DIR}' not found. Creating it.")
        os.makedirs(ACCOUNTS_DIR)
        return {}

    stock = {}
    try:
        for entry in os.scandir(ACCOUNTS_DIR):
            if entry.is_dir():
                try:
                    session_files = [f for f in os.listdir(entry.path) if f.endswith('.session')]
                    if session_files:
                        stock[entry.name] = len(session_files)
                except OSError: continue
    except OSError as e:
        print(f"Error scanning stock directory '{ACCOUNTS_DIR}': {e}")
        return {}
        
    return stock