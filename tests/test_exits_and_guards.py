from pathlib import Path
from kalshi_btc15m_bot.config import BotConfig
from kalshi_btc15m_bot.execution.exits import build_exit_decision
from kalshi_btc15m_bot.execution.guards import depth_ok, net_edge_ok, spread_ok, time_ok
from kalshi_btc15m_bot.market.orderbook import best_no_bid, best_yes_bid
from kalshi_btc15m_bot.models import BotState, OrderbookLevel, OrderbookState, PositionState

def make_cfg():
    return BotConfig(kalshi_env="demo", api_key_id="", private_key_path="", series_ticker="kxbtc15m",
                     dry_run=True, state_file=Path("state.json"), log_level="INFO", loop_seconds=5,
                     order_size=10, final_minute_order_size=4, max_spread_cents=4.0,
                     min_depth_contracts=5.0, normal_min_edge_cents=3.5, final_minute_min_edge_cents=6.0,
                     slippage_buffer_cents=1.0, coinbase_product="BTC-USD", coinbase_granularity=60,
                     coinbase_candles_count=30)

def make_book_for_yes(price_cents):
    return OrderbookState(yes_bids=[OrderbookLevel(price_cents, 10.0)], no_bids=[])

def make_book_for_no(price_cents):
    return OrderbookState(yes_bids=[], no_bids=[OrderbookLevel(price_cents, 10.0)])

def test_spread_and_depth_guards():
    cfg = make_cfg()
    book_yes = OrderbookState(yes_bids=[OrderbookLevel(40.0, 10.0)], no_bids=[OrderbookLevel(59.0, 10.0)])
    assert spread_ok(book_yes, cfg, side="yes") is True
    assert depth_ok(book_yes, cfg, side="yes") is True
    book_no_wide = OrderbookState(yes_bids=[OrderbookLevel(10.0, 1.0)], no_bids=[OrderbookLevel(30.0, 1.0)])
    assert spread_ok(book_no_wide, cfg, side="no") is False
    assert depth_ok(book_no_wide, cfg, side="no") is False

def test_net_edge_guard_uses_phase_thresholds():
    cfg = make_cfg()
    assert net_edge_ok(3.0, phase="phase2", cfg=cfg) is False
    assert net_edge_ok(3.6, phase="phase2", cfg=cfg) is True
    assert net_edge_ok(5.9, phase="final_minute", cfg=cfg) is False
    assert net_edge_ok(6.0, phase="final_minute", cfg=cfg) is True

def test_time_guard_blocks_late_new_entries_outside_final_minute():
    cfg = make_cfg()
    assert time_ok(phase="phase2", remaining=21, cfg=cfg) is True
    assert time_ok(phase="phase2", remaining=20, cfg=cfg) is False
    assert time_ok(phase="final_minute", remaining=10, cfg=cfg) is True

def test_exit_engine_tp1_and_tp2_reduce_contracts():
    cfg = make_cfg()
    position = PositionState(ticker="TEST-YES", side="yes", contracts=10,
                              avg_entry_price_cents=40.0, entry_time_iso="2024-01-01T00:00:00Z")
    book = make_book_for_yes(46.0)
    decision_tp1 = build_exit_decision(position, book, 600, residual_edge_cents=5.0, cfg=cfg)
    assert decision_tp1.action == "sell_partial"
    assert decision_tp1.reason == "tp1"
    assert decision_tp1.contracts == 5
    position.contracts -= decision_tp1.contracts
    position.tp1_done = True
    decision_tp2 = build_exit_decision(position, book, 600, residual_edge_cents=5.0, cfg=cfg)
    assert decision_tp2.action == "sell_partial"
    assert decision_tp2.reason == "tp2"
    assert decision_tp2.contracts == 2

def test_stop_loss_exits_full_position():
    cfg = make_cfg()
    position = PositionState(ticker="TEST-NO", side="no", contracts=7,
                              avg_entry_price_cents=60.0, entry_time_iso="2024-01-01T00:00:00Z")
    book = make_book_for_no(50.0)
    decision = build_exit_decision(position, book, 600, residual_edge_cents=-5.0, cfg=cfg)
    assert decision.action == "sell_all"
    assert decision.reason == "stop loss"
    assert best_no_bid(book) == 50.0
    assert (best_no_bid(book) - position.avg_entry_price_cents) / position.avg_entry_price_cents <= -0.06
