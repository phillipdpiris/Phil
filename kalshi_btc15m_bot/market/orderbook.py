from __future__ import annotations
from bisect import bisect_left
import time
from ..clients.kalshi_rest import KalshiRestClient
from ..models import OrderbookLevel, OrderbookState

def _normalize_levels(raw_levels):
    levels = [OrderbookLevel(price_cents=round(float(p)*100.0,6), size=float(s)) for p,s in raw_levels]
    levels.sort(key=lambda l: l.price_cents)
    return levels

def build_book_from_snapshot(msg: dict) -> OrderbookState:
    data = msg.get("msg", msg)
    orderbook = data.get("orderbook") or data.get("orderbook_fp") or {}
    yes = orderbook.get("yes") or orderbook.get("yes_dollars") or []
    no = orderbook.get("no") or orderbook.get("no_dollars") or []
    return OrderbookState(yes_bids=_normalize_levels(yes), no_bids=_normalize_levels(no), ts_ms=data.get("ts_ms"))

def fetch_rest_orderbook_snapshot(rest: KalshiRestClient, ticker: str) -> OrderbookState:
    return build_book_from_snapshot(rest.public_get(f"/markets/{ticker}/orderbook"))

def _apply_side_delta(levels, price_cents, new_size):
    prices = [l.price_cents for l in levels]
    idx = bisect_left(prices, price_cents)
    if idx < len(levels) and abs(levels[idx].price_cents - price_cents) < 1e-9:
        if new_size <= 0: levels.pop(idx)
        else: levels[idx].size = new_size
        return
    if new_size > 0:
        levels.insert(idx, OrderbookLevel(price_cents=price_cents, size=new_size))

def apply_orderbook_delta(book: OrderbookState, msg: dict) -> None:
    data = msg.get("msg", msg)
    side = data.get("side")
    price = data.get("price_dollars") or data.get("price")
    price_cents = round(float(price)*100.0, 6)
    delta_size = data.get("delta") or data.get("delta_fp") or data.get("size")
    new_size = float(delta_size)
    target = book.yes_bids if side == "yes" else book.no_bids
    _apply_side_delta(target, price_cents, new_size)
    if data.get("ts_ms") is not None:
        book.ts_ms = int(data["ts_ms"])

def best_yes_bid(book): return book.yes_bids[-1].price_cents if book.yes_bids else 0.0
def best_no_bid(book): return book.no_bids[-1].price_cents if book.no_bids else 0.0
def best_yes_ask(book): return 100.0 - best_no_bid(book) if book.no_bids else 100.0
def best_no_ask(book): return 100.0 - best_yes_bid(book) if book.yes_bids else 100.0
def yes_spread(book): return max(0.0, best_yes_ask(book) - best_yes_bid(book))
def no_spread(book): return max(0.0, best_no_ask(book) - best_no_bid(book))
def depth_at_best(book, side):
    if side == "yes": return book.yes_bids[-1].size if book.yes_bids else 0.0
    return book.no_bids[-1].size if book.no_bids else 0.0
def mid_yes(book): return (best_yes_bid(book)+best_yes_ask(book))/2.0
def mid_no(book): return (best_no_bid(book)+best_no_ask(book))/2.0
def depth_imbalance(book):
    y=sum(l.size for l in book.yes_bids); n=sum(l.size for l in book.no_bids)
    t=y+n; return y/t if t>0 else 0.5
def is_book_stale(book, now_ms=None, max_stale_ms=5000):
    if book.ts_ms is None: return True
    if now_ms is None: now_ms=int(time.time()*1000)
    return now_ms-int(book.ts_ms)>max_stale_ms
def summarize_top_levels(book, side, depth=3):
    levels=book.yes_bids if side=="yes" else book.no_bids
    if not levels: return {"levels":[],'total_size':0.0}
    top=levels[-depth:][::-1]
    return {"levels":[(l.price_cents,l.size) for l in top],"total_size":sum(l.size for l in top)}
