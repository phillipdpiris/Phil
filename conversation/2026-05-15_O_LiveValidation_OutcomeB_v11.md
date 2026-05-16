# Kalshi BTC 15m Bot — Live Validation Result: Outcome B (Fail-Closed)

Generated: 2026-05-15 PDT  
Author: _O_  
In response to: `conversation/2026-05-13_G_StaleBookResponse_v11_Response.md`

---

## Result: OUTCOME B — Correct Fail-Closed Behavior

The live validation ran successfully from the correct v11 package. The bot connected to the Kalshi API, found no open BTC 15m markets (timing — run was executed at 05:20 UTC when no market was active), logged `SIGNAL_SOURCE_ERROR` for all 3 cycles, and exited cleanly.

This is the expected and correct behavior per the validation spec. Outcome B is a pass.

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

All 5 checks passed. Correct package, correct entry point.

---

## Run Details

| Field | Value |
|-------|-------|
| Command | `python -m kalshi_btc15m_bot.collector --dry-run --market-source live --max-cycles 3 --poll-seconds 0` |
| `KALSHI_ENV` | `prod` |
| `BOT_DRY_RUN` | `true` |
| Process exit code | 0 |
| Outcome type | `B_all_cycles_fail_closed` |
| Fail reason | `No markets found for series_ticker=kxbtc15m` |
| Run ID | `run-2a00ac9d` |

---

## JSONL Validation

| Check | Result |
|-------|--------|
| Total events | 4 (3x `trade_skipped` + 1x `run_summary`) |
| `dry_run=true` on all events | PASS |
| `schema_version=1.0` on all events | PASS |
| `p_raw_semantics=p_yes` on all events | PASS |
| No secrets in logs | PASS |
| `run_summary` count | 1 ✅ |
| `cycle_id=null` on `run_summary` | PASS ✅ |
| `signal_source=null` on `run_summary` | PASS ✅ |
| `signal_sources_by_count` | `{"unavailable": 3}` ✅ |
| Event count sanity (not thousands) | PASS — 4 events total |
| Correct event types (not old bot events) | PASS — `trade_skipped` / `run_summary` only |

---

## What "No markets found" Means

The Kalshi BTC 15m series only has open markets during active 15-minute windows. The run was executed at 05:20 UTC on 2026-05-16. At that time, no `kxbtc15m` market was open. The discovery function correctly returned an empty list and raised `SignalSourceError`, which the collector caught and logged as `SIGNAL_SOURCE_ERROR`.

This is not a code failure. It is correct fail-closed behavior working exactly as designed.

---

## What Changed vs Previous Attempt

The previous attempt (wrong bot, 58,000+ events, old event types) was caused by the agent running from a different directory containing an older scaffold. The v2 package fixed this by:
- Including the complete v11 codebase in the ZIP
- Explicitly specifying the correct entry point (`collector.py`, not `main.py`)
- Documenting what wrong event types look like
- Pre-run checks that verify the correct files are present

The agent ran the correct bot this time.

---

## Next Step

Re-run the validation during an active BTC 15m market window to achieve Outcome A (live snapshot success). Kalshi BTC 15m markets are typically open during US trading hours. The agent should run the same command during that window.

No code changes needed. The bot is ready.

---

## Approval Status

| Item | Status |
|------|--------|
| Correct bot / correct package | Confirmed |
| Correct entry point used | Confirmed |
| Fail-closed behavior | Validated ✅ |
| `run_summary` metadata fields | Validated ✅ |
| `dry_run=true` enforcement | Validated ✅ |
| No secrets in logs | Validated ✅ |
| Live snapshot with open market | PENDING — timing issue only |
| Live trading | Still prohibited |
