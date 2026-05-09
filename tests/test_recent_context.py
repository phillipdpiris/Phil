from kalshi_btc15m_bot.strategy.recent_context import (
    build_recent_context_summary, compute_mid_to_close_reversal_rate,
    compute_open_to_mid_continuation_rate, compute_outcome_yes_rate,
)

def test_outcome_yes_rate_uses_resolved_markets_only():
    markets = [{"result": "yes"}, {"result": "no"}, {"result": "yes"}, {"result": "pending"}]
    assert abs(compute_outcome_yes_rate(markets) - 2/3) < 1e-9

def test_path_based_continuation_and_reversal_rates():
    m1 = {"open_price_cents": 50.0, "mid_price_cents": 60.0, "close_price_cents": 70.0}
    m2 = {"open_price_cents": 50.0, "mid_price_cents": 60.0, "close_price_cents": 55.0}
    m3 = {"open_price_cents": 50.0, "mid_price_cents": 40.0, "close_price_cents": 45.0}
    markets = [m1, m2, m3]
    assert abs(compute_open_to_mid_continuation_rate(markets) - 1.0) < 1e-9
    assert abs(compute_mid_to_close_reversal_rate(markets) - 2/3) < 1e-9

def test_recent_context_summary_falls_back_to_neutral_when_no_data():
    summary = build_recent_context_summary([])
    assert summary["outcome_yes_rate"] == 0.5
    assert summary["open_mid_continuation_rate"] == 0.5
    assert summary["mid_close_reversal_rate"] == 0.5
    assert summary["sample_size"] == 0
