from __future__ import annotations
import logging
from datetime import datetime, timezone
from .analytics.logger import JsonlLogger
from .clients.coinbase_spot import CoinbaseSpotClient
from .clients.kalshi_rest import KalshiRestClient
from .config import load_config
from .execution.guards import single_position_ok
from .portfolio import reconcile_position_state
from .execution.exits import build_exit_decision
from .execution.router import route_entry, route_exit
from .market.clocks import phase_from_clock, remaining_seconds
from .market.discovery import find_open_btc15m_market, refresh_market
from .market.orderbook import (best_no_ask, best_no_bid, best_yes_ask, best_yes_bid,
    build_book_from_snapshot, depth_imbalance, fetch_rest_orderbook_snapshot,
    is_book_stale, no_spread, yes_spread)
from .models import OrderbookState
from .state_store import load_state, save_state
from .strategy.features import (compute_btc_returns, compute_mean_reversion_features,
    compute_momentum_features, compute_volatility_features)
from .strategy.recent_context import build_recent_context_summary, fetch_recent_contract_context
from .strategy.scorer import best_entry_decision

def build_feature_bundle(candles):
    features = {}
    features.update(compute_btc_returns(candles))
    features.update(compute_momentum_features(candles))
    features.update(compute_mean_reversion_features(candles))
    features.update(compute_volatility_features(candles))
    return features

def validate_config(cfg):
    if cfg.kalshi_env not in {"demo","prod"}:
        raise ValueError("KALSHI_ENV must be 'demo' or 'prod'")

def run_once():
    cfg=load_config(); validate_config(cfg)
    print("run_once: use collector.py --dry-run --market-source live for live validation")

def run_loop():
    print("run_loop: use collector.py for loop operation")

if __name__=="__main__":
    run_once()
