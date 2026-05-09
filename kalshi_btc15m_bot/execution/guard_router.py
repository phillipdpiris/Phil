"""
guard_router.py — Wires all execution guards into a single entry-path check.

All guards must pass before any EV calculation or order routing occurs.
A failed guard produces a logged skip event — never a silent no-op.

Guards checked (in order):
  1. data_freshness_ok  — signal and orderbook not stale
  2. spread_ok          — spread within acceptable range
  3. depth_ok           — sufficient visible liquidity
  4. time_ok            — not in blocked entry window
  5. price_bounds_ok    — price within [min_price_cents, max_price_cents]
"""

from dataclasses import dataclass
from typing import Optional

from kalshi_btc15m_bot.market.orderbook import yes_spread, no_spread, depth_at_best


@dataclass
class GuardResult:
    passed: bool
    skip_reason: Optional[str] = None
    block_reason: Optional[str] = None
    spread_ok: Optional[bool] = None
    depth_ok: Optional[bool] = None
    time_ok: Optional[bool] = None
    data_freshness_ok: Optional[bool] = None
    price_bounds_ok: Optional[bool] = None


@dataclass
class GuardContext:
    best_yes_bid: float
    best_yes_ask: float
    best_no_bid: float
    best_no_ask: float
    spread_cents: float
    depth_bid: float
    depth_ask: float
    book_timestamp_ms: float
    signal_timestamp_ms: float
    current_timestamp_ms: float
    minutes_to_expiry: float
    limit_price_cents: float
    max_spread_cents: float = 5.0
    min_depth: float = 10.0
    min_price_cents: float = 1.0
    max_price_cents: float = 99.0
    max_book_age_seconds: float = 2.0
    max_signal_age_seconds: float = 5.0
    tau_floor_seconds: float = 60.0


class GuardRouter:
    def __init__(self, cfg: Optional[dict] = None):
        self.cfg = cfg or {}

    def check(self, ctx: GuardContext) -> GuardResult:
        result = GuardResult(passed=False)
        signal_age_s = (ctx.current_timestamp_ms - ctx.signal_timestamp_ms) / 1000.0
        book_age_s = (ctx.current_timestamp_ms - ctx.book_timestamp_ms) / 1000.0
        signal_fresh = signal_age_s <= ctx.max_signal_age_seconds
        book_fresh = book_age_s <= ctx.max_book_age_seconds
        result.data_freshness_ok = signal_fresh and book_fresh
        if not signal_fresh:
            result.skip_reason = "STALE_SIGNAL"
            result.block_reason = f"Signal age {signal_age_s:.2f}s exceeds max {ctx.max_signal_age_seconds}s"
            return result
        if not book_fresh:
            result.skip_reason = "STALE_ORDERBOOK"
            result.block_reason = f"Book age {book_age_s:.2f}s exceeds max {ctx.max_book_age_seconds}s"
            return result
        spread_passed = ctx.spread_cents <= ctx.max_spread_cents
        result.spread_ok = spread_passed
        if not spread_passed:
            result.skip_reason = "SPREAD_TOO_WIDE"
            result.block_reason = f"Spread {ctx.spread_cents:.1f}¢ exceeds max {ctx.max_spread_cents:.1f}¢"
            return result
        min_side_depth = min(ctx.depth_bid, ctx.depth_ask)
        depth_passed = min_side_depth >= ctx.min_depth
        result.depth_ok = depth_passed
        if not depth_passed:
            result.skip_reason = "INSUFFICIENT_DEPTH"
            result.block_reason = f"Depth bid={ctx.depth_bid} ask={ctx.depth_ask} below min {ctx.min_depth}"
            return result
        seconds_to_expiry = ctx.minutes_to_expiry * 60.0
        time_passed = seconds_to_expiry > ctx.tau_floor_seconds
        result.time_ok = time_passed
        if not time_passed:
            result.skip_reason = "TIME_GUARD_BLOCKED"
            result.block_reason = f"minutes_to_expiry={ctx.minutes_to_expiry:.2f} within tau_floor ({ctx.tau_floor_seconds}s)"
            return result
        price_ok = ctx.min_price_cents <= ctx.limit_price_cents <= ctx.max_price_cents
        result.price_bounds_ok = price_ok
        if not price_ok:
            result.skip_reason = "INVALID_PRICE"
            result.block_reason = f"Price {ctx.limit_price_cents}¢ outside [{ctx.min_price_cents}, {ctx.max_price_cents}]¢"
            return result
        result.passed = True
        result.spread_ok = True
        result.depth_ok = True
        result.time_ok = True
        result.data_freshness_ok = True
        result.price_bounds_ok = True
        return result
