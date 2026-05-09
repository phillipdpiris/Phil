# Architecture Overview

See full architecture document in the project. This file summarises the key structure.

## Package layout

- `kalshi_btc15m_bot/app.py` — Phase 1 canonical pipeline entry point
- `kalshi_btc15m_bot/collector.py` — Week 2 dry-run collector (loop-smoke / replay / live)
- `kalshi_btc15m_bot/config.py` — BotConfig + load_config()
- `kalshi_btc15m_bot/strategy/` — Fair value, scorer, EV engine, probability pipeline
- `kalshi_btc15m_bot/execution/` — Guard router, order mapper
- `kalshi_btc15m_bot/market/` — Orderbook, clocks, discovery, fees
- `kalshi_btc15m_bot/analytics/` — Lifecycle logger, replay
- `kalshi_btc15m_bot/risk/` — Clustering engine
- `tests/` — 156 tests covering all modules

## Key invariants

- p_raw always = P(YES settles). Never side-local probability.
- StubKalshiClient always used in collector. No live orders ever.
- DryRunEnforcementError raised if dry_run=False.
- All guard regimes testable in replay via snapshot book_timestamp.
