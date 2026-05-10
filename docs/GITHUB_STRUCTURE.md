# GitHub Repo Structure & G/O Workflow Guide

Repo: `phillipdpiris/Phil`  
Codebase version: v11 (156/156 tests, SHA-256: `f5e662689a3ca25829fb1546ef21afe3d0135716b9fd992faca91c91bb22b2a6`)

---

## Folder Map

```
Phil/
├── README.md                        # Project overview, run commands, current status
├── .gitignore
├── pyproject.toml                   # Package name, Python version, pytest config
├── requirements.txt                 # Runtime + test deps (no dateutil)
│
├── config/
│   └── phase1.yaml                  # LOCKED Phase 1 config — do not modify without approval
│
├── docs/
│   ├── ARCHITECTURE_OVERVIEW.md     # Package layout, key invariants, module roles
│   ├── GITHUB_STRUCTURE.md          # THIS FILE — repo map + G/O workflow
│   ├── RISK_AND_REVIEW_GUIDE.md     # Trading rules, risk controls, review checklist
│   ├── SOURCE_NOTES.md              # Kalshi API assumptions (signing, orderbook shape, etc.)
│   └── STARTER_AGENT_SETUP.md      # Handoff doc for a new coding agent
│
├── kalshi_btc15m_bot/               # Main Python package
│   ├── __init__.py
│   ├── app.py                       # Phase 1 canonical pipeline (DryRunEnforcementError, Phase1Pipeline)
│   ├── cli.py                       # CLI: replay + compare-exits commands
│   ├── collector.py                 # Week 2 collector: loop-smoke / replay / live modes
│   ├── config.py                    # BotConfig dataclass + load_config() — NEVER use BotConfig() directly
│   ├── main.py                      # Scaffold entry point (run_once, run_single_cycle, run_loop)
│   ├── models.py                    # Shared dataclasses (OrderbookState, PositionState, etc.)
│   ├── portfolio.py                 # Position reconciliation against live Kalshi account
│   ├── state_store.py               # load_state / save_state / clear_position
│   │
│   ├── analytics/
│   │   ├── lifecycle_logger.py      # Phase 1 JSONL logger (p_raw_semantics='p_yes' on every event)
│   │   ├── logger.py                # Simple JsonlLogger (market/signal/order/exit events)
│   │   ├── replay.py                # Offline PnL replay from JSONL session logs
│   │   └── reports.py              # Daily PnL, strategy attribution, late-exit giveback
│   │
│   ├── clients/
│   │   ├── coinbase_spot.py         # Coinbase REST: get_candles, get_last_trade
│   │   ├── kalshi_rest.py           # Kalshi REST client — ALWAYS use KalshiRestClient.build(cfg)
│   │   └── kalshi_ws.py             # Kalshi WebSocket: subscribe, snapshot, iter_messages
│   │
│   ├── execution/
│   │   ├── exits.py                 # Exit engine: TP1/TP2/stop-loss/late-flatten decisions
│   │   ├── guard_router.py          # Phase 1 guard router (stale/spread/depth/time/price checks)
│   │   ├── guards.py                # Scaffold guards (spread_ok, depth_ok, time_ok, net_edge_ok)
│   │   ├── order_mapper.py          # V2 payload builder with validation (OrderMappingError)
│   │   ├── orders.py                # Raw order builders (build_limit_buy_yes, etc.)
│   │   └── router.py               # Entry/exit routing (resting vs aggressive limit)
│   │
│   ├── market/
│   │   ├── clocks.py                # Phase detection from open/close times
│   │   ├── discovery.py             # Find open BTC 15m market, refresh, settled history
│   │   ├── fees.py                  # Fee estimation, net_edge_cents helper
│   │   ├── orderbook.py             # Book build/delta/query helpers (best bid/ask, spread, stale check)
│   │   └── queue.py                 # Queue position helpers
│   │
│   ├── risk/
│   │   └── clustering_engine.py     # 5-constraint clustering guard (rate/side/total/strike/notional)
│   │
│   └── strategy/
│       ├── ev_engine.py             # EV computation with all cost components
│       ├── fair_value.py            # Phase-weighted fair YES/NO probability model
│       ├── features.py              # BTC return, momentum, mean-reversion, vol feature computation
│       ├── fill_model.py            # Fill probability estimate from price position in spread
│       ├── latency_engine.py        # Probability and fill decay over signal/book age
│       ├── phases.py                # Phase-specific weight dictionaries
│       ├── probability_adjuster.py  # Shrinkage (p_raw → p_shrunk), validation
│       ├── recent_context.py        # Recent settled market context (outcome/continuation/reversal rates)
│       ├── scorer.py                # Best entry decision: combine features → edge → side selection
│       └── strategy_router.py      # Route decision to strategy name, check EV threshold
│
├── snapshots/                       # Replay snapshot files for collector dry-runs
│   ├── sample_week2_snapshot.json
│   ├── sample_week2_diverse_snapshot.json   # All guard regimes (spread, stale, time, EV)
│   └── sample_week2_scorer_snapshot.json    # Deterministic scorer fixture (bearish NO signal)
│
├── tests/                           # 156 tests — all passing on v11
│   ├── test_cli.py
│   ├── test_clocks.py
│   ├── test_collector.py            # Loop-smoke, replay, stale-book, run_summary metadata
│   ├── test_exits_and_guards.py
│   ├── test_fees.py
│   ├── test_integration.py          # Full Phase 1 pipeline end-to-end
│   ├── test_orderbook.py
│   ├── test_phase1.py               # Unit tests: prob_adjuster, latency, fill, EV, clustering, logger, guards
│   ├── test_portfolio_reconcile.py
│   ├── test_recent_context.py
│   ├── test_replay.py
│   ├── test_scoring.py
│   └── test_signature.py
│
└── conversation/                    # G/O exchange — mirrors Google Drive Conversation folder
    ├── .gitkeep
    ├── YYYY-MM-DD_HH-MM_O_Description.md   # Active O response (posted by O after each cycle)
    └── read/
        ├── .gitkeep
        └── YYYY-MM-DD_HH-MM_O_Description_read.md  # Archived after G reads (renamed + moved)
```

---

## G/O Workflow on GitHub

This mirrors the Google Drive conversation pattern exactly.

### Naming conventions

| Author | File name pattern | Location |
|--------|-------------------|----------|
| O (Claude) | `YYYY-MM-DD_HH-MM_O_Description.md` | `conversation/` |
| G (reviewer) | Posts feedback directly in chat or uploads a doc | — |
| Archived | `YYYY-MM-DD_HH-MM_O_Description_read.md` | `conversation/read/` |

Timestamps are PDT (UTC−7). Example: `2026-05-10_10-48_O_GitHubStructure_v11.md`

### Response cycle (GitHub equivalent)

1. **G sends feedback** in chat (or uploads a doc)
2. **O reads it** fully
3. **O renames the previous active O doc** — adds `_read` suffix in filename
4. **O moves the renamed file** to `conversation/read/`
5. **O fixes code / runs tests / verifies**
6. **O posts new O doc** at `conversation/YYYY-MM-DD_HH-MM_O_Description.md`
7. **O links to the new file** in chat immediately
8. **O updates state** (README or state doc) if package changed

### The `_read` rule (CRITICAL)

Before moving any file to `conversation/read/`, always rename it with `_read` suffix first:

```
2026-05-10_10-48_O_GitHubStructure_v11.md
         ↓  (rename via new commit)
2026-05-10_10-48_O_GitHubStructure_v11_read.md
         ↓  (move via new path in commit)
conversation/read/2026-05-10_10-48_O_GitHubStructure_v11_read.md
```

On GitHub, "rename + move" = push a new file at the new path and delete the old one.

---

## Key Invariants (never change without approval)

- `p_raw` always = P(YES settles). Never side-local probability.
- `StubKalshiClient` always used in collector. No live orders ever.
- `DryRunEnforcementError` raised if `dry_run=False`.
- `load_config()` — never `BotConfig()` directly.
- `KalshiRestClient.build(cfg)` — never `KalshiRestClient(cfg)` directly.
- Scaffold files untouched: `main.py`, `config.py`, `fair_value.py`, `scorer.py`, `guards.py`.
- All guard regimes testable via replay snapshot `book_timestamp`.

---

## Quick-start Commands

```bash
# Install
python -m venv .venv && .venv/bin/pip install -r requirements.txt

# Run all 156 tests
.venv/bin/pytest

# Loop-smoke (no API needed)
python -m kalshi_btc15m_bot.collector --loop-smoke --max-cycles 5

# Replay (no API needed)
python -m kalshi_btc15m_bot.collector --dry-run --market-source replay \
  --snapshot-file snapshots/sample_week2_diverse_snapshot.json --max-cycles 7

# Phase 1 smoke test
python -m kalshi_btc15m_bot.app --smoke
```

---

## Current Status (v11)

| Item | Status |
|------|--------|
| Phase 1 pipeline | ACCEPTED |
| Week 2 loop-smoke | ACCEPTED |
| Week 2 replay (all regimes) | ACCEPTED |
| Stale-book replay fidelity | ACCEPTED |
| run_summary metadata | ACCEPTED |
| Live mode with API credentials | PENDING |
| GitHub push | COMPLETE (70 files) |
