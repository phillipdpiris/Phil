from __future__ import annotations
import logging
from datetime import datetime, timezone
from .analytics.logger import JsonlLogger
from .clients.coinbase_spot import CoinbaseSpotClient
from .clients.kalshi_rest import KalshiRestClient
from .clients.kalshi_ws import KalshiWebSocketClient
from .config import load_config, validate_config
from .execution.guards import single_position_ok
from .portfolio import reconcile_position_state
from .execution.exits import build_exit_decision
from .execution.router import route_entry, route_exit
from .market.clocks import phase_from_clock, remaining_seconds
from .market.discovery import find_open_btc15m_market, refresh_market
from .market.orderbook import (best_no_ask, best_no_bid, best_yes_ask, best_yes_bid,
    build_book_from_snapshot, depth_imbalance, fetch_rest_orderbook_snapshot,
    is_book_stale, no_spread, yes_spread)
from .market.fees import estimate_entry_fee
from .models import OrderbookState
from .state_store import load_state, save_state
from .strategy.features import (compute_btc_returns, compute_mean_reversion_features,
    compute_momentum_features, compute_volatility_features)
from .strategy.recent_context import build_recent_context_summary, fetch_recent_contract_context
from .strategy.scorer import best_entry_decision

COOLDOWN_NEG_PNL_CENTS = -150.0
COOLDOWN_STOP_LOSS_COUNT = 8

def _expiry_in_cooldown(ticker, state):
    meta = state.metadata.get("expiry_stats", {}).get(ticker)
    if not meta: return False
    return float(meta.get("realized_pnl_cents", 0.0)) <= COOLDOWN_NEG_PNL_CENTS and int(meta.get("stop_losses", 0)) >= COOLDOWN_STOP_LOSS_COUNT

def build_feature_bundle(candles):
    features = {}
    features.update(compute_btc_returns(candles))
    features.update(compute_momentum_features(candles))
    features.update(compute_mean_reversion_features(candles))
    features.update(compute_volatility_features(candles))
    return features

def run_once():
    cfg = load_config(); validate_config(cfg)
    logging.basicConfig(level=getattr(logging, cfg.log_level, logging.INFO))
    logger = logging.getLogger("kalshi-btc15m-bot")
    state = load_state(cfg.state_file)
    event_logger = JsonlLogger()
    rest = KalshiRestClient.build(cfg)
    coinbase = CoinbaseSpotClient()
    run_single_cycle(cfg, logger, state, event_logger, rest, coinbase)
    save_state(cfg.state_file, state)

def run_single_cycle(cfg, logger, state, event_logger, rest, coinbase):
    market = find_open_btc15m_market(rest, cfg.series_ticker)
    market = refresh_market(rest, market.ticker)
    now = datetime.now(timezone.utc)
    phase = phase_from_clock(market.open_time, market.close_time, now)
    remaining = remaining_seconds(market.close_time, now)
    allow_trading = reconcile_position_state(rest, state, market.ticker, logger)
    book = OrderbookState()
    try:
        ws_client = KalshiWebSocketClient.connect(cfg)
        try:
            sid = ws_client.subscribe_orderbook(market.ticker)
            ws_client.get_snapshot(sid, market.ticker)
            for _ in range(20):
                ws_msg = ws_client.recv_json()
                if ws_msg.get("type") == "orderbook_snapshot" and ws_msg.get("sid") == sid:
                    book = build_book_from_snapshot(ws_msg); break
            else: raise RuntimeError("No orderbook_snapshot received")
        finally: ws_client.close()
    except Exception as exc:
        logger.warning("WS snapshot failed (%s), falling back to REST", exc)
        try: book = fetch_rest_orderbook_snapshot(rest, market.ticker)
        except Exception as exc2:
            logger.warning("Failed to fetch REST orderbook: %s", exc2)
            book = OrderbookState()
    if is_book_stale(book):
        try: book = fetch_rest_orderbook_snapshot(rest, market.ticker)
        except Exception as exc3: logger.warning("REST refresh after stale failed: %s", exc3)
    candles = coinbase.get_candles(cfg.coinbase_product, cfg.coinbase_granularity)[-cfg.coinbase_candles_count:]
    features = build_feature_bundle(candles)
    context = build_recent_context_summary(fetch_recent_contract_context(rest, cfg.series_ticker, limit=20))
    event_logger.log_market_snapshot({"ticker": market.ticker, "phase": phase,
                                       "remaining_seconds": remaining, "close_time": market.close_time.isoformat()})
    decision = best_entry_decision(features, context, book, phase, cfg)
    if decision.tradable and decision.side and phase == "phase1":
        decision.tradable = False; decision.reason = f"{decision.reason} (blocked: phase1 disabled)"
    if decision.tradable and decision.side and _expiry_in_cooldown(market.ticker, state):
        decision.tradable = False; decision.reason = f"{decision.reason} (blocked: expiry cooldown)"
    ob_summary = {"best_yes_bid": best_yes_bid(book), "best_yes_ask": best_yes_ask(book),
                  "yes_spread_cents": yes_spread(book), "best_no_bid": best_no_bid(book),
                  "best_no_ask": best_no_ask(book), "no_spread_cents": no_spread(book),
                  "depth_imbalance": depth_imbalance(book)}
    event_logger.log_signal_snapshot({"ticker": market.ticker, "phase": phase, "decision": decision.reason,
                                       "tradable": decision.tradable, "edge_cents": decision.edge_cents,
                                       "fair_yes_cents": decision.fair_yes_cents, "fair_no_cents": decision.fair_no_cents,
                                       "orderbook": ob_summary, "context": context, "features": features})
    if allow_trading and single_position_ok(state) and decision.tradable and decision.side:
        routed = route_entry(rest, market.ticker, decision, book, phase, dry_run=cfg.dry_run)
        event_logger.log_order_submission({"mode": "entry", "dry_run": cfg.dry_run, "ticker": market.ticker,
                                           "phase": phase, "payload": routed.get("payload"),
                                           "skipped": routed.get("skipped", False), "reason": routed.get("reason")})
        if not routed.get("skipped") and cfg.dry_run:
            payload = routed["payload"]
            price_cents = float(payload.get("yes_price") or payload.get("no_price") or 0)
            from .models import PositionState
            state.position = PositionState(ticker=market.ticker, side=decision.side, contracts=decision.contracts,
                                           avg_entry_price_cents=price_cents, entry_time_iso=now.isoformat(),
                                           tp1_done=False, tp2_done=False, phase_at_entry=phase, simulated=True)
    elif state.position is not None and allow_trading:
        exit_decision = build_exit_decision(state.position, book, remaining, decision.edge_cents, cfg)
        routed = route_exit(rest, market.ticker, state.position.side, exit_decision, book, dry_run=cfg.dry_run)
        event_logger.log_exit({"ticker": market.ticker, "phase": phase, "remaining_seconds": remaining,
                                "exit_decision": exit_decision.reason, "action": exit_decision.action,
                                "contracts": exit_decision.contracts, "residual_edge_cents": decision.edge_cents,
                                "dry_run": cfg.dry_run, "payload": routed.get("payload"),
                                "skipped": routed.get("skipped", False), "reason": routed.get("reason")})
        if cfg.dry_run and not routed.get("skipped"):
            payload = routed.get("payload") or {}
            price_cents = float(payload.get("yes_price") or payload.get("no_price") or 0)
            if state.position is not None and price_cents > 0:
                contracts_closed = min(exit_decision.contracts, state.position.contracts)
                if contracts_closed > 0:
                    realized_pnl = (price_cents - state.position.avg_entry_price_cents) * contracts_closed
                    stats = state.metadata.setdefault("expiry_stats", {})
                    meta = stats.setdefault(market.ticker, {"realized_pnl_cents": 0.0, "stop_losses": 0})
                    meta["realized_pnl_cents"] = float(meta.get("realized_pnl_cents", 0.0)) + realized_pnl
                    if exit_decision.reason == "stop loss": meta["stop_losses"] = int(meta.get("stop_losses", 0)) + 1
            if exit_decision.action == "sell_all": state.position = None
            elif exit_decision.action == "sell_partial" and state.position and state.position.contracts > exit_decision.contracts:
                state.position.contracts -= exit_decision.contracts
                if exit_decision.reason == "tp1": state.position.tp1_done = True
                if exit_decision.reason == "tp2": state.position.tp2_done = True

def run_loop():
    cfg = load_config(); validate_config(cfg)
    logging.basicConfig(level=getattr(logging, cfg.log_level, logging.INFO))
    logger = logging.getLogger("kalshi-btc15m-bot")
    state = load_state(cfg.state_file)
    event_logger = JsonlLogger()
    rest = KalshiRestClient.build(cfg)
    coinbase = CoinbaseSpotClient()
    while True:
        run_single_cycle(cfg, logger, state, event_logger, rest, coinbase)
        save_state(cfg.state_file, state)
        from time import sleep; sleep(cfg.loop_seconds)

if __name__ == "__main__":
    run_once()
