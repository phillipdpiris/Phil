from __future__ import annotations
from ..models import EntryDecision, ExitDecision
from ..market.orderbook import best_no_ask, best_no_bid, best_yes_ask, best_yes_bid
from .orders import build_limit_buy_no, build_limit_buy_yes, build_limit_sell_no, build_limit_sell_yes, submit_order

def choose_order_style(decision: EntryDecision, phase: str) -> str:
    return "aggressive_limit" if phase == "final_minute" else decision.order_style

def price_for_resting_limit(decision: EntryDecision, book) -> float:
    return max(0.0, best_yes_ask(book) - 1.0) if decision.side == "yes" else max(0.0, best_no_ask(book) - 1.0)

def price_for_aggressive_limit(decision: EntryDecision, book) -> float:
    return best_yes_ask(book) if decision.side == "yes" else best_no_ask(book)

def route_entry(rest, ticker: str, decision: EntryDecision, book, phase: str, dry_run: bool = True) -> dict:
    if not decision.tradable or not decision.side:
        return {"skipped": True, "reason": decision.reason}
    style = choose_order_style(decision, phase)
    price = price_for_resting_limit(decision, book) if style == "resting_limit" else price_for_aggressive_limit(decision, book)
    payload = build_limit_buy_yes(ticker, decision.contracts, price) if decision.side == "yes" else build_limit_buy_no(ticker, decision.contracts, price)
    return {"dry_run": True, "payload": payload} if dry_run else submit_order(rest, payload)

def route_exit(rest, ticker: str, side: str, decision: ExitDecision, book, dry_run: bool = True) -> dict:
    if decision.action == "hold":
        return {"skipped": True, "reason": decision.reason}
    price = best_yes_bid(book) if side == "yes" else best_no_bid(book)
    payload = build_limit_sell_yes(ticker, decision.contracts, price) if side == "yes" else build_limit_sell_no(ticker, decision.contracts, price)
    return {"dry_run": True, "payload": payload} if dry_run else submit_order(rest, payload)
