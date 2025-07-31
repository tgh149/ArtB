import json
import os
from typing import Dict

class Translator:
    def __init__(self, locales_dir: str = "locales"):
        self.locales = {}
        for filename in os.listdir(locales_dir):
            if filename.endswith(".json"):
                lang_code = filename.split(".")[0]
                with open(os.path.join(locales_dir, filename), "r", encoding="utf-8") as f:
                    self.locales[lang_code] = json.load(f)

    def get_string(self, key: str, lang: str, **kwargs) -> str:
        """
        Get a translated string. Falls back to English if the key is not found
        in the target language.
        """
        lang = lang if lang in self.locales else "en"
        base_string = self.locales.get(lang, {}).get(key)

        if not base_string:
            # Fallback to English
            base_string = self.locales.get("en", {}).get(key, f"_{key}_")

        return base_string.format(**kwargs)

    def get_all_translations(self, key: str) -> Dict[str, str]:
        """
        Returns a dictionary of all available translations for a specific key.
        e.g., {'en': 'Settings', 'ru': 'Настройки'}
        """
        return {
            lang: self.get_string(key, lang)
            for lang in self.locales
        }

# Global instance
translator = Translator()