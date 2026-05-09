from pathlib import Path
from kalshi_btc15m_bot.config import BotConfig
from kalshi_btc15m_bot.models import OrderbookLevel, OrderbookState
from kalshi_btc15m_bot.strategy.scorer import best_entry_decision

def make_cfg():
    return BotConfig(kalshi_env="demo", api_key_id="", private_key_path="", series_ticker="kxbtc15m",
                     dry_run=True, state_file=Path("state.json"), log_level="INFO", loop_seconds=5,
                     order_size=10, final_minute_order_size=4, max_spread_cents=4.0,
                     min_depth_contracts=5.0, normal_min_edge_cents=3.5, final_minute_min_edge_cents=6.0,
                     slippage_buffer_cents=1.0, coinbase_product="BTC-USD", coinbase_granularity=60,
                     coinbase_candles_count=30)

def make_book():
    return OrderbookState(yes_bids=[OrderbookLevel(40.0,10),OrderbookLevel(42.0,10)],
                          no_bids=[OrderbookLevel(55.0,10),OrderbookLevel(57.0,10)])

def test_scoring_returns_decision_object():
    decision = best_entry_decision(
        {"momentum_score":0.7,"meanrev_score":-0.1,"realized_vol":0.001,"ret_1m":0.001,"ret_3m":0.002},
        {"open_mid_continuation_rate":0.55,"mid_close_reversal_rate":0.45,"outcome_yes_rate":0.52},
        make_book(), "phase1", make_cfg())
    assert hasattr(decision, "edge_cents")
    assert 0.0 <= decision.fair_yes_cents <= 100.0
    assert 0.0 <= decision.fair_no_cents <= 100.0

def test_no_entry_when_edge_below_threshold():
    cfg = make_cfg()
    decision = best_entry_decision(
        {"momentum_score":0.0,"meanrev_score":0.0,"realized_vol":0.001,"ret_1m":0.0,"ret_3m":0.0},
        {"open_mid_continuation_rate":0.5,"mid_close_reversal_rate":0.5,"outcome_yes_rate":0.5},
        make_book(), "phase2", cfg)
    assert decision.tradable is False
    assert decision.side is None
    assert decision.edge_cents < cfg.normal_min_edge_cents

def test_final_minute_stays_flat_on_negative_edge():
    cfg = make_cfg()
    decision = best_entry_decision(
        {"momentum_score":-1.5,"meanrev_score":0.0,"realized_vol":0.001,"ret_1m":0.0,"ret_3m":0.0},
        {"open_mid_continuation_rate":0.5,"mid_close_reversal_rate":0.5,"outcome_yes_rate":0.5},
        make_book(), "final_minute", cfg)
    assert decision.tradable is False
    assert decision.side is None
    assert decision.edge_cents < 0.0
