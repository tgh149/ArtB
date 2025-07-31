import aiohttp
import time
import asyncio
from decimal import Decimal, ROUND_HALF_UP

# In a real app, store this in your config
API_URL = "https://open.er-api.com/v6/latest/USD"

class CurrencyConverter:
    def __init__(self):
        self.rates = {}
        self.last_updated = 0
        self.cache_duration = 3600  # Cache for 1 hour
        self.symbols = {
            "USD": "$",
            "RUB": "₽",
            "CNY": "¥"
        }
        self.formatting = {
            "USD": "{symbol}{amount:.2f}",
            "RUB": "{amount:.2f} {symbol}",
            "CNY": "{symbol}{amount:.2f}"
        }
        self._update_task = None

    async def _fetch_rates(self):
        """Fetches rates from the API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_URL) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("result") == "success":
                            self.rates = data.get("rates", {})
                            self.last_updated = time.time()
                            print("Currency rates updated successfully.")
                    else:
                        print(f"Failed to fetch currency rates. Status: {response.status}")
        except Exception as e:
            print(f"Error updating currency rates: {e}")

    async def update_rates_periodically(self):
        """A background task to update rates every hour."""
        while True:
            await self._fetch_rates()
            await asyncio.sleep(self.cache_duration)

    def start_background_update(self):
        """Starts the background task."""
        if not self._update_task or self._update_task.done():
            self._update_task = asyncio.create_task(self.update_rates_periodically())
            print("Started background currency rate updates.")

    def stop_background_update(self):
        """Stops the background task."""
        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
            print("Stopped background currency rate updates.")


    async def _ensure_rates_are_loaded(self):
        """Ensures that rates are loaded at least once before converting."""
        if not self.rates:
            print("Initial currency rates not loaded. Fetching now...")
            await self._fetch_rates()

    async def convert(self, amount_usd: Decimal, target_currency: str) -> Decimal:
        await self._ensure_rates_are_loaded()
        target_currency = target_currency.upper()

        if not self.rates or target_currency not in self.rates:
            return amount_usd # Fallback to USD if rates are unavailable

        rate = Decimal(str(self.rates.get(target_currency, 1)))
        converted_amount = (amount_usd * rate)
        return converted_amount

    async def format_currency(self, amount_usd: Decimal, target_currency: str) -> str:
        await self._ensure_rates_are_loaded()
        target_currency = target_currency.upper()
        converted_amount = await self.convert(amount_usd, target_currency)
        
        symbol = self.symbols.get(target_currency, "$")
        format_str = self.formatting.get(target_currency, "{symbol}{amount:.2f}")

        quantizer = Decimal("0.01")
        rounded_amount = converted_amount.quantize(quantizer, rounding=ROUND_HALF_UP)
        
        return format_str.format(amount=rounded_amount, symbol=symbol)

# Global instance
currency_converter = CurrencyConverter()