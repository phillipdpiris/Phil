from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class BotConfig:
    kalshi_env: str
    api_key_id: str
    private_key_path: str
    series_ticker: str
    dry_run: bool
    state_file: Path
    log_level: str
    loop_seconds: int
    order_size: int
    final_minute_order_size: int
    max_spread_cents: float
    min_depth_contracts: float
    normal_min_edge_cents: float
    final_minute_min_edge_cents: float
    slippage_buffer_cents: float
    coinbase_product: str
    coinbase_granularity: int
    coinbase_candles_count: int

    @property
    def rest_base_url(self) -> str:
        return (
            "https://api.elections.kalshi.com/trade-api/v2"
            if self.kalshi_env == "prod"
            else "https://demo-api.kalshi.co/trade-api/v2"
        )

    @property
    def public_rest_base_url(self) -> str:
        return "https://api.elections.kalshi.com/trade-api/v2"

    @property
    def ws_url(self) -> str:
        return (
            "wss://api.elections.kalshi.com/trade-api/ws/v2"
            if self.kalshi_env == "prod"
            else "wss://demo-api.kalshi.co/trade-api/ws/v2"
        )


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> BotConfig:
    load_dotenv()
    return BotConfig(
        kalshi_env=os.getenv("KALSHI_ENV", "demo").strip().lower(),
        api_key_id=os.getenv("KALSHI_API_KEY_ID", "").strip(),
        private_key_path=os.getenv("KALSHI_PRIVATE_KEY_PATH", "").strip(),
        series_ticker=os.getenv("KALSHI_SERIES_TICKER", "kxbtc15m").strip(),
        dry_run=_env_bool("BOT_DRY_RUN", True),
        state_file=Path(os.getenv("BOT_STATE_FILE", "kalshi_btc15m_state.json")),
        log_level=os.getenv("BOT_LOG_LEVEL", "INFO").strip().upper(),
        loop_seconds=int(os.getenv("BOT_LOOP_SECONDS", "5")),
        order_size=int(os.getenv("BOT_ORDER_SIZE", "10")),
        final_minute_order_size=int(os.getenv("BOT_FINAL_MINUTE_ORDER_SIZE", "4")),
        max_spread_cents=float(os.getenv("BOT_MAX_SPREAD_CENTS", "4.0")),
        min_depth_contracts=float(os.getenv("BOT_MIN_DEPTH_CONTRACTS", "5.0")),
        normal_min_edge_cents=float(os.getenv("BOT_NORMAL_MIN_EDGE_CENTS", "5.0")),
        final_minute_min_edge_cents=float(os.getenv("BOT_FINAL_MINUTE_MIN_EDGE_CENTS", "8.0")),
        slippage_buffer_cents=float(os.getenv("BOT_SLIPPAGE_BUFFER_CENTS", "1.0")),
        coinbase_product=os.getenv("COINBASE_PRODUCT", "BTC-USD").strip(),
        coinbase_granularity=int(os.getenv("COINBASE_GRANULARITY", "60")),
        coinbase_candles_count=int(os.getenv("COINBASE_CANDLES_COUNT", "30")),
    )


def validate_config(cfg: BotConfig) -> None:
    if cfg.kalshi_env not in {"demo", "prod"}:
        raise ValueError("KALSHI_ENV must be 'demo' or 'prod'")
    if cfg.loop_seconds <= 0:
        raise ValueError("BOT_LOOP_SECONDS must be > 0")
    if cfg.order_size <= 0 or cfg.final_minute_order_size <= 0:
        raise ValueError("Order sizes must be > 0")
    if cfg.kalshi_env == "prod" and not cfg.dry_run:
        if not cfg.api_key_id:
            raise ValueError("KALSHI_API_KEY_ID is required for live trading")
        if not cfg.private_key_path:
            raise ValueError("KALSHI_PRIVATE_KEY_PATH is required for live trading")
