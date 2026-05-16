"""collector.py - Week 2 Dry-Run Collector. Modes: loop-smoke, replay, live."""
import argparse, json, os, signal, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from kalshi_btc15m_bot.analytics.lifecycle_logger import LifecycleLogger
from kalshi_btc15m_bot.app import Phase1Pipeline, SignalContext, StubKalshiClient, StubSpotSource, CoinbaseSpotSource

MODEL_VERSION = "phase1-v3"
FEATURE_VERSION = "scaffold-v2.2.1"
DEFAULT_POLL_SECONDS = 15

def load_snapshot(path):
    with open(path) as f: data = json.load(f)
    if isinstance(data, dict) and "snapshots" in data: return data["snapshots"]
    if isinstance(data, list): return data
    raise ValueError(f"Unrecognised snapshot format in {path}")

class SignalSourceError(Exception): pass
class SnapshotTimestampInvalid(Exception): pass
class NoTradableSignal(Exception): pass

def generate_p_raw_from_scaffold(features, context, phase, yes_bid=50.0, no_bid=50.0):
    from kalshi_btc15m_bot.strategy.scorer import best_entry_decision
    from kalshi_btc15m_bot.market.orderbook import OrderbookState, OrderbookLevel
    from kalshi_btc15m_bot.config import load_config
    book = OrderbookState()
    if yes_bid > 0: book.yes_bids.append(OrderbookLevel(price_cents=yes_bid, size=100))
    if no_bid > 0: book.no_bids.append(OrderbookLevel(price_cents=no_bid, size=100))
    cfg = load_config()
    decision = best_entry_decision(features, context, book, phase, cfg)
    if not decision.tradable or not decision.side:
        raise NoTradableSignal(f"Scorer returned no tradable signal: {decision.reason}")
    p_raw = max(0.01, min(0.99, decision.fair_yes_cents / 100.0))
    return p_raw, decision.side

def fixed_signal_generator(cycle_idx):
    sides = ["yes","no","yes","yes","no"]
    probs = [0.72, 0.25, 0.68, 0.50, 0.30]
    return probs[cycle_idx % len(probs)], sides[cycle_idx % len(sides)]

def get_live_market_snapshot():
    try:
        from kalshi_btc15m_bot.clients.kalshi_rest import KalshiRestClient
        from kalshi_btc15m_bot.config import load_config
        from kalshi_btc15m_bot.market.discovery import find_open_btc15m_market
        from kalshi_btc15m_bot.market.orderbook import (fetch_rest_orderbook_snapshot,
            best_yes_bid, best_yes_ask, best_no_bid, best_no_ask, yes_spread, is_book_stale)
        cfg = load_config(); rest = KalshiRestClient.build(cfg)
        market = find_open_btc15m_market(rest, cfg.series_ticker)
        now = datetime.now(timezone.utc)
        remaining = (market.close_time - now).total_seconds()
        book = fetch_rest_orderbook_snapshot(rest, market.ticker)
        return {"market_ticker": market.ticker,
                "strike": None,  # kxbtc15m is time-based — no price strike; null avoids misleading analytics
                "expiry": market.close_time.isoformat(), "minutes_to_expiry": remaining/60.0,
                "best_yes_bid": best_yes_bid(book) or 0.0, "best_yes_ask": best_yes_ask(book) or 0.0,
                "best_no_bid": best_no_bid(book) or 0.0, "best_no_ask": best_no_ask(book) or 0.0,
                "spread_cents": yes_spread(book), "depth_bid": 50.0, "depth_ask": 50.0,
                "book_timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "book_stale": is_book_stale(book)}
    except Exception as e: raise SignalSourceError(f"Live market snapshot failed: {e}")

def get_candle_features():
    from kalshi_btc15m_bot.clients.coinbase_spot import CoinbaseSpotClient
    from kalshi_btc15m_bot.config import load_config
    from kalshi_btc15m_bot.main import build_feature_bundle
    from kalshi_btc15m_bot.strategy.recent_context import build_recent_context_summary
    cfg = load_config(); coinbase = CoinbaseSpotClient()
    candles = coinbase.get_candles(cfg.coinbase_product, cfg.coinbase_granularity)[-cfg.coinbase_candles_count:]
    return build_feature_bundle(candles), build_recent_context_summary([])

def _parse_book_ts_ms(book_timestamp, fallback_now_ms, mode):
    if book_timestamp is None:
        if mode == "loop-smoke": return int(fallback_now_ms - 500)
        raise SnapshotTimestampInvalid("book_timestamp missing")
    try:
        raw = book_timestamp.rstrip("Z") + "+00:00" if book_timestamp.endswith("Z") else book_timestamp
        ts = int(datetime.fromisoformat(raw).timestamp() * 1000)
        return min(ts, int(fallback_now_ms - 500))
    except (ValueError, AttributeError, TypeError):
        if mode == "loop-smoke": return int(fallback_now_ms - 500)
        raise SnapshotTimestampInvalid(f"malformed book_timestamp: {book_timestamp!r}")

class Collector:
    def __init__(self, mode, log_file, duration_minutes, poll_seconds=DEFAULT_POLL_SECONDS,
                 max_cycles=None, snapshot_file=None, run_id=None):
        self.mode=mode; self.duration_minutes=duration_minutes; self.poll_seconds=poll_seconds
        self.max_cycles=max_cycles; self.snapshot_file=snapshot_file
        self.run_id=run_id or f"run-{uuid.uuid4().hex[:8]}"
        date_str=datetime.now(timezone.utc).strftime("%Y-%m-%d")  # UTC date
        if "YYYY-MM-DD" in log_file: log_file=log_file.replace("YYYY-MM-DD",date_str)
        elif not log_file.endswith(".jsonl"): log_file=log_file.rstrip("/")+f"/dry_run_events_{date_str}.jsonl"
        self.log_file=log_file
        os.makedirs(os.path.dirname(os.path.abspath(log_file)),exist_ok=True)
        self.logger=LifecycleLogger(log_file=log_file,extra_base_fields={"run_id":self.run_id})
        spot_source=StubSpotSource(price=95000.0) if mode in ("loop-smoke","replay") else CoinbaseSpotSource()
        self.pipeline=Phase1Pipeline(logger=self.logger,client=StubKalshiClient(fill_always=True),spot_source=spot_source)
        self.snapshots=[]
        if mode=="replay" and snapshot_file: self.snapshots=load_snapshot(snapshot_file)
        self._stop=False
        signal.signal(signal.SIGINT,self._handle_sigint)

    def _handle_sigint(self,signum,frame):
        print("\nCtrl+C received — flushing logs and exiting..."); self._stop=True

    def _make_signal_ctx(self,snapshot,p_raw,side,cycle_id):
        now_ms=time.time()*1000.0
        raw_book_timestamp=snapshot.get("book_timestamp")
        book_timestamp_ms=_parse_book_ts_ms(raw_book_timestamp,now_ms,self.mode)
        return SignalContext(
            correlation_id=cycle_id,market_ticker=snapshot["market_ticker"],
            event_ticker=snapshot["market_ticker"].rsplit("-",1)[0],
            strike=snapshot.get("strike") or 0.0,  # None for live time-based markets; 0.0 fallback for SignalContext
            expiry=snapshot["expiry"],side=side,minutes_to_expiry=snapshot["minutes_to_expiry"],
            spot_at_signal=snapshot.get("spot_price",95000.0),
            reference_source="stub_fixed_price" if self.mode!="live" else "coinbase_ticker",
            best_yes_bid=snapshot["best_yes_bid"],best_yes_ask=snapshot["best_yes_ask"],
            best_no_bid=snapshot["best_no_bid"],best_no_ask=snapshot["best_no_ask"],
            spread_cents=snapshot["spread_cents"],depth_bid=snapshot.get("depth_bid",50.0),
            depth_ask=snapshot.get("depth_ask",50.0),book_timestamp=raw_book_timestamp or "",
            book_timestamp_ms=book_timestamp_ms,signal_timestamp_ms=now_ms-1000,current_timestamp_ms=now_ms,
            p_raw=p_raw,limit_price_cents=snapshot.get("limit_price_cents",48.0),requested_count=5)

    def _log_run_summary(self,cycles,filled,skipped,errors,elapsed_s,signal_sources_by_count=None):
        saved=self.logger._extra_base_fields.copy()
        self.logger._extra_base_fields={"run_id":self.run_id,"cycle_id":None,"signal_source":None,
                                         "model_version":saved.get("model_version"),"feature_version":saved.get("feature_version")}
        self.logger._write({**self.logger._base_fields("run_summary","run"),"run_id":self.run_id,
                            "mode":self.mode,"total_cycles":cycles,"filled":filled,"skipped":skipped,
                            "errors":errors,"elapsed_seconds":round(elapsed_s,1),"log_file":self.log_file,
                            "signal_sources_by_count":signal_sources_by_count or {}})
        self.logger._extra_base_fields=saved

    def run(self):
        deadline=time.time()+self.duration_minutes*60
        cycle_idx=0; filled=skipped=errors=0; start_time=time.time(); signal_sources={}
        print(f"[{self.run_id}] Starting {self.mode} | duration={self.duration_minutes}min | log={self.log_file}")
        while not self._stop and time.time()<deadline:
            if self.max_cycles is not None and cycle_idx>=self.max_cycles:
                print(f"Reached max_cycles={self.max_cycles}, stopping."); break
            cycle_id=f"{self.run_id}-c{cycle_idx:04d}"; cycle_start=time.time()
            self.logger._extra_base_fields={"run_id":self.run_id,"cycle_id":cycle_id,
                "signal_source":"unavailable","model_version":MODEL_VERSION,"feature_version":FEATURE_VERSION}
            try:
                snapshot,p_raw,side,signal_source=self._get_cycle_data(cycle_idx)
                self.logger._extra_base_fields["signal_source"]=signal_source
                signal_sources[signal_source]=signal_sources.get(signal_source,0)+1
                ctx=self._make_signal_ctx(snapshot,p_raw,side,cycle_id)
                result=self.pipeline.process_signal(ctx)
                if result["outcome"]=="filled":
                    filled+=1; print(f"  [{cycle_id}] filled  order_id={result.get('order_id')}")
                else:
                    skipped+=1; print(f"  [{cycle_id}] skipped reason={result.get('skip_reason','?')}")
            except SnapshotTimestampInvalid as e:
                skipped+=1
                self.logger.log_skip(correlation_id=cycle_id,skip_reason="SNAPSHOT_TIMESTAMP_INVALID",block_reason=str(e))
                print(f"  [{cycle_id}] skipped reason=SNAPSHOT_TIMESTAMP_INVALID")
            except NoTradableSignal as e:
                skipped+=1; signal_sources["scaffold_scorer_live"]=signal_sources.get("scaffold_scorer_live",0)+1
                self.logger.log_skip(correlation_id=cycle_id,skip_reason="NO_TRADABLE_SIGNAL",block_reason=str(e))
                print(f"  [{cycle_id}] skipped reason=NO_TRADABLE_SIGNAL")
            except SignalSourceError as e:
                errors+=1; signal_sources["unavailable"]=signal_sources.get("unavailable",0)+1
                self.logger.log_skip(correlation_id=cycle_id,skip_reason="SIGNAL_SOURCE_ERROR",block_reason=str(e))
                print(f"  [{cycle_id}] ERROR  {e}")
            except Exception as e:
                errors+=1
                self.logger.log_error(exception_type=type(e).__name__,exception_message=str(e),context=f"collector cycle {cycle_id}")
                print(f"  [{cycle_id}] UNEXPECTED ERROR  {e}")
            cycle_idx+=1
            elapsed=time.time()-cycle_start
            sleep_time=min(max(0,self.poll_seconds-elapsed),deadline-time.time())
            if sleep_time>0 and not self._stop: time.sleep(sleep_time)
        elapsed_total=time.time()-start_time
        self._log_run_summary(cycle_idx,filled,skipped,errors,elapsed_total,signal_sources_by_count=signal_sources)
        print(f"\n[{self.run_id}] Done - {cycle_idx} cycles | {filled} filled | {skipped} skipped | {errors} errors")

    def _get_cycle_data(self,cycle_idx):
        now_utc=datetime.now(timezone.utc)
        base_expiry=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(time.time()+420))
        if self.mode=="loop-smoke":
            p_raw,side=fixed_signal_generator(cycle_idx)
            snap={"market_ticker":"KXBTC-SMOKE-T95000","strike":95000.0,"expiry":base_expiry,
                  "minutes_to_expiry":7.0,"best_yes_bid":46.0,"best_yes_ask":50.0,
                  "best_no_bid":50.0,"best_no_ask":54.0,"spread_cents":4.0,
                  "depth_bid":80.0,"depth_ask":80.0,
                  "book_timestamp":now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),"spot_price":95000.0}
            return snap,p_raw,side,"fixed_signal"
        elif self.mode=="replay":
            if not self.snapshots: raise SignalSourceError("No snapshots loaded for replay mode")
            snap=dict(self.snapshots[cycle_idx%len(self.snapshots)]); snap["expiry"]=base_expiry
            if "p_raw" in snap and "side" in snap:
                return snap,snap["p_raw"],snap["side"],"snapshot_stored"
            try:
                features=snap.get("features",{}); context=snap.get("context",{}); phase=snap.get("phase","phase2")
                p_raw,side=generate_p_raw_from_scaffold(features,context,phase,
                    yes_bid=snap.get("best_yes_bid",50.0),no_bid=snap.get("best_no_bid",50.0))
                return snap,p_raw,side,"scaffold_scorer"
            except Exception as e: raise SignalSourceError(f"Replay scorer failed: {e}")
        elif self.mode=="live":
            snapshot=get_live_market_snapshot()
            if snapshot.get("book_stale"): raise SignalSourceError("Live orderbook is stale")
            try:
                features,context=get_candle_features()
                from kalshi_btc15m_bot.market.clocks import phase_from_clock
                from datetime import timedelta
                close_dt=datetime.fromisoformat(snapshot["expiry"].replace("Z","+00:00"))
                open_dt=close_dt-timedelta(minutes=15)
                phase=phase_from_clock(open_dt,close_dt,datetime.now(timezone.utc))
                p_raw,side=generate_p_raw_from_scaffold(features,context,phase,
                    yes_bid=snapshot.get("best_yes_bid",50.0),no_bid=snapshot.get("best_no_bid",50.0))
                snapshot["spot_price"]=self.pipeline.spot_source.get_spot()
                return snapshot,p_raw,side,"scaffold_scorer_live"
            except SignalSourceError: raise
            except Exception as e: raise SignalSourceError(f"Live signal generation failed: {e}")
        raise ValueError(f"Unknown mode: {self.mode}")

def main():
    parser=argparse.ArgumentParser(description="Kalshi BTC 15-min Week 2 collector")
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--loop-smoke",action="store_true")
    group.add_argument("--dry-run",action="store_true")
    parser.add_argument("--market-source",choices=["replay","live"],default="replay")
    parser.add_argument("--snapshot-file",type=str)
    parser.add_argument("--duration-minutes",type=float,default=10.0)
    parser.add_argument("--poll-seconds",type=float,default=DEFAULT_POLL_SECONDS)
    parser.add_argument("--max-cycles",type=int,default=None)
    parser.add_argument("--log-file",type=str,default="logs/dry_run_events_YYYY-MM-DD.jsonl")
    args=parser.parse_args()
    if args.loop_smoke: mode="loop-smoke"
    elif args.dry_run:
        mode=args.market_source
        if mode=="replay" and not args.snapshot_file: parser.error("--market-source replay requires --snapshot-file")
    else: parser.error("Must specify --loop-smoke or --dry-run")
    Collector(mode=mode,log_file=args.log_file,duration_minutes=args.duration_minutes,
              poll_seconds=args.poll_seconds,max_cycles=args.max_cycles,snapshot_file=args.snapshot_file).run()

if __name__=="__main__":
    main()
