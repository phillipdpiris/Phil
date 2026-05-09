import math
from dataclasses import dataclass
from typing import Optional

class EVError(ValueError):
    pass

@dataclass
class EVResult:
    p_adj: float
    side: str
    price_cents: float
    p_win: float
    ev_filled_cents: float
    p_fill_adjusted: float
    adverse_selection_penalty_cents: float
    fee_buffer_cents: float
    slippage_buffer_cents: float
    ev_submitted_cents: float
    passes: bool
    min_ev_threshold_cents: float
    fail_reason: Optional[str] = None

def compute_ev(p_adj, side, price_cents, p_fill_adjusted, spread_cents,
              adverse_selection_fraction=0.25, adverse_selection_min_cents=1.0,
              fee_buffer_cents=0.5, slippage_buffer_cents=0.5,
              min_ev_submitted_cents=1.0) -> EVResult:
    for name, val in [("p_adj",p_adj),("price_cents",price_cents),("p_fill_adjusted",p_fill_adjusted),("spread_cents",spread_cents)]:
        if val is None: raise EVError(f"Required EV component '{name}' is None")
        if math.isnan(val) or math.isinf(val): raise EVError(f"'{name}'={val!r} is NaN/inf")
    if side not in ("yes","no"): raise EVError(f"Invalid side={side!r}")
    if not (0.0 <= p_adj <= 1.0): raise EVError(f"p_adj={p_adj} outside [0,1]")
    if not (0.0 <= p_fill_adjusted <= 1.0): raise EVError(f"p_fill_adjusted={p_fill_adjusted} outside [0,1]")
    if price_cents <= 0 or price_cents >= 100: raise EVError(f"price_cents={price_cents} outside (0,100)")
    p_win = p_adj if side == "yes" else 1.0 - p_adj
    ev_filled = p_win*(100.0-price_cents) - (1.0-p_win)*price_cents - fee_buffer_cents
    adv_penalty = max(adverse_selection_min_cents, adverse_selection_fraction*spread_cents)
    ev_submitted = p_fill_adjusted*ev_filled - adv_penalty - slippage_buffer_cents
    passes = ev_submitted >= min_ev_submitted_cents
    fail_reason = None if passes else f"EV_submitted={ev_submitted:.3f}c < min={min_ev_submitted_cents}c (ev_filled={ev_filled:.3f}c, p_fill={p_fill_adjusted:.3f})"
    return EVResult(p_adj=p_adj, side=side, price_cents=price_cents, p_win=p_win,
                    ev_filled_cents=ev_filled, p_fill_adjusted=p_fill_adjusted,
                    adverse_selection_penalty_cents=adv_penalty, fee_buffer_cents=fee_buffer_cents,
                    slippage_buffer_cents=slippage_buffer_cents, ev_submitted_cents=ev_submitted,
                    passes=passes, min_ev_threshold_cents=min_ev_submitted_cents, fail_reason=fail_reason)
