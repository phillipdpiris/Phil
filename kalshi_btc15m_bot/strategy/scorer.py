from __future__ import annotations
from ..config import BotConfig
from ..market.fees import estimate_entry_fee, net_edge_cents
from ..market.orderbook import best_no_ask, best_yes_ask, no_spread, yes_spread
from ..models import EntryDecision
from .fair_value import estimate_no_probability, estimate_yes_probability, fair_no_price_cents, fair_yes_price_cents

YES_EDGE_PENALTY_CENTS = 6.0

def combine_scores(features: dict, context: dict, phase: str) -> dict:
    prob_yes = estimate_yes_probability(features, context, phase)
    prob_no = estimate_no_probability(features, context, phase)
    return {"prob_yes": prob_yes, "prob_no": prob_no,
            "fair_yes_cents": fair_yes_price_cents(prob_yes), "fair_no_cents": fair_no_price_cents(prob_no)}

def best_entry_decision(features: dict, context: dict, book, phase: str, cfg: BotConfig) -> EntryDecision:
    scores = combine_scores(features, context, phase)
    yes_price = best_yes_ask(book)
    no_price = best_no_ask(book)
    yes_edge = net_edge_cents(fair_value_cents=scores["fair_yes_cents"], market_price_cents=yes_price,
                              fee_cents=estimate_entry_fee(yes_price, contracts=1),
                              spread_cents=yes_spread(book), slippage_cents=cfg.slippage_buffer_cents)
    no_edge = net_edge_cents(fair_value_cents=scores["fair_no_cents"], market_price_cents=no_price,
                             fee_cents=estimate_entry_fee(no_price, contracts=1),
                             spread_cents=no_spread(book), slippage_cents=cfg.slippage_buffer_cents)
    if yes_edge >= no_edge + YES_EDGE_PENALTY_CENTS:
        side, edge = "yes", yes_edge
    else:
        side, edge = "no", no_edge
    price = yes_price if side == "yes" else no_price
    min_edge = cfg.final_minute_min_edge_cents if phase == "final_minute" else cfg.normal_min_edge_cents
    tradable = edge >= min_edge
    return EntryDecision(
        side=side if tradable else None,
        confidence=max(scores["prob_yes"], scores["prob_no"]),
        fair_value_cents=scores["fair_yes_cents"] if side == "yes" else scores["fair_no_cents"],
        target_entry_price_cents=price, edge_cents=edge, tradable=tradable,
        reason=f"{phase} best-side evaluation",
        order_style="resting_limit" if phase != "final_minute" else "aggressive_limit",
        contracts=cfg.final_minute_order_size if phase == "final_minute" else cfg.order_size,
        fair_yes_cents=scores["fair_yes_cents"], fair_no_cents=scores["fair_no_cents"],
    )
