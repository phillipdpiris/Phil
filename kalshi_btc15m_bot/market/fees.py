from __future__ import annotations
import math

def estimate_entry_fee(price_cents: float, contracts: float, maker: bool = False) -> float:
    if maker:
        return 0.0
    p = max(0.0, min(1.0, price_cents / 100.0))
    raw_dollars = 0.07 * contracts * p * (1.0 - p)
    return math.ceil(raw_dollars * 100.0) / 100.0 * 100.0

def estimate_exit_fee(price_cents: float, contracts: float, maker: bool = False) -> float:
    return estimate_entry_fee(price_cents, contracts, maker=maker)

def estimate_round_trip_cost(entry_price_cents: float, exit_price_cents: float, contracts: float,
                             maker_entry: bool = False, maker_exit: bool = False) -> float:
    return estimate_entry_fee(entry_price_cents, contracts, maker_entry) + estimate_exit_fee(exit_price_cents, contracts, maker_exit)

def net_edge_cents(fair_value_cents: float, market_price_cents: float, fee_cents: float,
                  spread_cents: float, slippage_cents: float) -> float:
    return fair_value_cents - market_price_cents - fee_cents - spread_cents - slippage_cents
