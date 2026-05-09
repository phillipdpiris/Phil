# Source Notes

These notes capture the main API and help-center assumptions the scaffold was built around.

- Authenticated REST requests use:
  - `KALSHI-ACCESS-KEY`
  - `KALSHI-ACCESS-TIMESTAMP`
  - `KALSHI-ACCESS-SIGNATURE`
- Signature payload should be:
  - `timestamp_ms + HTTP_METHOD + path_from_root`
  - exclude query parameters from the signing path
- WebSocket sessions are authenticated
- `orderbook_delta` supports snapshots and deltas
- recent changelog mentions `get_snapshot` support for `orderbook_delta`
- orderbooks expose bids and reciprocal pricing logic matters for asks
- market close should be taken from market metadata / timeline
- portfolio cash-out depends on available liquidity
- fees are real and can vary by market

Verify these assumptions against the live docs before enabling live trading.
