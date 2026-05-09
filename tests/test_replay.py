from pathlib import Path
from kalshi_btc15m_bot.analytics.replay import compare_exit_variants, load_saved_orderbook_stream, replay_market

def test_load_saved_orderbook_stream_handles_missing_file(tmp_path):
    assert load_saved_orderbook_stream(tmp_path / "missing.jsonl") == []

def test_replay_market_computes_realized_pnl_and_open_positions(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join([
        '{"event_type": "order_submission", "mode": "entry", "dry_run": true, "ticker": "TEST", "phase": "phase2", "payload": {"ticker": "TEST", "side": "yes", "action": "buy", "type": "limit", "count": 10, "yes_price": 40}, "skipped": false, "reason": null}',
        '{"event_type": "exit", "ticker": "TEST", "phase": "phase2", "remaining_seconds": 300, "exit_decision": "tp1", "action": "sell_partial", "contracts": 5, "residual_edge_cents": 1.0, "dry_run": true, "payload": {"ticker": "TEST", "side": "yes", "action": "sell", "type": "limit", "count": 5, "yes_price": 45}, "skipped": false, "reason": null}',
    ]), encoding="utf-8")
    session = load_saved_orderbook_stream(path)
    result = replay_market(session, {"test": True})
    assert result["status"] == "ok"
    assert abs(result["markets"]["TEST"]["realized_pnl_cents"] - 25.0) < 1e-9
    assert result["open_positions"]["TEST"]["contracts"] == 5

def test_compare_exit_variants_wraps_baseline_replay(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_text('{"event_type": "market_snapshot", "ticker": "T", "phase": "phase1", "remaining_seconds": 900}', encoding="utf-8")
    result = compare_exit_variants(load_saved_orderbook_stream(path))
    assert result["status"] == "baseline_only"
    assert "recorded" in result["variants"]
