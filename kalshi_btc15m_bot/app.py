"""app.py - Phase 1 Canonical Dry-Run Orchestrator. See v11 zip for full source."""
import signal, time, uuid
from dataclasses import dataclass, field
from typing import List, Optional
from kalshi_btc15m_bot.analytics.lifecycle_logger import LifecycleLogger
from kalshi_btc15m_bot.execution.guard_router import GuardRouter, GuardContext
from kalshi_btc15m_bot.execution.order_mapper import map_intent_to_v2_payload, payload_to_dict, OrderMappingError
from kalshi_btc15m_bot.risk.clustering_engine import check_clustering, ClusteringConfig, OpenPosition, RecentTrade
from kalshi_btc15m_bot.strategy.ev_engine import compute_ev, EVError
from kalshi_btc15m_bot.strategy.fill_model import estimate_fill_probability_base, FillModelError
from kalshi_btc15m_bot.strategy.latency_engine import adjust_probability_for_latency, adjust_fill_probability_for_latency
from kalshi_btc15m_bot.strategy.probability_adjuster import apply_shrinkage, ProbabilityError
from kalshi_btc15m_bot.strategy.strategy_router import route

class SpotPriceSource:
    reference_source: str = "unknown"
    def get_spot(self) -> float: raise NotImplementedError

class CoinbaseSpotSource(SpotPriceSource):
    reference_source = "coinbase_ticker"
    def __init__(self, product="BTC-USD"):
        from kalshi_btc15m_bot.clients.coinbase_spot import CoinbaseSpotClient
        self._client = CoinbaseSpotClient(); self._product = product
    def get_spot(self): return self._client.get_last_trade(self._product)["price"]
    def get_spot_with_metadata(self):
        r = self._client.get_last_trade(self._product)
        return {"coinbase_ticker_price": r["price"], "bid": r.get("bid"), "ask": r.get("ask"),
                "ticker_timestamp": r.get("time"), "reference_source": "coinbase_ticker"}

class StubSpotSource(SpotPriceSource):
    reference_source = "stub_fixed_price"
    def __init__(self, price=95000.0): self._price = price
    def get_spot(self): return self._price

class StubKalshiClient:
    def __init__(self, fill_always=True):
        self.fill_always = fill_always
        self.submitted_orders = []
    def submit_order(self, payload):
        assert payload.get("ticker"), "Payload missing ticker"
        order_id = f"stub-{uuid.uuid4().hex[:8]}"
        self.submitted_orders.append(payload)
        if self.fill_always:
            return {"order_id": order_id, "status": "filled",
                    "fill_count_fp": payload["count"], "remaining_count_fp": 0,
                    "average_fill_price": payload.get("yes_price") or payload.get("no_price")}
        return {"order_id": order_id, "status": "resting", "fill_count_fp": 0,
                "remaining_count_fp": payload["count"], "average_fill_price": None}

@dataclass
class SignalContext:
    correlation_id: str; market_ticker: str; event_ticker: str; strike: float
    expiry: str; side: str; minutes_to_expiry: float; spot_at_signal: float
    reference_source: str; best_yes_bid: float; best_yes_ask: float
    best_no_bid: float; best_no_ask: float; spread_cents: float
    depth_bid: float; depth_ask: float; book_timestamp: str
    book_timestamp_ms: float; signal_timestamp_ms: float; current_timestamp_ms: float
    p_raw: float; limit_price_cents: float; requested_count: int = 5

class DryRunEnforcementError(RuntimeError): pass

class Phase1Pipeline:
    def __init__(self, logger, client, spot_source=None, clustering_cfg=None,
                 open_positions=None, recent_trades=None, dry_run=True,
                 shrinkage_factor=0.70, lambda_prob=1.0, lambda_fill=0.10,
                 tau_floor_seconds=60.0, max_signal_age_seconds=5.0, max_book_age_seconds=2.0,
                 max_spread_cents=6.0, min_depth=10.0, min_price_cents=1.0, max_price_cents=99.0,
                 min_ev_submitted_cents=1.0, adverse_selection_fraction=0.25,
                 adverse_selection_min_cents=1.0, fee_buffer_cents=0.5, slippage_buffer_cents=0.5):
        if not dry_run: raise DryRunEnforcementError("dry_run=False is not permitted in Phase 1.")
        self.dry_run=dry_run; self.logger=logger; self.client=client
        self.spot_source=spot_source or StubSpotSource(price=95000.0)
        self.clustering_cfg=clustering_cfg or ClusteringConfig()
        self.open_positions=open_positions or []; self.recent_trades=recent_trades or []
        self.shrinkage_factor=shrinkage_factor; self.lambda_prob=lambda_prob
        self.lambda_fill=lambda_fill; self.tau_floor_seconds=tau_floor_seconds
        self.max_signal_age_seconds=max_signal_age_seconds; self.max_book_age_seconds=max_book_age_seconds
        self.max_spread_cents=max_spread_cents; self.min_depth=min_depth
        self.min_price_cents=min_price_cents; self.max_price_cents=max_price_cents
        self.min_ev_submitted_cents=min_ev_submitted_cents
        self.adverse_selection_fraction=adverse_selection_fraction
        self.adverse_selection_min_cents=adverse_selection_min_cents
        self.fee_buffer_cents=fee_buffer_cents; self.slippage_buffer_cents=slippage_buffer_cents

    def process_signal(self, ctx: SignalContext) -> dict:
        trade_attempt_id = f"attempt-{uuid.uuid4().hex[:8]}"
        try:
            spot_at_signal = self.spot_source.get_spot()
            reference_source = self.spot_source.reference_source
        except Exception as e:
            self.logger.log_error(exception_type=type(e).__name__, exception_message=str(e), context="spot_source.get_spot [signal]")
            self.logger.log_skip(correlation_id=ctx.correlation_id, skip_reason="SIGNAL_SOURCE_ERROR", block_reason=f"spot_source failed: {type(e).__name__}")
            return {"outcome": "skipped", "skip_reason": "SIGNAL_SOURCE_ERROR"}
        self.logger.log_signal(correlation_id=ctx.correlation_id, market_ticker=ctx.market_ticker,
            event_ticker=ctx.event_ticker, strike=ctx.strike, expiry=ctx.expiry, side=ctx.side,
            minutes_to_expiry=ctx.minutes_to_expiry, spot_at_signal=spot_at_signal, reference_source=reference_source,
            best_yes_bid=ctx.best_yes_bid, best_yes_ask=ctx.best_yes_ask, best_no_bid=ctx.best_no_bid,
            best_no_ask=ctx.best_no_ask, spread_cents=ctx.spread_cents, depth_bid=ctx.depth_bid,
            depth_ask=ctx.depth_ask, book_timestamp=ctx.book_timestamp, p_raw=ctx.p_raw)
        guard_ctx = GuardContext(best_yes_bid=ctx.best_yes_bid, best_yes_ask=ctx.best_yes_ask,
            best_no_bid=ctx.best_no_bid, best_no_ask=ctx.best_no_ask, spread_cents=ctx.spread_cents,
            depth_bid=ctx.depth_bid, depth_ask=ctx.depth_ask, book_timestamp_ms=ctx.book_timestamp_ms,
            signal_timestamp_ms=ctx.signal_timestamp_ms, current_timestamp_ms=ctx.current_timestamp_ms,
            minutes_to_expiry=ctx.minutes_to_expiry, limit_price_cents=ctx.limit_price_cents,
            max_spread_cents=self.max_spread_cents, min_depth=self.min_depth, min_price_cents=self.min_price_cents,
            max_price_cents=self.max_price_cents, max_book_age_seconds=self.max_book_age_seconds,
            max_signal_age_seconds=self.max_signal_age_seconds, tau_floor_seconds=self.tau_floor_seconds)
        guard_result = GuardRouter().check(guard_ctx)
        if not guard_result.passed:
            self.logger.log_skip(correlation_id=ctx.correlation_id, skip_reason=guard_result.skip_reason,
                block_reason=guard_result.block_reason, market_ticker=ctx.market_ticker, side=ctx.side,
                spread_ok=guard_result.spread_ok, depth_ok=guard_result.depth_ok, time_ok=guard_result.time_ok, p_raw=ctx.p_raw)
            return {"outcome": "skipped", "skip_reason": guard_result.skip_reason}
        notional = int(ctx.limit_price_cents * ctx.requested_count)
        cluster_result = check_clustering(new_side=ctx.side, new_strike=ctx.strike, new_notional_cents=notional,
            open_positions=self.open_positions, recent_trades=self.recent_trades, cfg=self.clustering_cfg, now_ms=ctx.current_timestamp_ms)
        if not cluster_result.allowed:
            self.logger.log_skip(correlation_id=ctx.correlation_id, skip_reason=cluster_result.skip_reason,
                block_reason=cluster_result.block_reason, market_ticker=ctx.market_ticker, side=ctx.side, clustering_ok=False, p_raw=ctx.p_raw)
            return {"outcome": "skipped", "skip_reason": cluster_result.skip_reason}
        try: shrinkage = apply_shrinkage(ctx.p_raw, self.shrinkage_factor)
        except ProbabilityError as e:
            self.logger.log_skip(correlation_id=ctx.correlation_id, skip_reason="PROBABILITY_ERROR", block_reason=str(e), p_raw=ctx.p_raw)
            return {"outcome": "skipped", "skip_reason": "PROBABILITY_ERROR"}
        signal_age_s = (ctx.current_timestamp_ms - ctx.signal_timestamp_ms) / 1000.0
        tau_s = ctx.minutes_to_expiry * 60.0
        prob_latency = adjust_probability_for_latency(p_input=shrinkage.p_shrunk, delta_t_seconds=signal_age_s,
            tau_seconds=tau_s, lambda_prob=self.lambda_prob, tau_floor_seconds=self.tau_floor_seconds)
        try:
            bid = ctx.best_yes_bid if ctx.side=="yes" else ctx.best_no_bid
            ask = ctx.best_yes_ask if ctx.side=="yes" else ctx.best_no_ask
            fill_est = estimate_fill_probability_base(order_price=ctx.limit_price_cents, best_bid=bid, best_ask=ask)
        except FillModelError as e:
            self.logger.log_skip(correlation_id=ctx.correlation_id, skip_reason="FILL_MODEL_ERROR", block_reason=str(e), p_raw=ctx.p_raw, p_shrunk=shrinkage.p_shrunk)
            return {"outcome": "skipped", "skip_reason": "FILL_MODEL_ERROR"}
        book_age_s = (ctx.current_timestamp_ms - ctx.book_timestamp_ms) / 1000.0
        fill_latency = adjust_fill_probability_for_latency(p_fill_base=fill_est.p_fill_base, delta_t_seconds=book_age_s, lambda_fill=self.lambda_fill)
        try:
            ev = compute_ev(p_adj=prob_latency.p_latency, side=ctx.side, price_cents=ctx.limit_price_cents,
                p_fill_adjusted=fill_latency.p_fill_adjusted, spread_cents=ctx.spread_cents,
                adverse_selection_fraction=self.adverse_selection_fraction, adverse_selection_min_cents=self.adverse_selection_min_cents,
                fee_buffer_cents=self.fee_buffer_cents, slippage_buffer_cents=self.slippage_buffer_cents, min_ev_submitted_cents=self.min_ev_submitted_cents)
        except EVError as e:
            self.logger.log_skip(correlation_id=ctx.correlation_id, skip_reason="EV_COMPUTATION_ERROR", block_reason=str(e), p_raw=ctx.p_raw, p_shrunk=shrinkage.p_shrunk)
            return {"outcome": "skipped", "skip_reason": "EV_COMPUTATION_ERROR"}
        strategy = route(side=ctx.side, p_adj=prob_latency.p_latency, minutes_to_expiry=ctx.minutes_to_expiry,
            ev_submitted_cents=ev.ev_submitted_cents, min_ev_cents=self.min_ev_submitted_cents)
        if not ev.passes or not strategy.should_trade:
            self.logger.log_skip(correlation_id=ctx.correlation_id, skip_reason="EV_BELOW_THRESHOLD",
                block_reason=ev.fail_reason or strategy.skip_reason, market_ticker=ctx.market_ticker, side=ctx.side,
                spread_ok=True, depth_ok=True, time_ok=True, clustering_ok=True, p_raw=ctx.p_raw,
                p_shrunk=shrinkage.p_shrunk, p_latency=prob_latency.p_latency, ev_filled_cents=ev.ev_filled_cents, ev_submitted_cents=ev.ev_submitted_cents)
            return {"outcome": "skipped", "skip_reason": "EV_BELOW_THRESHOLD"}
        try:
            payload = map_intent_to_v2_payload(ticker=ctx.market_ticker, side=ctx.side, limit_price_cents=ctx.limit_price_cents,
                count=ctx.requested_count, min_price_cents=self.min_price_cents, max_price_cents=self.max_price_cents)
        except OrderMappingError as e:
            self.logger.log_skip(correlation_id=ctx.correlation_id, skip_reason="ORDER_MAPPING_ERROR", block_reason=str(e), p_raw=ctx.p_raw)
            return {"outcome": "skipped", "skip_reason": "ORDER_MAPPING_ERROR"}
        self.logger.log_order_prepared(correlation_id=ctx.correlation_id, trade_attempt_id=trade_attempt_id,
            market_ticker=ctx.market_ticker, side=ctx.side, order_type="limit", time_in_force="gtc",
            limit_price_cents=ctx.limit_price_cents, requested_count=ctx.requested_count, p_raw=ctx.p_raw,
            p_shrunk=shrinkage.p_shrunk, p_latency=prob_latency.p_latency, shrink_factor=self.shrinkage_factor,
            lambda_prob=self.lambda_prob, delta_t_seconds=signal_age_s, tau_seconds=prob_latency.tau_seconds,
            p_fill_base=fill_est.p_fill_base, p_fill_adjusted=fill_latency.p_fill_adjusted, lambda_fill=self.lambda_fill,
            price_position=fill_est.price_position, fill_latency_ms=book_age_s*1000, ev_filled_cents=ev.ev_filled_cents,
            ev_submitted_cents=ev.ev_submitted_cents, fees_estimated=ev.fee_buffer_cents,
            slippage_buffer=ev.slippage_buffer_cents, adverse_selection_penalty=ev.adverse_selection_penalty_cents,
            min_ev_threshold=self.min_ev_submitted_cents, strategy_name=strategy.strategy_name, strategy_notes=strategy.notes)
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            spot_at_submit = self.spot_source.get_spot(); spot_at_submit_source = self.spot_source.reference_source; spot_submit_error = False
        except Exception as e:
            self.logger.log_error(exception_type=type(e).__name__, exception_message=str(e), context="spot_source.get_spot [submit]")
            spot_at_submit = spot_at_signal; spot_at_submit_source = "fallback_signal"; spot_submit_error = True
        self.logger.log_order_submitted(correlation_id=ctx.correlation_id, trade_attempt_id=trade_attempt_id,
            order_id="pending", market_ticker=ctx.market_ticker, side=ctx.side, limit_price_cents=ctx.limit_price_cents,
            requested_count=ctx.requested_count, timestamp_submit=now_iso, spot_at_submit=spot_at_submit,
            spot_at_submit_source=spot_at_submit_source, spot_source_error=spot_submit_error,
            spot_source_error_stage="submit" if spot_submit_error else None)
        response = self.client.submit_order(payload_to_dict(payload))
        order_id = response.get("order_id", "unknown")
        try:
            spot_at_fill = self.spot_source.get_spot(); spot_at_fill_source = self.spot_source.reference_source; spot_fill_error = False
        except Exception as e:
            self.logger.log_error(exception_type=type(e).__name__, exception_message=str(e), context="spot_source.get_spot [fill]")
            spot_at_fill = spot_at_submit; spot_at_fill_source = "fallback_submit"; spot_fill_error = True
        if response.get("status") == "filled":
            self.logger.log_order_filled(correlation_id=ctx.correlation_id, trade_attempt_id=trade_attempt_id,
                order_id=order_id, market_ticker=ctx.market_ticker, side=ctx.side,
                filled_count=response.get("fill_count_fp", ctx.requested_count), remaining_count=response.get("remaining_count_fp", 0),
                avg_fill_price=response.get("average_fill_price", ctx.limit_price_cents), timestamp_fill=now_iso,
                spot_at_fill=spot_at_fill, spot_at_fill_source=spot_at_fill_source,
                spot_source_error=spot_fill_error, spot_source_error_stage="fill" if spot_fill_error else None)
            return {"outcome": "filled", "order_id": order_id}
        return {"outcome": "resting", "order_id": order_id}


def run_smoke_test(log_file="logs/smoke_test_output.jsonl") -> dict:
    import os; os.makedirs(os.path.dirname(log_file) if os.path.dirname(log_file) else ".", exist_ok=True)
    logger = LifecycleLogger(log_file=log_file)
    client = StubKalshiClient(fill_always=True)
    spot = StubSpotSource(price=94921.0)
    pipeline = Phase1Pipeline(logger=logger, client=client, spot_source=spot)
    base_time = time.time(); expiry_ts = base_time + 420.0
    expiry_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expiry_ts))
    now_ms = base_time * 1000.0
    def sig(corr_id, **overrides):
        defaults = dict(correlation_id=corr_id, market_ticker="KXBTC-SMOKE-T95000", event_ticker="KXBTC-SMOKE",
            strike=95000.0, expiry=expiry_iso, side="yes", minutes_to_expiry=7.0, spot_at_signal=spot.get_spot(),
            reference_source="coinbase_ticker", best_yes_bid=46.0, best_yes_ask=50.0, best_no_bid=50.0, best_no_ask=54.0,
            spread_cents=4.0, depth_bid=80.0, depth_ask=80.0, book_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(base_time-0.5)),
            book_timestamp_ms=now_ms-500, signal_timestamp_ms=now_ms-1000, current_timestamp_ms=now_ms,
            p_raw=0.72, limit_price_cents=48.0, requested_count=5)
        defaults.update(overrides)
        return SignalContext(**defaults)
    results = {}
    results["allowed_yes"] = pipeline.process_signal(sig("smoke-allowed-yes"))
    results["guard_fail_spread"] = pipeline.process_signal(sig("smoke-guard-spread", spread_cents=15.0))
    results["stale_signal"] = pipeline.process_signal(sig("smoke-stale", signal_timestamp_ms=now_ms-10_000, current_timestamp_ms=now_ms))
    pipeline.recent_trades = [RecentTrade(side="no", opened_at_ms=now_ms-30_000)]
    results["cluster_rate_limit"] = pipeline.process_signal(sig("smoke-cluster", side="no", p_raw=0.25))
    pipeline.recent_trades = []
    results["ev_fail"] = pipeline.process_signal(sig("smoke-ev", p_raw=0.50))
    results["allowed_no"] = pipeline.process_signal(sig("smoke-allowed-no", side="no", p_raw=0.25))
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Kalshi BTC 15-min bot - Phase 1")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--log-file", default="logs/dry_run_events.jsonl")
    args = parser.parse_args()
    if args.smoke:
        log_file = args.log_file.replace("dry_run_events", "smoke_test_output")
        results = run_smoke_test(log_file=log_file)
        for scenario, result in results.items():
            print(f"  {scenario:30s} -> {result['outcome']}" + (f" ({result.get('skip_reason','')}" if result['outcome']=='skipped' else ""))
    else:
        print("Continuous dry-run loop not yet wired. Use --smoke for now.")

if __name__ == "__main__":
    main()
