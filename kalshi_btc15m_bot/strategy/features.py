from __future__ import annotations
import math

def _pct_change(a: float, b: float) -> float:
    return 0.0 if a == 0 else (b - a) / a

def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0

def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = _mean(values)
    return math.sqrt(sum((v - mu) ** 2 for v in values) / (len(values) - 1))

def compute_btc_returns(candles: list[dict]) -> dict:
    closes = [row["close"] for row in candles]
    if len(closes) < 11:
        raise ValueError("Need at least 11 candles")
    return {"ret_1m": _pct_change(closes[-2], closes[-1]), "ret_3m": _pct_change(closes[-4], closes[-1]),
            "ret_5m": _pct_change(closes[-6], closes[-1]), "ret_10m": _pct_change(closes[-11], closes[-1]),
            "last_close": closes[-1]}

def compute_momentum_features(candles: list[dict]) -> dict:
    returns = compute_btc_returns(candles)
    score = (2.2 * math.tanh(returns["ret_1m"] / 0.0015) + 2.8 * math.tanh(returns["ret_3m"] / 0.0035)
             + 3.2 * math.tanh(returns["ret_5m"] / 0.0060) + 1.2 * math.tanh(returns["ret_10m"] / 0.0100))
    returns["momentum_score"] = score
    return returns

def compute_mean_reversion_features(candles: list[dict]) -> dict:
    closes = [row["close"] for row in candles]
    window = closes[-20:] if len(closes) >= 20 else closes
    mu = _mean(window)
    sigma = _std(window)
    zscore_20 = 0.0 if sigma == 0 else (closes[-1] - mu) / sigma
    return {"zscore_20": zscore_20, "meanrev_score": -2.6 * math.tanh(zscore_20 / 1.6)}

def compute_volatility_features(candles: list[dict]) -> dict:
    closes = [row["close"] for row in candles]
    returns = [_pct_change(closes[i - 1], closes[i]) for i in range(1, len(closes))]
    return {"realized_vol": _std(returns) if len(returns) >= 2 else 0.0}

def compute_microstructure_features(book) -> dict:
    from ..market.orderbook import best_yes_bid, best_yes_ask, best_no_bid, best_no_ask, depth_at_best
    return {"best_yes_bid": best_yes_bid(book), "best_yes_ask": best_yes_ask(book),
            "best_no_bid": best_no_bid(book), "best_no_ask": best_no_ask(book),
            "yes_depth": depth_at_best(book, "yes"), "no_depth": depth_at_best(book, "no")}
