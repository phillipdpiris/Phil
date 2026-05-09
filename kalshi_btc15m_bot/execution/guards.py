from __future__ import annotations
from ..market.orderbook import depth_at_best, no_spread, yes_spread
from ..models import BotState

def spread_ok(book, cfg, side: str = "yes") -> bool:
    spread = yes_spread(book) if side == "yes" else no_spread(book)
    return spread <= cfg.max_spread_cents

def depth_ok(book, cfg, side: str = "yes") -> bool:
    return depth_at_best(book, side) >= cfg.min_depth_contracts

def time_ok(phase: str, remaining: int, cfg) -> bool:
    if phase != "final_minute" and remaining <= 20:
        return False
    return True

def single_position_ok(state: BotState) -> bool:
    return state.position is None

def net_edge_ok(edge_cents: float, phase: str, cfg) -> bool:
    threshold = cfg.final_minute_min_edge_cents if phase == "final_minute" else cfg.normal_min_edge_cents
    return edge_cents >= threshold
