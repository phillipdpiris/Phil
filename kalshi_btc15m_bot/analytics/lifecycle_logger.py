"""lifecycle_logger.py - Phase 1 lifecycle event logger. See full source in v11 zip."""
import json, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

SCHEMA_VERSION = "1.0"
BOT_VERSION = "1.0.0-phase1"
_REDACTED_KEYS = frozenset({"api_key","private_key","secret","password","token"})
EVENT_TYPES = frozenset({"signal_generated","trade_skipped","order_prepared","order_submitted",
                         "order_rejected","order_filled","order_partially_filled","order_cancelled",
                         "settlement_recorded","error_event","run_summary"})

def _redact(obj, depth=0):
    if depth>10: return obj
    if isinstance(obj,dict): return {k:"[REDACTED]" if k.lower() in _REDACTED_KEYS else _redact(v,depth+1) for k,v in obj.items()}
    if isinstance(obj,list): return [_redact(i,depth+1) for i in obj]
    return obj

class LifecycleLogger:
    def __init__(self, log_file="logs/dry_run_events.jsonl", bot_version=BOT_VERSION,
                 config_version="phase1", dry_run=True, extra_base_fields=None):
        self.log_file = Path(log_file)
        self.bot_version = bot_version
        self.config_version = config_version
        self.dry_run = dry_run
        self._extra_base_fields: dict = extra_base_fields or {}
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def _base_fields(self, event_type, correlation_id=None):
        if event_type not in EVENT_TYPES: raise ValueError(f"Unknown event_type: {event_type!r}")
        now_utc = datetime.now(timezone.utc)
        base = {"schema_version": SCHEMA_VERSION, "bot_version": self.bot_version,
                "config_version": self.config_version, "dry_run": self.dry_run,
                "p_raw_semantics": "p_yes", "event_id": str(uuid.uuid4()), "event_type": event_type,
                "correlation_id": correlation_id or str(uuid.uuid4()),
                "timestamp_utc": now_utc.isoformat(), "monotonic_time_ns": time.monotonic_ns()}
        if self._extra_base_fields: base.update(self._extra_base_fields)
        return base

    def _write(self, record):
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(_redact(record), default=str) + "\n")

    def log_signal(self, *, correlation_id, market_ticker, event_ticker, strike, expiry, side,
                   minutes_to_expiry, spot_at_signal, reference_source, best_yes_bid, best_yes_ask,
                   best_no_bid, best_no_ask, spread_cents, depth_bid, depth_ask, book_timestamp, p_raw, extra=None):
        r = {**self._base_fields("signal_generated", correlation_id), "market_ticker": market_ticker,
             "event_ticker": event_ticker, "strike": strike, "expiry": expiry, "side": side,
             "minutes_to_expiry": minutes_to_expiry, "spot_at_signal": spot_at_signal,
             "reference_source": reference_source, "best_yes_bid": best_yes_bid, "best_yes_ask": best_yes_ask,
             "best_no_bid": best_no_bid, "best_no_ask": best_no_ask, "spread_cents": spread_cents,
             "depth_bid": depth_bid, "depth_ask": depth_ask, "book_timestamp": book_timestamp, "p_raw": p_raw}
        if extra: r.update(extra)
        self._write(r)

    def log_skip(self, *, correlation_id, skip_reason, block_reason=None, market_ticker=None, side=None,
                 spread_ok=None, depth_ok=None, time_ok=None, clustering_ok=None, p_raw=None,
                 p_shrunk=None, p_latency=None, ev_filled_cents=None, ev_submitted_cents=None, extra=None):
        r = {**self._base_fields("trade_skipped", correlation_id), "skip_reason": skip_reason,
             "block_reason": block_reason, "market_ticker": market_ticker, "side": side,
             "spread_ok": spread_ok, "depth_ok": depth_ok, "time_ok": time_ok, "clustering_ok": clustering_ok,
             "p_raw": p_raw, "p_shrunk": p_shrunk, "p_latency": p_latency,
             "ev_filled_cents": ev_filled_cents, "ev_submitted_cents": ev_submitted_cents}
        if extra: r.update(extra)
        self._write(r)

    def log_order_prepared(self, *, correlation_id, trade_attempt_id, market_ticker, side, order_type,
                           time_in_force, limit_price_cents, requested_count, p_raw, p_shrunk, p_latency,
                           shrink_factor, lambda_prob, delta_t_seconds, tau_seconds, p_fill_base,
                           p_fill_adjusted, lambda_fill, price_position, fill_latency_ms, ev_filled_cents,
                           ev_submitted_cents, fees_estimated, slippage_buffer, adverse_selection_penalty,
                           min_ev_threshold, strategy_name=None, strategy_notes=None, extra=None):
        r = {**self._base_fields("order_prepared", correlation_id), "trade_attempt_id": trade_attempt_id,
             "market_ticker": market_ticker, "side": side, "order_type": order_type,
             "time_in_force": time_in_force, "limit_price_cents": limit_price_cents,
             "requested_count": requested_count, "p_raw": p_raw, "p_shrunk": p_shrunk, "p_latency": p_latency,
             "shrink_factor": shrink_factor, "lambda_prob": lambda_prob, "delta_t_seconds": delta_t_seconds,
             "tau_seconds": tau_seconds, "p_fill_base": p_fill_base, "p_fill_adjusted": p_fill_adjusted,
             "lambda_fill": lambda_fill, "price_position": price_position, "fill_latency_ms": fill_latency_ms,
             "ev_filled_cents": ev_filled_cents, "ev_submitted_cents": ev_submitted_cents,
             "fees_estimated": fees_estimated, "slippage_buffer": slippage_buffer,
             "adverse_selection_penalty": adverse_selection_penalty, "min_ev_threshold": min_ev_threshold,
             "strategy_name": strategy_name, "strategy_notes": strategy_notes}
        if extra: r.update(extra)
        self._write(r)

    def log_order_submitted(self, *, correlation_id, trade_attempt_id, order_id, market_ticker, side,
                            limit_price_cents, requested_count, timestamp_submit, spot_at_submit,
                            spot_at_submit_source=None, spot_source_error=False, spot_source_error_stage=None, extra=None):
        r = {**self._base_fields("order_submitted", correlation_id), "trade_attempt_id": trade_attempt_id,
             "order_id": order_id, "market_ticker": market_ticker, "side": side,
             "limit_price_cents": limit_price_cents, "requested_count": requested_count,
             "timestamp_submit": timestamp_submit, "spot_at_submit": spot_at_submit,
             "spot_at_submit_source": spot_at_submit_source, "spot_source_error": spot_source_error,
             "spot_source_error_stage": spot_source_error_stage}
        if extra: r.update(extra)
        self._write(r)

    def log_order_filled(self, *, correlation_id, trade_attempt_id, order_id, market_ticker, side,
                         filled_count, remaining_count, avg_fill_price, timestamp_fill, spot_at_fill,
                         spot_at_fill_source=None, spot_source_error=False, spot_source_error_stage=None,
                         partial=False, extra=None):
        event_type = "order_partially_filled" if partial else "order_filled"
        r = {**self._base_fields(event_type, correlation_id), "trade_attempt_id": trade_attempt_id,
             "order_id": order_id, "market_ticker": market_ticker, "side": side,
             "filled_count": filled_count, "remaining_count": remaining_count,
             "avg_fill_price": avg_fill_price, "timestamp_fill": timestamp_fill,
             "spot_at_fill": spot_at_fill, "spot_at_fill_source": spot_at_fill_source,
             "spot_source_error": spot_source_error, "spot_source_error_stage": spot_source_error_stage}
        if extra: r.update(extra)
        self._write(r)

    def log_order_rejected(self, *, correlation_id, trade_attempt_id, market_ticker,
                           api_error_code=None, exception_type=None, exception_message=None, retry_count=0, extra=None):
        r = {**self._base_fields("order_rejected", correlation_id), "trade_attempt_id": trade_attempt_id,
             "market_ticker": market_ticker, "api_error_code": api_error_code,
             "exception_type": exception_type, "exception_message": exception_message, "retry_count": retry_count}
        if extra: r.update(extra)
        self._write(r)

    def log_error(self, *, correlation_id=None, exception_type, exception_message,
                  context=None, retry_count=0, extra=None):
        r = {**self._base_fields("error_event", correlation_id), "exception_type": exception_type,
             "exception_message": exception_message, "context": context, "retry_count": retry_count}
        if extra: r.update(extra)
        self._write(r)
