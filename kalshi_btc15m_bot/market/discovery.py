from __future__ import annotations
from datetime import datetime, timezone
from ..clients.kalshi_rest import KalshiRestClient
from ..models import MarketSnapshot

def parse_iso8601(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts).astimezone(timezone.utc)

def market_snapshot_from_payload(payload: dict) -> MarketSnapshot:
    if "market" in payload and isinstance(payload["market"], dict):
        payload = payload["market"]
    return MarketSnapshot(ticker=payload["ticker"], title=payload.get("title", ""),
                          series_ticker=payload.get("series_ticker", ""),
                          open_time=parse_iso8601(payload["open_time"]),
                          close_time=parse_iso8601(payload["close_time"]),
                          status=payload.get("status", "unknown"), raw=payload)

def find_open_btc15m_market(rest: KalshiRestClient, series_ticker: str) -> MarketSnapshot:
    payload = rest.public_get("/markets", params={"status": "open", "series_ticker": series_ticker, "limit": 100})
    markets = payload.get("markets", [])
    if not markets:
        payload = rest.public_get("/markets", params={"series_ticker": series_ticker, "limit": 100})
        markets = payload.get("markets", [])
    if not markets:
        raise RuntimeError(f"No markets found for series_ticker={series_ticker}")
    now = datetime.now(timezone.utc)
    future_markets = [m for m in markets if parse_iso8601(m["close_time"]) > now]
    if future_markets:
        markets = future_markets
    markets.sort(key=lambda m: parse_iso8601(m["close_time"]))
    return market_snapshot_from_payload(markets[0])

def refresh_market(rest: KalshiRestClient, ticker: str) -> MarketSnapshot:
    return market_snapshot_from_payload(rest.public_get(f"/markets/{ticker}"))

def get_recent_settled_markets(rest: KalshiRestClient, series_ticker: str, limit: int = 20) -> list[MarketSnapshot]:
    payload = rest.public_get("/historical/markets", params={"series_ticker": series_ticker, "limit": limit})
    return [market_snapshot_from_payload(item) for item in payload.get("markets", [])]
