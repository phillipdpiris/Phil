import json, os, tempfile, time
from pathlib import Path
import pytest
from kalshi_btc15m_bot.app import Phase1Pipeline, SignalContext, StubKalshiClient, StubSpotSource, DryRunEnforcementError
from kalshi_btc15m_bot.analytics.lifecycle_logger import LifecycleLogger
from kalshi_btc15m_bot.execution.order_mapper import map_intent_to_v2_payload, payload_to_dict, OrderMappingError
from kalshi_btc15m_bot.strategy.strategy_router import route

def make_pipeline(tmp_path, fill_always=True, spot_price=94900.0):
    log_file = str(tmp_path / "events.jsonl")
    logger = LifecycleLogger(log_file=log_file)
    client = StubKalshiClient(fill_always=fill_always)
    spot_source = StubSpotSource(price=spot_price)
    pipeline = Phase1Pipeline(logger=logger, client=client, spot_source=spot_source)
    return pipeline, log_file

def read_events(log_file):
    with open(log_file) as f: return [json.loads(l) for l in f if l.strip()]

def good_signal(**overrides):
    now_ms = time.time() * 1000.0
    defaults = dict(correlation_id="test-corr-001", market_ticker="KXBTC-25050614-T95000",
        event_ticker="KXBTC-25050614", strike=95000.0, expiry="2026-05-06T14:00:00Z",
        side="yes", minutes_to_expiry=7.0, spot_at_signal=94900.0, reference_source="coinbase_ticker",
        best_yes_bid=46.0, best_yes_ask=50.0, best_no_bid=50.0, best_no_ask=54.0,
        spread_cents=4.0, depth_bid=80.0, depth_ask=80.0, book_timestamp="2026-05-06T13:53:00Z",
        book_timestamp_ms=now_ms-500, signal_timestamp_ms=now_ms-1000, current_timestamp_ms=now_ms,
        p_raw=0.72, limit_price_cents=48.0, requested_count=5)
    defaults.update(overrides)
    return SignalContext(**defaults)

class TestAllowedPath:
    def test_allowed_signal_produces_filled_outcome(self, tmp_path):
        pipeline, log_file = make_pipeline(tmp_path)
        assert pipeline.process_signal(good_signal())["outcome"] == "filled"

    def test_allowed_signal_produces_jsonl_events(self, tmp_path):
        pipeline, log_file = make_pipeline(tmp_path)
        pipeline.process_signal(good_signal())
        types = [e["event_type"] for e in read_events(log_file)]
        for t in ["signal_generated","order_prepared","order_submitted","order_filled"]:
            assert t in types

    def test_all_events_have_schema_version_and_correlation_id(self, tmp_path):
        pipeline, log_file = make_pipeline(tmp_path)
        pipeline.process_signal(good_signal(correlation_id="corr-xyz"))
        for e in read_events(log_file):
            assert e.get("schema_version") == "1.0"
            assert e.get("correlation_id") == "corr-xyz"

    def test_order_prepared_logs_all_ev_components(self, tmp_path):
        pipeline, log_file = make_pipeline(tmp_path)
        pipeline.process_signal(good_signal())
        prepared = next(e for e in read_events(log_file) if e["event_type"]=="order_prepared")
        for f in ["p_raw","p_shrunk","p_latency","p_fill_base","p_fill_adjusted",
                  "ev_filled_cents","ev_submitted_cents","adverse_selection_penalty","fees_estimated","slippage_buffer"]:
            assert f in prepared

    def test_no_live_client_calls(self, tmp_path):
        pipeline, log_file = make_pipeline(tmp_path)
        pipeline.process_signal(good_signal())
        assert len(pipeline.client.submitted_orders) == 1
        assert pipeline.client.submitted_orders[0]["ticker"] == "KXBTC-25050614-T95000"

class TestGuardFailurePaths:
    def test_stale_signal_skips_with_correct_reason(self, tmp_path):
        pipeline, log_file = make_pipeline(tmp_path)
        now = time.time() * 1000.0
        result = pipeline.process_signal(good_signal(signal_timestamp_ms=now-10_000, current_timestamp_ms=now))
        assert result["outcome"] == "skipped"
        assert result["skip_reason"] == "STALE_SIGNAL"

    def test_stale_book_skips_with_correct_reason(self, tmp_path):
        pipeline, log_file = make_pipeline(tmp_path)
        now = time.time() * 1000.0
        result = pipeline.process_signal(good_signal(book_timestamp_ms=now-5000, current_timestamp_ms=now))
        assert result["outcome"] == "skipped"
        assert result["skip_reason"] == "STALE_ORDERBOOK"

    def test_wide_spread_skips_before_ev(self, tmp_path):
        pipeline, log_file = make_pipeline(tmp_path)
        result = pipeline.process_signal(good_signal(spread_cents=15.0))
        assert result["outcome"] == "skipped"
        assert result["skip_reason"] == "SPREAD_TOO_WIDE"
        assert not any(e["event_type"]=="order_prepared" for e in read_events(log_file))

    def test_near_expiry_skips(self, tmp_path):
        pipeline, log_file = make_pipeline(tmp_path)
        result = pipeline.process_signal(good_signal(minutes_to_expiry=0.5))
        assert result["outcome"] == "skipped"
        assert result["skip_reason"] == "TIME_GUARD_BLOCKED"

    def test_guard_skip_never_calls_client(self, tmp_path):
        pipeline, log_file = make_pipeline(tmp_path)
        pipeline.process_signal(good_signal(spread_cents=20.0))
        assert len(pipeline.client.submitted_orders) == 0

class TestClusteringFailurePaths:
    def test_rate_limit_skips_with_correct_reason(self, tmp_path):
        from kalshi_btc15m_bot.risk.clustering_engine import RecentTrade
        pipeline, log_file = make_pipeline(tmp_path)
        pipeline.recent_trades = [RecentTrade(side="yes", opened_at_ms=time.time()*1000.0-60_000)]
        result = pipeline.process_signal(good_signal())
        assert result["outcome"] == "skipped"
        assert result["skip_reason"] == "CLUSTERING_RATE_LIMIT"

class TestEVFailurePaths:
    def test_low_probability_ev_negative_skips(self, tmp_path):
        pipeline, log_file = make_pipeline(tmp_path)
        result = pipeline.process_signal(good_signal(p_raw=0.50))
        assert result["outcome"] == "skipped"
        assert result["skip_reason"] == "EV_BELOW_THRESHOLD"

    def test_ev_skip_never_calls_client(self, tmp_path):
        pipeline, log_file = make_pipeline(tmp_path)
        pipeline.process_signal(good_signal(p_raw=0.50))
        assert len(pipeline.client.submitted_orders) == 0

class TestNoSidePath:
    def test_no_side_allowed_path(self, tmp_path):
        pipeline, log_file = make_pipeline(tmp_path)
        result = pipeline.process_signal(good_signal(side="no", p_raw=0.25, limit_price_cents=48.0))
        assert result["outcome"] == "filled"
        order = pipeline.client.submitted_orders[0]
        assert order["side"] == "no"
        assert "no_price" in order

class TestOrderMapper:
    def test_yes_payload_has_yes_price(self):
        d = payload_to_dict(map_intent_to_v2_payload("TICKER","yes",50.0,5))
        assert d["yes_price"]==50 and "no_price" not in d and d["side"]=="yes"

    def test_no_payload_has_no_price(self):
        d = payload_to_dict(map_intent_to_v2_payload("TICKER","no",48.0,3))
        assert d["no_price"]==48 and "yes_price" not in d

    def test_invalid_price_below_min_raises(self):
        with pytest.raises(OrderMappingError): map_intent_to_v2_payload("TICKER","yes",0.5,5)

    def test_invalid_price_above_max_raises(self):
        with pytest.raises(OrderMappingError): map_intent_to_v2_payload("TICKER","yes",99.5,5)

    def test_zero_count_raises(self):
        with pytest.raises(OrderMappingError): map_intent_to_v2_payload("TICKER","yes",50.0,0)

    def test_invalid_side_raises(self):
        with pytest.raises(OrderMappingError): map_intent_to_v2_payload("TICKER","maybe",50.0,5)

class TestStrategyRouter:
    def test_yes_allowed_when_ev_positive(self):
        d = route("yes",0.65,7.0,ev_submitted_cents=2.5)
        assert d.should_trade and d.strategy_name=="symmetric_phase1"

    def test_no_allowed_when_ev_positive(self):
        d = route("no",0.35,7.0,ev_submitted_cents=2.5)
        assert d.should_trade and d.side=="no"

    def test_blocked_when_ev_below_threshold(self):
        d = route("yes",0.55,7.0,ev_submitted_cents=0.5,min_ev_cents=1.0)
        assert not d.should_trade and d.skip_reason=="EV_BELOW_THRESHOLD"

    def test_invalid_side_blocked(self):
        d = route("unknown",0.65,7.0,ev_submitted_cents=2.5)
        assert not d.should_trade and d.skip_reason=="INVALID_SIDE"

class TestSpotPriceSource:
    def test_stub_spot_returns_configured_price(self):
        assert StubSpotSource(price=94321.0).get_spot() == 94321.0

    def test_spot_at_submit_logged_from_source(self, tmp_path):
        pipeline, log_file = make_pipeline(tmp_path, spot_price=94567.0)
        pipeline.process_signal(good_signal())
        submitted = next(e for e in read_events(log_file) if e["event_type"]=="order_submitted")
        assert submitted["spot_at_submit"] == 94567.0

    def test_dry_run_false_raises_enforcement_error(self, tmp_path):
        log_file = str(tmp_path / "events.jsonl")
        logger = LifecycleLogger(log_file=log_file)
        with pytest.raises(DryRunEnforcementError):
            Phase1Pipeline(logger=logger, client=StubKalshiClient(), dry_run=False)

class TestCLISmokeRunner:
    def test_run_smoke_test_returns_all_6_scenarios(self, tmp_path):
        from kalshi_btc15m_bot.app import run_smoke_test
        log_file = str(tmp_path / "smoke.jsonl")
        results = run_smoke_test(log_file=log_file)
        assert set(results.keys()) == {"allowed_yes","guard_fail_spread","stale_signal","cluster_rate_limit","ev_fail","allowed_no"}
        assert results["allowed_yes"]["outcome"] == "filled"
        assert results["allowed_no"]["outcome"] == "filled"
        for k in ["guard_fail_spread","stale_signal","cluster_rate_limit","ev_fail"]:
            assert results[k]["outcome"] == "skipped"

    def test_run_smoke_test_writes_valid_jsonl(self, tmp_path):
        from kalshi_btc15m_bot.app import run_smoke_test
        log_file = str(tmp_path / "smoke.jsonl")
        run_smoke_test(log_file=log_file)
        with open(log_file) as f:
            lines = [l for l in f if l.strip()]
        assert len(lines) >= 6
        for line in lines:
            assert json.loads(line)["dry_run"] is True

class TestSmokeTest:
    def test_smoke_all_scenarios(self, tmp_path):
        from kalshi_btc15m_bot.risk.clustering_engine import RecentTrade
        pipeline, log_file = make_pipeline(tmp_path)
        now_ms = time.time() * 1000.0
        results = {}
        results["allowed_yes"] = pipeline.process_signal(good_signal(correlation_id="smoke-yes", p_raw=0.72))
        results["guard_fail"] = pipeline.process_signal(good_signal(correlation_id="smoke-guard", spread_cents=15.0))
        pipeline.recent_trades = [RecentTrade(side="no", opened_at_ms=now_ms-30_000)]
        results["cluster_fail"] = pipeline.process_signal(good_signal(correlation_id="smoke-cluster", side="no", p_raw=0.25))
        pipeline.recent_trades = []
        results["ev_fail"] = pipeline.process_signal(good_signal(correlation_id="smoke-ev", p_raw=0.50))
        results["stale_signal"] = pipeline.process_signal(good_signal(correlation_id="smoke-stale", signal_timestamp_ms=now_ms-10_000, current_timestamp_ms=now_ms))
        results["allowed_no"] = pipeline.process_signal(good_signal(correlation_id="smoke-no", side="no", p_raw=0.25))
        assert results["allowed_yes"]["outcome"] == "filled"
        assert results["guard_fail"]["skip_reason"] == "SPREAD_TOO_WIDE"
        assert results["cluster_fail"]["skip_reason"] == "CLUSTERING_RATE_LIMIT"
        assert results["ev_fail"]["skip_reason"] == "EV_BELOW_THRESHOLD"
        assert results["stale_signal"]["skip_reason"] == "STALE_SIGNAL"
        assert results["allowed_no"]["outcome"] == "filled"
        assert len(pipeline.client.submitted_orders) == 2
