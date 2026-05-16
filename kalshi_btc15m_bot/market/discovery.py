from __future__ import annotations
import time
from datetime import datetime, timezone
from ..clients.kalshi_rest import KalshiRestClient
from ..models import MarketSnapshot

def parse_iso8601(ts):
    if ts.endswith("Z"): ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts).astimezone(timezone.utc)

def market_snapshot_from_payload(payload):
    if "market" in payload and isinstance(payload["market"], dict):
        payload = payload["market"]
    return MarketSnapshot(ticker=payload["ticker"], title=payload.get("title",""),
                          series_ticker=payload.get("series_ticker",""),
                          open_time=parse_iso8601(payload["open_time"]),
                          close_time=parse_iso8601(payload["close_time"]),
                          status=payload.get("status","unknown"), raw=payload)

def find_open_btc15m_market(rest, series_ticker):
    # Kalshi markets have status=initialized; querying with status=open returns them correctly.
    # Retry up to 3 times with a short wait to handle brief gaps between markets at boundaries.
    markets = []
    for attempt in range(3):
        payload = rest.public_get("/markets", params={"status":"open","series_ticker":series_ticker,"limit":100})
        markets = payload.get("markets",[])
        if markets:
            break
        if attempt < 2:
            time.sleep(2)
    if not markets:
        raise RuntimeError(f"No markets found for series_ticker={series_ticker} after 3 attempts")
    now = datetime.now(timezone.utc)
    future = [m for m in markets if parse_iso8601(m["close_time"]) > now]
    if future: markets = future
    markets.sort(key=lambda m: parse_iso8601(m["close_time"]))
    return market_snapshot_from_payload(markets[0])

def refresh_market(rest, ticker):
    return market_snapshot_from_payload(rest.public_get(f"/markets/{ticker}"))

def get_recent_settled_markets(rest, series_ticker, limit=20):
    payload = rest.public_get("/historical/markets", params={"series_ticker":series_ticker,"limit":limit})
    return [market_snapshot_from_payload(item) for item in payload.get("markets",[])]
