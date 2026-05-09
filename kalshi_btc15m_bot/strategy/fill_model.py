import math
from dataclasses import dataclass
from typing import Optional

class FillModelError(ValueError):
    pass

@dataclass
class FillEstimate:
    p_fill_base: float
    order_price: float
    best_bid: float
    best_ask: float
    spread: float
    price_position: float
    reason: str

def estimate_fill_probability_base(order_price: float, best_bid: float, best_ask: float,
                                   spread: Optional[float] = None) -> FillEstimate:
    if order_price is None or math.isnan(order_price):
        raise FillModelError("order_price is None or NaN")
    if best_bid is None or best_ask is None:
        raise FillModelError("Orderbook missing")
    if math.isnan(best_bid) or math.isnan(best_ask):
        raise FillModelError("Orderbook contains NaN values")
    if best_ask <= best_bid:
        raise FillModelError(f"Invalid orderbook: best_ask={best_ask} <= best_bid={best_bid}")
    computed_spread = best_ask - best_bid
    if computed_spread <= 0:
        raise FillModelError(f"Non-positive spread: {computed_spread}")
    effective_spread = max(computed_spread, 1e-9)
    mid = (best_bid + best_ask) / 2.0
    position = (order_price - mid) / effective_spread
    if position >= 0.4:
        p_fill, reason = 0.85, "near_ask_aggressive"
    elif position <= -0.4:
        p_fill, reason = 0.25, "near_bid_passive"
    else:
        p_fill, reason = 0.50, "inside_spread"
    return FillEstimate(p_fill_base=p_fill, order_price=order_price, best_bid=best_bid,
                        best_ask=best_ask, spread=effective_spread, price_position=position, reason=reason)
