from __future__ import annotations
import uuid
from ..clients.kalshi_rest import KalshiRestClient

def build_limit_buy_yes(ticker: str, contracts: int, yes_price_cents: float) -> dict:
    return {"ticker": ticker, "side": "yes", "action": "buy", "type": "limit",
            "count": int(contracts), "yes_price": int(round(yes_price_cents)), "client_order_id": str(uuid.uuid4())}

def build_limit_buy_no(ticker: str, contracts: int, no_price_cents: float) -> dict:
    return {"ticker": ticker, "side": "no", "action": "buy", "type": "limit",
            "count": int(contracts), "no_price": int(round(no_price_cents)), "client_order_id": str(uuid.uuid4())}

def build_limit_sell_yes(ticker: str, contracts: int, yes_price_cents: float) -> dict:
    return {"ticker": ticker, "side": "yes", "action": "sell", "type": "limit",
            "count": int(contracts), "yes_price": int(round(yes_price_cents)), "client_order_id": str(uuid.uuid4())}

def build_limit_sell_no(ticker: str, contracts: int, no_price_cents: float) -> dict:
    return {"ticker": ticker, "side": "no", "action": "sell", "type": "limit",
            "count": int(contracts), "no_price": int(round(no_price_cents)), "client_order_id": str(uuid.uuid4())}

def submit_order(rest: KalshiRestClient, payload: dict) -> dict:
    return rest.auth_post("/portfolio/orders", payload)

def cancel_order(rest: KalshiRestClient, order_id: str) -> dict:
    return rest.auth_delete(f"/portfolio/orders/{order_id}")

def amend_order(rest: KalshiRestClient, order_id: str, payload: dict) -> dict:
    return rest.auth_post(f"/portfolio/orders/{order_id}/amend", payload)
