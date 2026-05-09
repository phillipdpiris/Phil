import logging
from pathlib import Path
from kalshi_btc15m_bot.config import BotConfig
from kalshi_btc15m_bot.models import BotState, PositionState
from kalshi_btc15m_bot.portfolio import reconcile_position_state

class _FakeRest:
    def __init__(self, cfg, payload):
        self.cfg = cfg
        self._payload = payload
    def auth_get(self, path, params=None, timeout=15):
        assert path == "/portfolio/positions"
        return self._payload

def _make_cfg(kalshi_env="prod", dry_run=False):
    return BotConfig(kalshi_env=kalshi_env, api_key_id="dummy", private_key_path="/dev/null",
                     series_ticker="kxbtc15m", dry_run=dry_run, state_file=Path("state.json"),
                     log_level="INFO", loop_seconds=5, order_size=10, final_minute_order_size=4,
                     max_spread_cents=4.0, min_depth_contracts=5.0, normal_min_edge_cents=3.5,
                     final_minute_min_edge_cents=6.0, slippage_buffer_cents=1.0,
                     coinbase_product="BTC-USD", coinbase_granularity=60, coinbase_candles_count=30)

def test_reconcile_skips_in_demo_or_dry_run():
    cfg = _make_cfg(kalshi_env="demo", dry_run=True)
    assert reconcile_position_state(_FakeRest(cfg, {}), BotState(), ticker="T", logger=logging.getLogger("t")) is True

def test_reconcile_ok_when_both_flat():
    cfg = _make_cfg()
    ok = reconcile_position_state(_FakeRest(cfg, {"market_positions": []}), BotState(), ticker="T", logger=logging.getLogger("t"))
    assert ok is True

def test_reconcile_blocks_when_remote_only_position():
    cfg = _make_cfg()
    state = BotState(position=None)
    ok = reconcile_position_state(_FakeRest(cfg, {"market_positions": [{"ticker": "T", "position": 7}]}), state, ticker="T", logger=logging.getLogger("t"))
    assert ok is False
    assert state.metadata["reconciliation"]["status"] == "mismatch_remote_only"

def test_reconcile_blocks_when_local_only_position():
    cfg = _make_cfg()
    state = BotState(position=PositionState(ticker="T", side="yes", contracts=5, avg_entry_price_cents=40.0, entry_time_iso="2024-01-01T00:00:00Z"))
    ok = reconcile_position_state(_FakeRest(cfg, {"market_positions": []}), state, ticker="T", logger=logging.getLogger("t"))
    assert ok is False
    assert state.metadata["reconciliation"]["status"] == "mismatch_local_only"

def test_reconcile_ok_when_positions_match():
    cfg = _make_cfg()
    state = BotState(position=PositionState(ticker="T", side="yes", contracts=3, avg_entry_price_cents=42.0, entry_time_iso="2024-01-01T00:00:00Z"))
    ok = reconcile_position_state(_FakeRest(cfg, {"market_positions": [{"ticker": "T", "position": 3}]}), state, ticker="T", logger=logging.getLogger("t"))
    assert ok is True

def test_reconcile_blocks_when_both_nonzero_but_differ():
    cfg = _make_cfg()
    state = BotState(position=PositionState(ticker="T", side="yes", contracts=4, avg_entry_price_cents=42.0, entry_time_iso="2024-01-01T00:00:00Z"))
    ok = reconcile_position_state(_FakeRest(cfg, {"market_positions": [{"ticker": "T", "position": -4}]}), state, ticker="T", logger=logging.getLogger("t"))
    assert ok is False
    assert state.metadata["reconciliation"]["status"] == "mismatch_both"
