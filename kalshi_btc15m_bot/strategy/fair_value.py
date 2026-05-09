from __future__ import annotations
import math

def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))

def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))

def estimate_yes_probability(features: dict, context: dict, phase: str) -> float:
    continuation_bias = context.get("open_mid_continuation_rate", 0.5) - 0.5
    reversal_bias = context.get("mid_close_reversal_rate", 0.5) - 0.5
    outcome_bias = context.get("outcome_yes_rate", 0.5) - 0.5
    momentum = features.get("momentum_score", 0.0)
    meanrev = features.get("meanrev_score", 0.0)
    vol = max(0.0005, features.get("realized_vol", 0.001))
    ret_1m = features.get("ret_1m", 0.0)
    ret_3m = features.get("ret_3m", 0.0)
    momentum_yes = _sigmoid(momentum + continuation_bias * 1.3 - reversal_bias * 0.7 + outcome_bias * 0.15)
    meanrev_yes = _sigmoid(meanrev + reversal_bias * 1.2 - continuation_bias * 0.8 - outcome_bias * 0.10)
    spot_yes = _sigmoid((ret_3m + 0.75 * ret_1m) / (vol * 3.0) + outcome_bias * 0.2)
    if phase == "phase1":
        return _clamp(0.58 * momentum_yes + 0.22 * meanrev_yes + 0.20 * spot_yes, 0.01, 0.99)
    if phase == "phase2":
        return _clamp(0.60 * spot_yes + 0.25 * momentum_yes + 0.15 * meanrev_yes, 0.01, 0.99)
    if phase == "phase3":
        return _clamp(0.55 * spot_yes + 0.20 * momentum_yes + 0.10 * meanrev_yes + 0.15 * (0.5 + continuation_bias), 0.01, 0.99)
    return _clamp(0.60 * spot_yes + 0.25 * momentum_yes + 0.15 * (0.5 - reversal_bias), 0.01, 0.99)

def estimate_no_probability(features: dict, context: dict, phase: str) -> float:
    return 1.0 - estimate_yes_probability(features, context, phase)

def fair_yes_price_cents(prob_yes: float) -> float:
    return _clamp(prob_yes, 0.0, 1.0) * 100.0

def fair_no_price_cents(prob_no: float) -> float:
    return _clamp(prob_no, 0.0, 1.0) * 100.0

def mispricing_yes(fair_yes: float, market_yes: float) -> float:
    return fair_yes - market_yes

def mispricing_no(fair_no: float, market_no: float) -> float:
    return fair_no - market_no
