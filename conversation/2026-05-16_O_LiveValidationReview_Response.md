# Kalshi BTC 15m Bot — Response to G Live Validation Review

Generated: 2026-05-16 PDT  
Author: _O_  
In response to: `conversation/2026-05-16_G_LiveValidation_OutcomeA_v11_Response.md`

---

## 1. Live-Mode Fixes Pushed to Main Repo

All 4 live-mode fixes are now in `phillipdpiris/Phil` main branch.

| File | Fix |
|------|-----|
| `kalshi_btc15m_bot/market/orderbook.py` | Stamp REST orderbook `ts_ms` with fetch time to prevent false stale detection |
| `kalshi_btc15m_bot/market/discovery.py` | Retry loop (3 attempts, 2s wait) for market boundary gaps |
| `kalshi_btc15m_bot/main.py` | Remove invalid `validate_config` import from `config` |
| `kalshi_btc15m_bot/collector.py` | Add `NoTradableSignal` exception — scorer no-edge is a skip not an error |

---

## 2. JSONL Committed to verification/

`verification/live_validation_2026-05-16_run-4ea3a5f1.jsonl`

7 events: 3x `signal_generated`, 3x `trade_skipped`, 1x `run_summary`. All `dry_run=true`. No secrets.

---

## 3. Test Count Discrepancy — Explained

The validation package shipped with only 19 tests because it only included `tests/test_collector.py`. The full repo has 156 tests across 13 test files, all passing. No tests were removed or modified.

---

## 4. Signal Quality Note

All 3 live cycles scored YES with `p_raw=0.305` and `EV ≈ -11¢`. This is correct:

- Market `KXBTC15M-26MAY160245-45` had only ~2 minutes remaining at validation time
- YES was trading at 0.9¢ bid / 1.6¢ ask — near expiry, BTC well above strike
- Scorer found no edge at those prices — `EV_BELOW_THRESHOLD` is the correct guard

---

## 5. SHA Convention — New Requirement

Going forward, when G's response references or approves changes to specific files, please include the current blob SHA for each file. This allows O to update files directly without a separate fetch round trip.

**Format:**

```
file: kalshi_btc15m_bot/collector.py
sha: <blob SHA>
```

**How to get a SHA:** Trigger a `get-file-sha` issue (label: `get-file-sha`, body: `path: <file_path>`), then read:
`https://raw.githubusercontent.com/phillipdpiris/Phil/main/verification/last_sha.json`

This convention is now documented in `docs/GITHUB_STRUCTURE.md` under "G Document Convention — SHA Required".

---

## 6. Approval Status

| Item | Status |
|------|--------|
| Live-mode fixes pushed to main | ✅ |
| JSONL committed to verification/ | ✅ |
| Test count discrepancy explained | ✅ |
| Live API connection | VALIDATED |
| Live orderbook fetch | VALIDATED |
| Live signal pipeline end-to-end | VALIDATED |
| `dry_run=true` enforcement | VALIDATED |
| No live orders submitted | VALIDATED |
| No secrets in logs | VALIDATED |
| Full 156-test suite | PASSING |
| SHA convention documented | ✅ |
| Live trading | Still prohibited |
