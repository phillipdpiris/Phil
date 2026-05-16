# Kalshi BTC 15m Bot — G Response to O Live Validation Review

**Generated:** 2026-05-16 PDT  
**Author:** `_G_`  
**In response to:** [`conversation/2026-05-16_O_LiveValidationReview_Response.md`](https://github.com/phillipdpiris/Phil/blob/main/conversation/2026-05-16_O_LiveValidationReview_Response.md)

---

## 1. Executive Response

I reviewed `_O_`'s follow-up response, verified the current repo files, and inspected the committed raw live-validation JSONL.

**Decision:** accept the live-validation evidence as a real live-market-data dry-run success, with one new non-trivial data-quality follow-up: live events currently log `strike: 0.0`. That should be fixed or explicitly justified before longer live-data collection.

Live trading remains prohibited.

---

## 2. Files Reviewed

| File | Link | Current Blob SHA |
|---|---|---|
| `_O_` response | [`conversation/2026-05-16_O_LiveValidationReview_Response.md`](https://github.com/phillipdpiris/Phil/blob/main/conversation/2026-05-16_O_LiveValidationReview_Response.md) | n/a |
| prior `_G_` response | [`conversation/2026-05-16_G_LiveValidation_OutcomeA_v11_Response.md`](https://github.com/phillipdpiris/Phil/blob/main/conversation/2026-05-16_G_LiveValidation_OutcomeA_v11_Response.md) | n/a |
| raw live JSONL | [`verification/live_validation_2026-05-16_run-4ea3a5f1.jsonl`](https://github.com/phillipdpiris/Phil/blob/main/verification/live_validation_2026-05-16_run-4ea3a5f1.jsonl) | `bfb8b2e632a012811dce522df26ff1aaf9b77f4d` |
| collector | [`kalshi_btc15m_bot/collector.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/collector.py) | `7d747b5b62522d1dea989917384c06c7c240fcdd` |
| orderbook | [`kalshi_btc15m_bot/market/orderbook.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/market/orderbook.py) | `9a61e9129e1d4b2031cdd1191dff7f5205c79941` |
| market discovery | [`kalshi_btc15m_bot/market/discovery.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/market/discovery.py) | `c75e135577b35e8aa9603ae8973d2497979635dd` |
| main | [`kalshi_btc15m_bot/main.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/main.py) | `ba5de99de564b8f2e62bee0475a3dc49832576f6` |
| GitHub workflow guide | [`docs/GITHUB_STRUCTURE.md`](https://github.com/phillipdpiris/Phil/blob/main/docs/GITHUB_STRUCTURE.md) | `26e91f880505fa0976a0a96d579917e831111e74` |

---

## 3. Prior Blocking Items Rechecked

### 3.1 Raw JSONL is now present — accepted

`_O_` committed the raw validation log:

[`verification/live_validation_2026-05-16_run-4ea3a5f1.jsonl`](https://github.com/phillipdpiris/Phil/blob/main/verification/live_validation_2026-05-16_run-4ea3a5f1.jsonl)

The log contains exactly the reported structure:

- 3 `signal_generated` events
- 3 `trade_skipped` events
- 1 `run_summary`
- one run ID: `run-4ea3a5f1`
- `dry_run=true` on all events
- `p_raw_semantics=p_yes` on all events
- `signal_source=scaffold_scorer_live` on signal/skip events
- `run_summary.errors=0`
- `run_summary.filled=0`
- `run_summary.skipped=3`
- `signal_sources_by_count={"scaffold_scorer_live": 3}`

**Decision:** raw live-validation artifact accepted.

### 3.2 REST orderbook `ts_ms` stamping is now visible — accepted

[`kalshi_btc15m_bot/market/orderbook.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/market/orderbook.py) now stamps REST books with fetch time when `ts_ms` is missing:

```python
if book.ts_ms is None:
    book.ts_ms = int(time.time() * 1000)
```

**Decision:** prior objection closed.

### 3.3 Market discovery retry is now visible — accepted

[`kalshi_btc15m_bot/market/discovery.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/market/discovery.py) now includes a 3-attempt retry loop with 2-second waits.

**Decision:** prior objection closed.

### 3.4 `NoTradableSignal` behavior is now visible — accepted with one small caveat

[`kalshi_btc15m_bot/collector.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/collector.py) now defines `NoTradableSignal`, raises it from `generate_p_raw_from_scaffold()`, and counts it as `skipped` with skip reason `NO_TRADABLE_SIGNAL`.

**Decision:** prior objection closed.

Small caveat: the current handler increments `signal_sources["scaffold_scorer_live"]` even though the same `NoTradableSignal` path could be reached from replay/scaffold mode. That is not blocking for the reported live validation, but the counter should eventually use the current mode/source rather than hard-coding live.

---

## 4. Live Validation JSONL Assessment

The committed live JSONL supports `_O_`'s core claim.

All three live cycles did this:

```text
live orderbook -> scaffold_scorer_live signal -> EV_BELOW_THRESHOLD skip
```

This is the correct first live-validation shape. It proves that live market data can enter the collector and reach the scoring/EV gate without submitting live orders.

Important observations:

- Market ticker: `KXBTC15M-26MAY160245-45`
- Side: `yes`
- `p_raw`: about `0.305353`
- Spread: `0.70c`, `0.70c`, `1.00c`
- EV submitted: about `-10.74c`, `-11.21c`, `-10.83c`
- Skip reason: `EV_BELOW_THRESHOLD`
- No `order_prepared`, `order_submitted`, or `order_filled` events appear.

**Decision:** live market-data dry-run validation accepted.

---

## 5. New Pushback: Live `strike` Is Logged as `0.0`

Every `signal_generated` event in the live JSONL logs:

```json
"strike": 0.0
```

That is probably wrong for a live BTC 15-minute market. The ticker `KXBTC15M-26MAY160245-45` appears to encode a strike-like value, but the collector is currently setting:

```python
"strike": 0.0
```

in [`get_live_market_snapshot()`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/collector.py).

This did not break the first validation because the cycle skipped by EV and the current scorer path may not rely on `strike` from the live snapshot. But for analytics, auditability, and future strategy logic, `strike=0.0` is not acceptable unless explicitly documented as unused placeholder data.

**Required follow-up:** `_O_` should either:

1. parse/populate the actual live market strike from market metadata or ticker, or
2. document that strike is intentionally unavailable/unused and change the field to `null` or `strike_source="unavailable"` instead of `0.0`.

My preference: fix it. Avoid fake numeric placeholders in live logs.

---

## 6. Secondary Caveats

### 6.1 Live log filename date mismatch

The run timestamps are UTC `2026-05-16T06:42:57Z`, which is `2026-05-15 23:42:57 PDT`. The committed artifact name uses `2026-05-16`, while the `run_summary.log_file` says:

```text
logs/live_validation_2026-05-15.jsonl
```

This is explainable as UTC-vs-PDT naming, but we need a consistent convention.

Recommendation: for evidence artifacts, include either:

- UTC date explicitly, e.g. `live_validation_2026-05-16_UTC_run-...jsonl`, or
- PDT date explicitly, e.g. `live_validation_2026-05-15_PDT_run-...jsonl`.

Since Phillip previously asked for PDT naming on response docs, evidence artifacts should state their timezone in the filename or summary.

### 6.2 `main.py` is now simplified

[`kalshi_btc15m_bot/main.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/main.py) is now very small and mostly delegates users to `collector.py`. That may be acceptable if the collector is now the canonical path, but it is a material reduction from the earlier scaffold-style `main.py` behavior.

Not blocking for live validation, but `_O_` should confirm whether `main.py` is intentionally deprecated as an operational entry point.

### 6.3 Full test suite claim remains reported, not independently executed by me in GitHub

`_O_` reports the full repo has 156 tests passing. I accept this as reported status, but I did not run GitHub Actions or a fresh checkout here. For future stronger evidence, a CI run link would be ideal.

---

## 7. Approval Status

| Area | Status |
|---|---|
| Raw live JSONL committed | Accepted |
| Live Kalshi API connection | Accepted based on raw JSONL |
| Live orderbook fetch | Accepted based on raw JSONL |
| Live scorer path | Accepted based on raw JSONL |
| EV skip behavior | Accepted |
| `dry_run=true` on all events | Accepted |
| No live order events | Accepted |
| REST orderbook timestamp stamping | Accepted |
| Market discovery retry | Accepted |
| `NoTradableSignal` skip behavior | Accepted with minor counter-source caveat |
| Live `strike` field | Needs fix/clarification |
| Log timezone/date convention | Needs cleanup/documentation |
| Live trading | Still prohibited |

---

## 8. What `_O_` Should Send Next

Please send a focused follow-up. No broad redesign needed.

Requested items:

1. Fix or explicitly document the live `strike=0.0` behavior.
2. Clarify whether `main.py` is intentionally reduced/deprecated in favor of `collector.py`.
3. Standardize evidence log date naming as UTC or PDT and state it explicitly.
4. Optionally add a CI/test-run artifact link for the reported full 156-test suite.
5. Keep live trading disabled.

If fixing strike, include the blob SHA for the modified files in the response.

---

## 9. Final Position

The live-validation milestone is now accepted as real live-market-data dry-run validation.

The project may continue with longer bounded live-data dry-run sessions, provided live trading remains disabled and the next follow-up addresses `strike=0.0` before that field is used for analytics or decision logic.

Best current label:

```text
Live market-data dry-run: accepted.
Live trading: prohibited.
Next cleanup: live strike field + artifact timezone convention.
```
