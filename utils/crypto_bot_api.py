import aiohttp
from typing import Optional, Dict, Any

class CryptoBotAPI:
    def __init__(self, token: str):
        self.base_url = "https://pay.crypt.bot/api"
        self.headers = {"Crypto-Pay-API-Token": token}

    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/{endpoint}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.request(method, url, headers=self.headers, json=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if data.get("ok"):
                        return data.get("result")
                    return None
            except aiohttp.ClientError as e:
                print(f"API request error: {e}")
                return None

    async def get_me(self):
        return await self._make_request("GET", "getMe")

    async def create_invoice(self, amount: float, asset: str = "USDT", description: str = "Add Funds") -> Optional[Dict]:
        params = {
            "amount": amount,
            "asset": asset,
            "description": description,
            "expires_in": 3600  # Invoice expires in 1 hour
        }
        return await self._make_request("POST", "createInvoice", params)

    async def get_invoices(self, invoice_ids: str):
        params = {"invoice_ids": invoice_ids}
        return await self._make_request("GET", "getInvoices", params)