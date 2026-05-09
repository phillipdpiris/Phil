from __future__ import annotations


def daily_pnl_report(trades: list[dict]) -> dict:
    realized = [trade.get("pnl_cents", 0.0) or 0.0 for trade in trades]
    return {"trade_count": len(trades), "realized_pnl_cents": sum(realized)}


def strategy_attribution_report(trades: list[dict]) -> dict:
    buckets: dict[str, int] = {}
    for trade in trades:
        key = trade.get("strategy_bucket", "unknown")
        buckets[key] = buckets.get(key, 0) + 1
    return buckets


def late_exit_giveback_report(trades: list[dict]) -> dict:
    return {"status": "not_implemented", "trade_count": len(trades)}
