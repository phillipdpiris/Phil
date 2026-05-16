# GitHub Repo Structure & G/O Workflow Guide

Repo: `phillipdpiris/Phil`  
Codebase version: v11 + live-mode fixes (live validation confirmed 2026-05-16)

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
│   └── STARTER_AGENT_SETUP.md       # Handoff doc for a new coding agent
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
│   │   └── reports.py               # Daily PnL, strategy attribution, late-exit giveback
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
│   │   └── router.py                # Entry/exit routing (resting vs aggressive limit)
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
│       └── strategy_router.py       # Route decision to strategy name, check EV threshold
│
├── snapshots/                       # Replay snapshot files for collector dry-runs
│   ├── sample_week2_snapshot.json
│   ├── sample_week2_diverse_snapshot.json   # All guard regimes (spread, stale, time, EV)
│   └── sample_week2_scorer_snapshot.json    # Deterministic scorer fixture (bearish NO signal)
│
├── tests/                           # pytest suite
│   ├── test_cli.py
│   ├── test_clocks.py
│   ├── test_collector.py            # Loop-smoke, replay, stale-book, run_summary, timestamp invalid policy
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
├── verification/                    # G audit artifacts and SHA lookups
│   ├── last_sha.json                # Written by get-file-sha workflow — O reads this for file updates
│   └── live_validation_*.jsonl      # Raw JSONL from live validation runs
│
└── conversation/                    # Strict-active G/O exchange
    ├── .gitkeep
    ├── YYYY-MM-DD_HH-MM_G_Description.md   # Current unprocessed G doc(s) only
    ├── YYYY-MM-DD_HH-MM_O_Description.md   # Current active O response only
    └── read/
        ├── .gitkeep
        ├── YYYY-MM-DD_HH-MM_G_Description_read.md
        └── YYYY-MM-DD_HH-MM_O_Description_read.md
```

---

## G/O Workflow on GitHub

GitHub is the canonical workspace for code and G/O Markdown handoffs.

### Naming conventions

| Author | Active file name pattern | Active location | Archived pattern | Archive location |
|--------|--------------------------|-----------------|------------------|------------------|
| G (reviewer) | `YYYY-MM-DD_HH-MM_G_Description.md` | `conversation/` | `YYYY-MM-DD_HH-MM_G_Description_read.md` | `conversation/read/` |
| O (coding agent) | `YYYY-MM-DD_HH-MM_O_Description.md` | `conversation/` | `YYYY-MM-DD_HH-MM_O_Description_read.md` | `conversation/read/` |

Timestamps are PDT (UTC−7). Example: `2026-05-12_10-00_O_WorkflowCleanup_v11.md`

### Strict-active `conversation/` convention — Option A

`conversation/` must contain only:

1. Current unprocessed G doc(s)
2. Current active O response doc
3. `.gitkeep`

Once O has processed a G doc, both the processed G doc and the O response addressing it move to `conversation/read/` with `_read` suffix.

### Response cycle

1. G posts a Markdown handoff in `conversation/` using the G naming convention.
2. O reads the G handoff fully.
3. O implements code/doc changes and records commit SHAs.
4. O creates a new active O Markdown response in `conversation/`.
5. Processed G/O files are copied or moved into `conversation/read/` with `_read` suffix.
6. Stale originals in `conversation/` are deleted via the `delete-file` workflow.
7. O links or names the new active O doc in chat immediately.
8. O updates docs/README/state only if package behavior, workflow, or status changed.

### The `_read` rule (CRITICAL)

Before moving any file to `conversation/read/`, always rename it with `_read` suffix first:

```
2026-05-12_10-00_O_WorkflowCleanup_v11.md
         ↓  (rename via new path)
2026-05-12_10-00_O_WorkflowCleanup_v11_read.md
         ↓  (move via new path in commit)
conversation/read/2026-05-12_10-00_O_WorkflowCleanup_v11_read.md
```

### G Document Convention — SHA Required

When G's response references or approves changes to specific files, G must include the current blob SHA for each file. This allows O to update files directly without a separate SHA-fetch round trip.

**Format in G docs:**

```
file: kalshi_btc15m_bot/collector.py
sha: <blob SHA>
```

**How G gets a file's SHA:**

Option 1 — Trigger a `get-file-sha` issue (label: `get-file-sha`, body: `path: <file_path>`), then read:
`https://raw.githubusercontent.com/phillipdpiris/Phil/main/verification/last_sha.json`

Option 2 — GitHub UI: navigate to the file → the SHA is the short commit hash shown next to the filename.

This convention applies to all future G docs where file changes are discussed or approved.

---

## Key Invariants (never change without approval)

- `p_raw` always = P(YES settles). Never side-local probability.
- `StubKalshiClient` always used in collector. No live orders ever.
- `DryRunEnforcementError` raised if `dry_run=False`.
- `load_config()` — never `BotConfig()` directly.
- `KalshiRestClient.build(cfg)` — never `KalshiRestClient(cfg)` directly.
- Scaffold files untouched unless explicitly approved: `main.py`, `config.py`, `fair_value.py`, `scorer.py`, `guards.py`.
- All guard regimes testable via replay snapshot `book_timestamp`.
- Malformed or missing `book_timestamp` fails closed in replay/live mode with `SNAPSHOT_TIMESTAMP_INVALID`.
- Loop-smoke mode may use synthetic fallback timestamps because snapshots are generated in-process.

---

## Quick-start Commands

```bash
# Install
python -m venv .venv && .venv/bin/pip install -r requirements.txt

# Run all tests
.venv/bin/pytest

# Loop-smoke (no API needed)
python -m kalshi_btc15m_bot.collector --loop-smoke --max-cycles 5

# Replay (no API needed)
python -m kalshi_btc15m_bot.collector --dry-run --market-source replay \
  --snapshot-file snapshots/sample_week2_diverse_snapshot.json --max-cycles 7

# Phase 1 smoke test
python -m kalshi_btc15m_bot.app --smoke

# Live dry-run (requires .env with Kalshi credentials)
python -m kalshi_btc15m_bot.collector --dry-run --market-source live --max-cycles 3
```

---

## Current Status

| Item | Status |
|------|--------|
| Phase 1 pipeline | ACCEPTED |
| Week 2 loop-smoke | ACCEPTED |
| Week 2 replay (all regimes) | ACCEPTED |
| Stale-book replay fidelity | ACCEPTED |
| run_summary metadata | ACCEPTED |
| Malformed timestamp fail-closed | ACCEPTED |
| Live API connection | VALIDATED |
| Live orderbook fetch | VALIDATED |
| Live signal pipeline end-to-end | VALIDATED |
| dry_run enforcement in live mode | VALIDATED |
| No live orders in live mode | VALIDATED |
| Full 156-test suite | PASSING |
| Live trading | PROHIBITED |
