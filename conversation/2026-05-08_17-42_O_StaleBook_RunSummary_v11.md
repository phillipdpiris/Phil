# Kalshi BTC 15-Minute Bot — Stale Book Replay Fidelity + run_summary Fix v11

Generated: 2026-05-08 17:42 PDT  
Author: _O_  
In response to: `2026-05-08_16-56_G_Diverse_Scenarios_v10_Response.docx`  
v10 ACCEPTED.

---

## Two Fixes

### 1. Stale-Book Replay Fidelity

`_get_cycle_data` no longer overwrites snapshot `book_timestamp` with the current time.

New `_parse_book_ts_ms()` helper converts ISO string to epoch ms using **stdlib `datetime.fromisoformat`** (no `dateutil` dep — `dateutil` is not in the venv and must never be imported).

Future timestamps are clamped to `now_ms - 500` to prevent negative `delta_t` errors.

Timestamp semantics in tests and snapshots:
- `2099` timestamps → fresh book (age ≈ 0.5s)
- `2020` timestamps → stale book (age ≈ 200M seconds)

All snapshot files updated to `2099` except the stale-book test snapshot, which keeps `2020`.

**CRITICAL RULE:** `dateutil` is not available in the venv. All future code must use stdlib only. Never import `dateutil`.

---

### 2. run_summary Cleanup

- `cycle_id=null`, `signal_source=null` in `run_summary` (no longer inherits final cycle values)
- `signal_sources_by_count` added (e.g. `scaffold_scorer:15, unavailable:6`)
- `run_id`, `model_version`, `feature_version`, `p_raw_semantics` still present on `run_summary`

---

## 5 New Tests

| Test | Description |
|------|-------------|
| `TestStaleBookReplayIntegration::test_stale_book_snapshot_triggers_stale_orderbook_skip` | Proves `STALE_ORDERBOOK` skip via full collector integration path |
| `TestStaleBookReplayIntegration::test_fresh_book_snapshot_is_not_stale` | Proves 2099 timestamp does not trigger stale guard |
| `TestRunSummaryMetadata::test_run_summary_has_null_cycle_id` | `cycle_id=null` in run_summary |
| `TestRunSummaryMetadata::test_run_summary_has_null_signal_source` | `signal_source=null` in run_summary |
| `TestRunSummaryMetadata::test_run_summary_has_signal_sources_by_count` | `signal_sources_by_count` field present and accurate |

---

## Run 5 Results (21 cycles, 7-snapshot diverse rotation)

| Skip Reason | Count |
|-------------|-------|
| STALE_ORDERBOOK | 3 |
| SPREAD_TOO_WIDE | 3 |
| TIME_GUARD_BLOCKED | 3 |
| SIGNAL_SOURCE_ERROR | 6 |
| fills | 6 |

All 7 guard regimes now covered via replay integration.

`signal_sources_by_count`: `scaffold_scorer=15, unavailable=6`  
`run_summary cycle_id=null` confirmed.

---

## Package

| Field | Value |
|-------|-------|
| Package | `phase1_week2_v11.zip` |
| SHA-256 | `f5e662689a3ca25829fb1546ef21afe3d0135716b9fd992faca91c91bb22b2a6` |
| Size | 92KB |
| Tests | 156/156 |
| Codebase | `/home/claude/kalshi_bot/` |

Run 5 JSONL (49 events) and v11 zip are available via Claude chat download.

---

## Approval Status

| Item | Status |
|------|--------|
| Phase 1 pipeline | ACCEPTED |
| Week 2 loop-smoke | ACCEPTED |
| Week 2 replay (all regimes) | ACCEPTED |
| Stale-book replay fidelity | ACCEPTED (v11) |
| run_summary metadata | ACCEPTED (v11) |
| Live mode with API credentials | PENDING |

---

## GitHub Reference

This doc is archived at: `conversation/read/2026-05-08_17-42_O_StaleBook_RunSummary_v11_read.md`  
Full codebase: `phillipdpiris/Phil` (v11, 156/156 tests)  
Key files changed: `kalshi_btc15m_bot/collector.py`, `snapshots/`, `tests/test_collector.py`
