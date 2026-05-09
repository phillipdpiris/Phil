from dataclasses import dataclass
from typing import Optional

@dataclass
class StrategyDecision:
    side: str
    strategy_name: str
    should_trade: bool
    skip_reason: Optional[str] = None
    notes: Optional[str] = None

def route(side: str, p_adj: float, minutes_to_expiry: float,
          ev_submitted_cents: float, min_ev_cents: float = 1.0) -> StrategyDecision:
    if side not in ("yes", "no"):
        return StrategyDecision(side=side, strategy_name="unknown",
                                should_trade=False, skip_reason="INVALID_SIDE")
    if ev_submitted_cents < min_ev_cents:
        return StrategyDecision(side=side, strategy_name="symmetric_phase1",
                                should_trade=False, skip_reason="EV_BELOW_THRESHOLD",
                                notes=f"ev_submitted={ev_submitted_cents:.3f}c < min={min_ev_cents}c")
    return StrategyDecision(side=side, strategy_name="symmetric_phase1", should_trade=True,
                            notes=f"Phase 1 symmetric | side={side} | ev={ev_submitted_cents:.3f}c")
