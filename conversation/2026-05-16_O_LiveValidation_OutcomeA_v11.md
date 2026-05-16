# Kalshi BTC 15m Bot — Live Validation Result: Outcome A (Live Snapshot Success)

Generated: 2026-05-16 PDT  
Author: _O_  
In response to: G approval to attempt live validation

---

## Result: OUTCOME A — LIVE VALIDATION CONFIRMED

The bot connected to the live Kalshi API, fetched a real orderbook, ran the full signal pipeline against live data, and exited cleanly. All pre-run checks passed. No live orders submitted. No secrets in logs.

---

## Pre-Run Checks

| Check | Result |
|-------|--------|
| Correct directory / key files present | PASS |
| `DryRunEnforcementError` present in `app.py` | PASS |
| `StubKalshiClient` hardcoded in `collector.py` | PASS |
| No `dateutil` import in codebase | PASS |
| `BOT_DRY_RUN=true` in `.env` | PASS |
| Test suite | PASS (19 passed) |

---

## Run Details

| Field | Value |
|-------|-------|
| Command | `python -m kalshi_btc15m_bot.collector --dry-run --market-source live --max-cycles 3 --poll-seconds 0` |
| `KALSHI_ENV` | `prod` |
| `BOT_DRY_RUN` | `true` |
| Process exit code | 0 |
| Outcome type | `A_live_snapshot_succeeded` |
| Market ticker seen | `KXBTC15M-26MAY160245-45` |
| Book timestamp seen | `2026-05-16T06:42:57Z` |
| Run ID | `run-4ea3a5f1` |

---

## JSONL Validation

| Check | Result |
|-------|--------|
| Total events | 7 (3x `signal_generated` + 3x `trade_skipped` + 1x `run_summary`) |
| `dry_run=true` on all events | PASS |
| `schema_version=1.0` on all events | PASS |
| `p_raw_semantics=p_yes` on all events | PASS |
| No secrets in logs | PASS |
| `run_summary` count | 1 ✅ |
| `cycle_id=null` on `run_summary` | PASS ✅ |
| `signal_source=null` on `run_summary` | PASS ✅ |
| `signal_sources_by_count` | `{"scaffold_scorer_live": 3}` ✅ |
| `errors` | 0 ✅ |
| No live orders submitted | PASS ✅ |

---

## Cycle Detail

| Cycle | Event | Side | p_raw | Spread | Skip Reason | EV |
|-------|-------|------|-------|--------|-------------|----|
| c0000 | signal_generated → trade_skipped | yes | 0.3054 | 0.70¢ | EV_BELOW_THRESHOLD | -10.74¢ |
| c0001 | signal_generated → trade_skipped | yes | 0.3054 | 0.70¢ | EV_BELOW_THRESHOLD | -11.21¢ |
| c0002 | signal_generated → trade_skipped | yes | 0.3054 | 1.00¢ | EV_BELOW_THRESHOLD | -10.83¢ |

All 3 cycles reached `signal_generated` with live data from `KXBTC15M-26MAY160245-45`. The scorer found a YES signal with `p_raw=0.3054` (fair value ~30.5¢). EV was deeply negative (−10 to −11¢) against the min threshold of +1¢, so all 3 cycles correctly skipped. This is expected and correct guard behavior.

---

## Live API Fixes Applied (v11 → live-ready)

The following live-mode bugs were discovered and fixed during validation:

| Fix | File | Description |
|-----|------|-------------|
| REST orderbook `ts_ms` stamping | `market/orderbook.py` | REST responses don't include `ts_ms`; book was always flagged stale. Now stamped with fetch time. |
| `validate_config` import | `main.py` | Was imported from `config.py` where it doesn't exist; defined locally instead. |
| `NoTradableSignal` exception | `collector.py` | Scorer returning no edge was counted as an error; now correctly counted as a skip. |
| Market discovery retry | `market/discovery.py` | Added 3-attempt retry with 2s wait for brief gaps at market boundaries. |

---

## Approval Status

| Item | Status |
|------|--------|
| Phase 1 pipeline | ACCEPTED |
| Week 2 loop-smoke | ACCEPTED |
| Week 2 replay (all regimes) | ACCEPTED |
| Stale-book replay fidelity | ACCEPTED (v11) |
| `run_summary` metadata | ACCEPTED (v11) |
| Malformed timestamp fail-closed | ACCEPTED (v11) |
| Live API connection | VALIDATED ✅ |
| Live orderbook fetch | VALIDATED ✅ |
| Live signal pipeline (end-to-end) | VALIDATED ✅ |
| `dry_run=true` enforcement | VALIDATED ✅ |
| No live orders submitted | VALIDATED ✅ |
| No secrets in logs | VALIDATED ✅ |
| Live trading | Still prohibited |
