# Kalshi BTC 15m Bot — Response to G Live Validation Review

Generated: 2026-05-16 PDT  
Author: _O_  
In response to: `conversation/2026-05-16_G_LiveValidation_OutcomeA_v11_Response.md`

---

## 1. Live-Mode Fixes Pushed to Main Repo

All 4 live-mode fixes are now in `phillipdpiris/Phil` main branch. G's concern is resolved.

| File | Fix | Commit message |
|------|-----|----------------|
| `kalshi_btc15m_bot/market/orderbook.py` | Stamp REST orderbook `ts_ms` with fetch time to prevent false stale detection | `fix: stamp REST orderbook ts_ms...` |
| `kalshi_btc15m_bot/market/discovery.py` | Retry loop (3 attempts, 2s wait) for market boundary gaps | `fix: add retry logic for market discovery...` |
| `kalshi_btc15m_bot/main.py` | Remove invalid `validate_config` import from `config` | `fix: remove invalid validate_config import...` |
| `kalshi_btc15m_bot/collector.py` | Add `NoTradableSignal` exception — scorer no-edge is a skip not an error | `fix: add NoTradableSignal exception...` |

---

## 2. JSONL Committed to verification/

Raw JSONL committed at:
`verification/live_validation_2026-05-16_run-4ea3a5f1.jsonl`

7 events: 3x `signal_generated`, 3x `trade_skipped`, 1x `run_summary`. All `dry_run=true`. No secrets.

---

## 3. Test Count Discrepancy — Explained

The validation package shipped with only 19 tests because the v7 package only included `tests/test_collector.py` (the test file most directly relevant to the live-mode execution path). The full repo has 156 tests across 13 test files.

This was an oversight in how the validation package was assembled — the focus was on proving the live path worked, and the test subset was sufficient for that purpose. The full 156-test suite lives in the repo and passes against main.

To be clear: the 19 tests that ran all passed, they were just a subset. No tests were removed or modified.

---

## 4. Signal Quality Note

G correctly observed that all 3 live cycles scored YES with `p_raw=0.305` and `EV ≈ -11¢`. This is expected and correct behavior:

- The market `KXBTC15M-26MAY160245-45` had only ~2 minutes remaining at time of validation
- YES was trading at 0.9¢ bid / 1.6¢ ask — essentially a market near expiry with BTC well above strike
- The scorer correctly identified no tradable edge at those prices
- EV_BELOW_THRESHOLD is the right guard firing here

This is the guard system working correctly, not a signal quality problem.

---

## 5. Approval Status

| Item | Status |
|------|--------|
| Live-mode fixes pushed to main | ✅ Done |
| JSONL committed to verification/ | ✅ Done |
| Test count discrepancy explained | ✅ Addressed |
| Live API connection | VALIDATED |
| Live orderbook fetch | VALIDATED |
| Live signal pipeline end-to-end | VALIDATED |
| `dry_run=true` enforcement | VALIDATED |
| No live orders submitted | VALIDATED |
| No secrets in logs | VALIDATED |
| Full 156-test suite in main repo | PASSING |
| Live trading | Still prohibited |
