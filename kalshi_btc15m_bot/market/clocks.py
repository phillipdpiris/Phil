from __future__ import annotations
from datetime import datetime
from ..models import MarketSnapshot, Phase

def get_market_times(market: MarketSnapshot) -> tuple[datetime, datetime]:
    return market.open_time, market.close_time

def elapsed_seconds(open_time: datetime, now: datetime) -> int:
    return max(0, int((now - open_time).total_seconds()))

def remaining_seconds(close_time: datetime, now: datetime) -> int:
    return max(0, int((close_time - now).total_seconds()))

def phase_from_clock(open_time: datetime, close_time: datetime, now: datetime) -> Phase:
    elapsed = elapsed_seconds(open_time, now)
    remaining = remaining_seconds(close_time, now)
    if remaining <= 60:
        return "final_minute"
    if elapsed < 180:
        return "phase1"
    if elapsed < 480:
        return "phase2"
    return "phase3"

def is_final_minute(close_time: datetime, now: datetime) -> bool:
    return remaining_seconds(close_time, now) <= 60
