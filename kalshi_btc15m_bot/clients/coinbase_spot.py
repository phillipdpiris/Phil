from __future__ import annotations
import requests

class CoinbaseSpotClient:
    BASE_URL = "https://api.exchange.coinbase.com"
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "kalshi-btc15m-bot/0.1"})
    def get_candles(self, product: str, granularity: int) -> list[dict]:
        url = f"{self.BASE_URL}/products/{product}/candles"
        response = self.session.get(url, params={"granularity": granularity}, timeout=15)
        response.raise_for_status()
        rows = response.json()
        rows.sort(key=lambda row: row[0])
        return [{"time": int(row[0]), "low": float(row[1]), "high": float(row[2]),
                 "open": float(row[3]), "close": float(row[4]), "volume": float(row[5])} for row in rows]
    def get_last_trade(self, product: str) -> dict:
        url = f"{self.BASE_URL}/products/{product}/ticker"
        response = self.session.get(url, timeout=15)
        response.raise_for_status()
        payload = response.json()
        return {"price": float(payload["price"]), "bid": float(payload.get("bid", payload["price"])),
                "ask": float(payload.get("ask", payload["price"])), "time": payload.get("time")}
