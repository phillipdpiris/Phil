from __future__ import annotations
import json, time
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Optional, Tuple
from ..clients.kalshi_rest import KalshiRestClient
from ..market.discovery import get_recent_settled_markets

_CACHE: dict = {}
_CACHE_FILE = Path("recent_context_cache.json")
_CACHE_TTL_SECONDS = 300

def _load_disk_cache():
    if not _CACHE_FILE.exists(): return {}
    try: return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except: return {}

def _save_disk_cache(cache):
    try: _CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
    except: return

def _cache_key(series_ticker, limit): return f"{series_ticker}:{limit}"

def fetch_recent_contract_context(rest, series_ticker, limit=20):
    now = time.time()
    key = _cache_key(series_ticker, limit)
    cached = _CACHE.get(key)
    if cached and now - cached.get("ts", 0) <= _CACHE_TTL_SECONDS:
        return list(cached.get("markets", []))
    disk = _load_disk_cache().get(key)
    if isinstance(disk, dict) and now - disk.get("ts", 0) <= _CACHE_TTL_SECONDS:
        markets = list(disk.get("markets", []))
        _CACHE[key] = {"ts": disk.get("ts", now), "markets": markets}
        return markets
    try:
        markets = get_recent_settled_markets(rest, series_ticker=series_ticker, limit=limit)
        raw = [m.raw for m in markets]
    except: return []
    entry = {"ts": now, "markets": raw}
    _CACHE[key] = entry
    disk_cache = _load_disk_cache()
    disk_cache[key] = entry
    _save_disk_cache(disk_cache)
    return list(raw)

def compute_outcome_yes_rate(markets):
    resolved = [1 if m.get("result")=="yes" else 0 for m in markets if m.get("result") in {"yes","no"}]
    return mean(resolved) if resolved else 0.5

def _direction(delta, tol=1e-6):
    if delta > tol: return 1
    if delta < -tol: return -1
    return 0

def _extract_open_mid_close(market):
    if "open_price_cents" in market and "close_price_cents" in market:
        try:
            open_p = float(market["open_price_cents"])
            close_p = float(market["close_price_cents"])
            mid_p = market.get("mid_price_cents")
            mid_p = float(mid_p) if mid_p is not None else (open_p+close_p)/2.0
            return open_p, mid_p, close_p
        except: pass
    seq = market.get("candles") or market.get("path")
    if isinstance(seq, list) and seq:
        prices = []
        for row in seq:
            pv = None
            if isinstance(row, dict): pv = row.get("yes_price_cents") or row.get("price_cents") or row.get("price") or row.get("close")
            elif isinstance(row, (list,tuple)) and row: pv = row[-1]
            if pv is None: continue
            try: prices.append(float(pv))
            except: continue
        if len(prices) >= 2:
            return prices[0], prices[len(prices)//2], prices[-1]
    return None

def compute_open_to_mid_continuation_rate(markets):
    flags = []
    for m in markets:
        t = _extract_open_mid_close(m)
        if t is None: continue
        o,mid,c = t
        d1,d2 = _direction(mid-o), _direction(c-o)
        if d1==0 or d2==0: continue
        flags.append(1 if d1==d2 else 0)
    return mean(flags) if flags else 0.5

def compute_mid_to_close_reversal_rate(markets):
    flags = []
    for m in markets:
        t = _extract_open_mid_close(m)
        if t is None: continue
        o,mid,c = t
        d1,d2 = _direction(mid-o), _direction(c-mid)
        if d1==0 or d2==0: continue
        flags.append(1 if d1!=d2 else 0)
    return mean(flags) if flags else 0.5

def build_recent_context_summary(markets):
    return {"outcome_yes_rate": compute_outcome_yes_rate(markets),
            "open_mid_continuation_rate": compute_open_to_mid_continuation_rate(markets),
            "mid_close_reversal_rate": compute_mid_to_close_reversal_rate(markets),
            "sample_size": len(markets)}
