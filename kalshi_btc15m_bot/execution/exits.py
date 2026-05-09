from __future__ import annotations
from ..market.orderbook import best_no_bid, best_yes_bid
from ..models import ExitDecision, PositionState

def mark_to_market(position: PositionState, book) -> dict:
    bid = best_yes_bid(book) if position.side == "yes" else best_no_bid(book)
    gross_pnl_cents = bid - position.avg_entry_price_cents
    gross_pct = 0.0 if position.avg_entry_price_cents <= 0 else gross_pnl_cents / position.avg_entry_price_cents
    return {"bid_cents": bid, "gross_pnl_cents": gross_pnl_cents, "gross_pct": gross_pct}

def should_take_tp1(position: PositionState, mtm: dict, remaining: int, cfg) -> bool:
    return (not position.tp1_done) and mtm["gross_pct"] >= 0.08

def should_take_tp2(position: PositionState, mtm: dict, remaining: int, cfg) -> bool:
    return position.tp1_done and (not position.tp2_done) and mtm["gross_pct"] >= 0.12

def should_stop_out(position: PositionState, mtm: dict, remaining: int, cfg) -> bool:
    return (mtm.get("gross_pct", 0.0) or 0.0) <= -0.06

def should_force_flatten(position: PositionState, remaining: int, residual_edge_cents: float, cfg) -> bool:
    if remaining <= 60 and residual_edge_cents < cfg.final_minute_min_edge_cents:
        return True
    if remaining <= 180 and residual_edge_cents < 0:
        return True
    return False

def build_exit_decision(position: PositionState, book, remaining: int, residual_edge_cents: float, cfg) -> ExitDecision:
    mtm = mark_to_market(position, book)
    if should_stop_out(position, mtm, remaining, cfg):
        return ExitDecision("sell_all", position.contracts, mtm["bid_cents"], "stop loss")
    if should_take_tp1(position, mtm, remaining, cfg):
        return ExitDecision("sell_partial", max(1, int(round(position.contracts * 0.50))), mtm["bid_cents"], "tp1")
    if should_take_tp2(position, mtm, remaining, cfg):
        return ExitDecision("sell_partial", max(1, int(round(position.contracts * 0.30))), mtm["bid_cents"], "tp2")
    if should_force_flatten(position, remaining, residual_edge_cents, cfg):
        return ExitDecision("sell_all", position.contracts, mtm["bid_cents"], "late flatten")
    return ExitDecision("hold", 0, mtm["bid_cents"], "hold")
