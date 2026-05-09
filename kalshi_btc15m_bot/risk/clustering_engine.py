import time
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class OpenPosition:
    market_ticker: str
    side: str
    strike: float
    notional_cents: int
    opened_at_ms: float

@dataclass
class RecentTrade:
    side: str
    opened_at_ms: float

@dataclass
class ClusteringConfig:
    max_trades_per_direction_per_5min: int = 1
    max_open_positions_same_side: int = 3
    max_total_open_positions: int = 5
    min_strike_separation_pct: float = 1.0
    max_notional_per_side_cents: int = 2500
    max_total_open_notional_cents: int = 5000

@dataclass
class ClusteringResult:
    allowed: bool
    skip_reason: Optional[str] = None
    block_reason: Optional[str] = None

def check_clustering(new_side, new_strike, new_notional_cents, open_positions, recent_trades,
                    cfg=None, now_ms=None):
    if cfg is None: cfg = ClusteringConfig()
    if now_ms is None: now_ms = time.time() * 1000.0
    window_ms = 5 * 60 * 1000.0
    same_side_recent = [t for t in recent_trades if t.side == new_side and (now_ms - t.opened_at_ms) <= window_ms]
    if len(same_side_recent) >= cfg.max_trades_per_direction_per_5min:
        return ClusteringResult(allowed=False, skip_reason="CLUSTERING_RATE_LIMIT",
                                block_reason=f"{len(same_side_recent)} {new_side.upper()} trades in last 5min (max={cfg.max_trades_per_direction_per_5min})")
    same_side_open = [p for p in open_positions if p.side == new_side]
    if len(same_side_open) >= cfg.max_open_positions_same_side:
        return ClusteringResult(allowed=False, skip_reason="CLUSTERING_SAME_SIDE_LIMIT",
                                block_reason=f"{len(same_side_open)} open {new_side.upper()} positions (max={cfg.max_open_positions_same_side})")
    if len(open_positions) >= cfg.max_total_open_positions:
        return ClusteringResult(allowed=False, skip_reason="CLUSTERING_TOTAL_POSITION_LIMIT",
                                block_reason=f"{len(open_positions)} total open positions (max={cfg.max_total_open_positions})")
    min_sep = cfg.min_strike_separation_pct / 100.0
    for pos in same_side_open:
        if pos.strike == 0: continue
        sep = abs(new_strike - pos.strike) / pos.strike
        if sep < min_sep:
            return ClusteringResult(allowed=False, skip_reason="CLUSTERING_STRIKE_TOO_CLOSE",
                                    block_reason=f"Strike {new_strike} is {sep*100:.3f}% from {pos.strike} (min={cfg.min_strike_separation_pct}%)")
    same_side_notional = sum(p.notional_cents for p in same_side_open)
    if same_side_notional + new_notional_cents > cfg.max_notional_per_side_cents:
        return ClusteringResult(allowed=False, skip_reason="CLUSTERING_NOTIONAL_SIDE_LIMIT",
                                block_reason=f"{new_side.upper()} notional {same_side_notional+new_notional_cents}c (max={cfg.max_notional_per_side_cents}c)")
    total_notional = sum(p.notional_cents for p in open_positions)
    if total_notional + new_notional_cents > cfg.max_total_open_notional_cents:
        return ClusteringResult(allowed=False, skip_reason="CLUSTERING_TOTAL_NOTIONAL_LIMIT",
                                block_reason=f"Total notional {total_notional+new_notional_cents}c (max={cfg.max_total_open_notional_cents}c)")
    return ClusteringResult(allowed=True)
