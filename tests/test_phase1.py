import json, math, os, tempfile, time
import pytest
from kalshi_btc15m_bot.strategy.probability_adjuster import apply_shrinkage, ProbabilityError
from kalshi_btc15m_bot.strategy.latency_engine import adjust_probability_for_latency, adjust_fill_probability_for_latency, LatencyError
from kalshi_btc15m_bot.strategy.fill_model import estimate_fill_probability_base, FillModelError
from kalshi_btc15m_bot.strategy.ev_engine import compute_ev, EVError
from kalshi_btc15m_bot.risk.clustering_engine import check_clustering, ClusteringConfig, OpenPosition, RecentTrade
from kalshi_btc15m_bot.analytics.lifecycle_logger import LifecycleLogger
from kalshi_btc15m_bot.execution.guard_router import GuardRouter, GuardContext

class TestProbabilityAdjuster:
    def test_shrinkage_070(self):
        r = apply_shrinkage(0.70, shrinkage_factor=0.70)
        assert math.isclose(r.p_shrunk, 0.64, rel_tol=1e-6)
    def test_symmetric(self):
        r = apply_shrinkage(0.30, shrinkage_factor=0.70)
        assert math.isclose(r.p_shrunk, 0.36, rel_tol=1e-6)
    def test_fifty_unchanged(self):
        assert math.isclose(apply_shrinkage(0.50).p_shrunk, 0.50, rel_tol=1e-9)
    def test_returns_raw_and_factor(self):
        r = apply_shrinkage(0.80, shrinkage_factor=0.70)
        assert r.p_raw == 0.80 and r.shrinkage_factor == 0.70
    def test_invalid_none_raises(self):
        with pytest.raises(ProbabilityError): apply_shrinkage(None)
    def test_invalid_nan_raises(self):
        with pytest.raises(ProbabilityError): apply_shrinkage(float("nan"))
    def test_invalid_inf_raises(self):
        with pytest.raises(ProbabilityError): apply_shrinkage(float("inf"))
    def test_out_of_range_above_raises(self):
        with pytest.raises(ProbabilityError): apply_shrinkage(1.01)
    def test_out_of_range_below_raises(self):
        with pytest.raises(ProbabilityError): apply_shrinkage(-0.01)
    def test_boundary_values(self):
        r0 = apply_shrinkage(0.0); assert r0.p_shrunk == pytest.approx(0.5-0.5*0.70)
        r1 = apply_shrinkage(1.0); assert r1.p_shrunk == pytest.approx(0.5+0.5*0.70)

class TestLatencyEngine:
    def test_decays_toward_half(self):
        r0 = adjust_probability_for_latency(0.70, 0, 300)
        r60 = adjust_probability_for_latency(0.70, 60, 300)
        assert r60.p_latency < r0.p_latency and r60.p_latency > 0.5
    def test_zero_latency_preserves(self):
        assert math.isclose(adjust_probability_for_latency(0.70, 0, 300).p_latency, 0.70, rel_tol=1e-6)
    def test_large_latency_approaches_half(self):
        assert abs(adjust_probability_for_latency(0.90, 10000, 60).p_latency - 0.5) < 0.01
    def test_below_half_decays_from_below(self):
        r60 = adjust_probability_for_latency(0.30, 60, 300)
        assert r60.p_latency > 0.30 and r60.p_latency < 0.5
    def test_tau_floor_applied(self):
        r = adjust_probability_for_latency(0.70, 30, 10, tau_floor_seconds=60)
        r_direct = adjust_probability_for_latency(0.70, 30, 60, tau_floor_seconds=60)
        assert math.isclose(r.p_latency, r_direct.p_latency, rel_tol=1e-9)
    def test_fill_decreases_with_latency(self):
        assert adjust_fill_probability_for_latency(0.80, 5).p_fill_adjusted < adjust_fill_probability_for_latency(0.80, 0).p_fill_adjusted
    def test_fill_no_latency(self):
        assert math.isclose(adjust_fill_probability_for_latency(0.85, 0).p_fill_adjusted, 0.85, rel_tol=1e-9)
    def test_fill_always_nonnegative(self):
        assert adjust_fill_probability_for_latency(0.50, 1000).p_fill_adjusted >= 0.0
    def test_invalid_nan_prob_raises(self):
        with pytest.raises(LatencyError): adjust_probability_for_latency(float("nan"), 0, 300)
    def test_invalid_negative_dt_raises(self):
        with pytest.raises(LatencyError): adjust_probability_for_latency(0.70, -1, 300)

class TestFillModel:
    def test_near_ask_high_fill(self):
        r = estimate_fill_probability_base(52, 48, 52)
        assert r.p_fill_base == pytest.approx(0.85) and r.reason == "near_ask_aggressive"
    def test_near_bid_low_fill(self):
        r = estimate_fill_probability_base(48, 48, 52)
        assert r.p_fill_base == pytest.approx(0.25) and r.reason == "near_bid_passive"
    def test_inside_spread_mid_fill(self):
        r = estimate_fill_probability_base(50, 48, 52)
        assert r.p_fill_base == pytest.approx(0.50) and r.reason == "inside_spread"
    def test_missing_bid_raises(self):
        with pytest.raises(FillModelError): estimate_fill_probability_base(50, None, 52)
    def test_inverted_book_raises(self):
        with pytest.raises(FillModelError): estimate_fill_probability_base(50, 55, 50)
    def test_nan_price_raises(self):
        with pytest.raises(FillModelError): estimate_fill_probability_base(float("nan"), 48, 52)

class TestEVEngine:
    def test_yes_ev_positive(self):
        r = compute_ev(p_adj=0.70, side="yes", price_cents=50, p_fill_adjusted=0.80, spread_cents=4)
        assert r.passes and r.ev_submitted_cents > 0
    def test_no_ev_positive(self):
        r = compute_ev(p_adj=0.30, side="no", price_cents=50, p_fill_adjusted=0.80, spread_cents=4)
        assert r.passes and r.ev_submitted_cents > 0
    def test_negative_ev_blocked(self):
        r = compute_ev(p_adj=0.50, side="yes", price_cents=50, p_fill_adjusted=0.80, spread_cents=4)
        assert not r.passes and r.fail_reason is not None
    def test_fees_reduce_ev(self):
        r_no = compute_ev(0.70,"yes",50,1.0,0.1,fee_buffer_cents=0,slippage_buffer_cents=0,adverse_selection_min_cents=0)
        r_fee = compute_ev(0.70,"yes",50,1.0,0.1,fee_buffer_cents=2.0,slippage_buffer_cents=1.0,adverse_selection_min_cents=1.0)
        assert r_fee.ev_submitted_cents < r_no.ev_submitted_cents
    def test_missing_p_adj_raises(self):
        with pytest.raises(EVError): compute_ev(None,"yes",50,0.80,4)
    def test_invalid_side_raises(self):
        with pytest.raises(EVError): compute_ev(0.70,"invalid",50,0.80,4)

class TestClusteringEngine:
    def _now(self): return time.time() * 1000.0
    def test_allows_clean_trade(self):
        assert check_clustering("yes",95000.0,500,[],[],ClusteringConfig()).allowed
    def test_blocks_rate_limit(self):
        r = check_clustering("yes",95000.0,500,[],[RecentTrade("yes",self._now()-60_000)],ClusteringConfig())
        assert not r.allowed and r.skip_reason=="CLUSTERING_RATE_LIMIT"
    def test_blocks_same_side_open_limit(self):
        pos = [OpenPosition("A","yes",94000.0,500,0),OpenPosition("B","yes",96000.0,500,0),OpenPosition("C","yes",97000.0,500,0)]
        r = check_clustering("yes",95000.0,500,pos,[],ClusteringConfig())
        assert not r.allowed and r.skip_reason=="CLUSTERING_SAME_SIDE_LIMIT"
    def test_blocks_total_open_limit(self):
        pos = [OpenPosition(str(i),"yes",90000.0+i*1000,500,0) for i in range(5)]
        r = check_clustering("no",95000.0,500,pos,[],ClusteringConfig())
        assert not r.allowed and r.skip_reason=="CLUSTERING_TOTAL_POSITION_LIMIT"
    def test_blocks_strike_too_close(self):
        r = check_clustering("yes",95475.0,500,[OpenPosition("A","yes",95000.0,500,0)],[],ClusteringConfig())
        assert not r.allowed and r.skip_reason=="CLUSTERING_STRIKE_TOO_CLOSE"
    def test_blocks_notional_side_limit(self):
        r = check_clustering("yes",95000.0,600,[OpenPosition("A","yes",90000.0,2000,0)],[],ClusteringConfig())
        assert not r.allowed and r.skip_reason=="CLUSTERING_NOTIONAL_SIDE_LIMIT"
    def test_blocks_total_notional_limit(self):
        cfg = ClusteringConfig(max_notional_per_side_cents=9999, max_total_open_notional_cents=5000)
        pos = [OpenPosition("A","yes",90000.0,2500,0),OpenPosition("B","no",91000.0,2000,0)]
        r = check_clustering("no",95000.0,600,pos,[],cfg)
        assert not r.allowed and r.skip_reason=="CLUSTERING_TOTAL_NOTIONAL_LIMIT"

class TestLifecycleLogger:
    def _make(self, tmp_path):
        log_file = str(tmp_path / "test_events.jsonl")
        return LifecycleLogger(log_file=log_file), log_file
    def _read(self, lf):
        with open(lf) as f: return [json.loads(l) for l in f if l.strip()]
    def test_log_signal_writes_jsonl(self, tmp_path):
        logger, lf = self._make(tmp_path)
        logger.log_signal(correlation_id="c1",market_ticker="T",event_ticker="E",strike=95000.0,
            expiry="2026-05-06T14:00:00Z",side="yes",minutes_to_expiry=7.5,spot_at_signal=94900.0,
            reference_source="coinbase",best_yes_bid=48.0,best_yes_ask=52.0,best_no_bid=48.0,
            best_no_ask=52.0,spread_cents=4.0,depth_bid=100.0,depth_ask=100.0,
            book_timestamp="2026-05-06T13:52:30Z",p_raw=0.62)
        e = self._read(lf)[0]
        assert e["event_type"]=="signal_generated" and e["p_raw"]==0.62 and "event_id" in e
    def test_log_skip_reason(self, tmp_path):
        logger, lf = self._make(tmp_path)
        logger.log_skip(correlation_id="c2",skip_reason="SPREAD_TOO_WIDE",spread_ok=False)
        e = self._read(lf)[0]
        assert e["skip_reason"]=="SPREAD_TOO_WIDE" and e["event_type"]=="trade_skipped"
    def test_no_secrets_logged(self, tmp_path):
        logger, lf = self._make(tmp_path)
        logger.log_error(exception_type="AuthError",exception_message="fail",extra={"api_key":"SECRET","other":"ok"})
        e = self._read(lf)[0]
        assert e.get("api_key")=="[REDACTED]" and e.get("other")=="ok"
    def test_invalid_event_type_raises(self, tmp_path):
        logger, lf = self._make(tmp_path)
        with pytest.raises(ValueError): logger._base_fields("invalid_xyz")
    def test_log_creates_directory(self, tmp_path):
        nested = str(tmp_path/"a"/"b"/"c"/"events.jsonl")
        LifecycleLogger(log_file=nested).log_error(exception_type="T",exception_message="t")
        assert os.path.exists(nested)

class TestGuardRouter:
    def _ctx(self, **ov):
        now = time.time() * 1000.0
        d = dict(best_yes_bid=48.0,best_yes_ask=52.0,best_no_bid=48.0,best_no_ask=52.0,
            spread_cents=4.0,depth_bid=50.0,depth_ask=50.0,book_timestamp_ms=now-500,
            signal_timestamp_ms=now-1000,current_timestamp_ms=now,minutes_to_expiry=5.0,
            limit_price_cents=50.0,max_spread_cents=6.0,min_depth=10.0,min_price_cents=1.0,
            max_price_cents=99.0,max_book_age_seconds=2.0,max_signal_age_seconds=5.0,tau_floor_seconds=60.0)
        d.update(ov); return GuardContext(**d)
    def test_all_pass(self):
        assert GuardRouter().check(self._ctx()).passed
    def test_stale_signal(self):
        now = time.time()*1000.0; r = GuardRouter().check(self._ctx(signal_timestamp_ms=now-10_000,current_timestamp_ms=now,max_signal_age_seconds=5.0))
        assert not r.passed and r.skip_reason=="STALE_SIGNAL"
    def test_stale_book(self):
        now = time.time()*1000.0; r = GuardRouter().check(self._ctx(book_timestamp_ms=now-5000,current_timestamp_ms=now,max_book_age_seconds=2.0))
        assert not r.passed and r.skip_reason=="STALE_ORDERBOOK"
    def test_spread_too_wide(self):
        r = GuardRouter().check(self._ctx(spread_cents=10.0,max_spread_cents=5.0))
        assert not r.passed and r.skip_reason=="SPREAD_TOO_WIDE"
    def test_insufficient_depth(self):
        r = GuardRouter().check(self._ctx(depth_bid=5.0,depth_ask=50.0,min_depth=10.0))
        assert not r.passed and r.skip_reason=="INSUFFICIENT_DEPTH"
    def test_time_guard(self):
        r = GuardRouter().check(self._ctx(minutes_to_expiry=0.5,tau_floor_seconds=60))
        assert not r.passed and r.skip_reason=="TIME_GUARD_BLOCKED"
    def test_invalid_price(self):
        r = GuardRouter().check(self._ctx(limit_price_cents=0.5,min_price_cents=1.0))
        assert not r.passed and r.skip_reason=="INVALID_PRICE"
