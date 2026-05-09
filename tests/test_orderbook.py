from kalshi_btc15m_bot.market.orderbook import (
    build_book_from_snapshot, best_yes_bid, best_yes_ask, best_no_bid, best_no_ask,
    yes_spread, depth_at_best, is_book_stale, apply_orderbook_delta,
)
from kalshi_btc15m_bot.models import OrderbookState

def _make_book(yes_bids=None, no_bids=None):
    msg = {"orderbook": {"yes": yes_bids or [], "no": no_bids or []}}
    return build_book_from_snapshot(msg)

def test_best_prices_from_snapshot():
    book = _make_book(yes_bids=[[0.45, 50], [0.46, 30]], no_bids=[[0.53, 40]])
    assert abs(best_yes_bid(book) - 46.0) < 0.01
    assert abs(best_no_bid(book) - 53.0) < 0.01
    assert abs(best_yes_ask(book) - 47.0) < 0.01
    assert abs(yes_spread(book) - 1.0) < 0.01
    assert depth_at_best(book, "yes") == 30.0

def test_is_book_stale_with_old_timestamp():
    book = build_book_from_snapshot({"orderbook": {"yes": [], "no": []}, "ts_ms": 1000})
    assert is_book_stale(book, now_ms=1_000_000, max_stale_ms=5000)

def test_is_book_stale_none_ts():
    book = OrderbookState()
    assert is_book_stale(book)
