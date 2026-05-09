from dataclasses import dataclass
from typing import Optional

class OrderMappingError(ValueError):
    pass

@dataclass
class V2OrderPayload:
    ticker: str
    action: str
    side: str
    type: str
    count: int
    yes_price: Optional[int] = None
    no_price: Optional[int] = None
    time_in_force: str = "gtc"

def map_intent_to_v2_payload(ticker: str, side: str, limit_price_cents: float, count: int,
                             min_price_cents: float = 1.0, max_price_cents: float = 99.0,
                             time_in_force: str = "gtc") -> V2OrderPayload:
    if side not in ("yes", "no"):
        raise OrderMappingError(f"Invalid side={side!r}. Must be 'yes' or 'no'")
    if not ticker or not isinstance(ticker, str):
        raise OrderMappingError("ticker must be a non-empty string")
    price_int = int(round(limit_price_cents))
    if price_int < min_price_cents or price_int > max_price_cents:
        raise OrderMappingError(f"Price {price_int}c outside valid range [{int(min_price_cents)}, {int(max_price_cents)}]c")
    if count < 1:
        raise OrderMappingError(f"count={count} must be >= 1")
    if time_in_force not in ("gtc", "ioc"):
        raise OrderMappingError(f"Invalid time_in_force={time_in_force!r}")
    payload = V2OrderPayload(ticker=ticker, action="buy", side=side, type="limit", count=count, time_in_force=time_in_force)
    if side == "yes":
        payload.yes_price = price_int
    else:
        payload.no_price = price_int
    return payload

def payload_to_dict(payload: V2OrderPayload) -> dict:
    d = {"ticker": payload.ticker, "action": payload.action, "side": payload.side,
         "type": payload.type, "count": payload.count, "time_in_force": payload.time_in_force}
    if payload.yes_price is not None:
        d["yes_price"] = payload.yes_price
    if payload.no_price is not None:
        d["no_price"] = payload.no_price
    return d
