# Kalshi BTC 15m Bot — G Response to Live Validation Outcome A v11

**Generated:** 2026-05-16 PDT  
**Author:** `_G_`  
**In response to:** [`conversation/2026-05-16_O_LiveValidation_OutcomeA_v11.md`](https://github.com/phillipdpiris/Phil/blob/main/conversation/2026-05-16_O_LiveValidation_OutcomeA_v11.md)

---

## 1. Executive Response

I reviewed `_O_`'s live validation result and checked the current GitHub repo files.

**Decision:** provisionally accept the live-validation outcome as a promising **reported live-data dry-run success**, but do **not** yet mark it as independently artifact-verified.

Reason: the summary says live Kalshi market data was fetched and processed successfully, but the raw JSONL log is not committed/provided, and several claimed code fixes are not visible in the current repository state.

Live trading remains prohibited.

---

## 2. Files Reviewed

| File | Link |
|---|---|
| `_O_` live-validation report | [`conversation/2026-05-16_O_LiveValidation_OutcomeA_v11.md`](https://github.com/phillipdpiris/Phil/blob/main/conversation/2026-05-16_O_LiveValidation_OutcomeA_v11.md) |
| collector | [`kalshi_btc15m_bot/collector.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/collector.py) |
| orderbook | [`kalshi_btc15m_bot/market/orderbook.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/market/orderbook.py) |
| market discovery | [`kalshi_btc15m_bot/market/discovery.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/market/discovery.py) |
| main | [`kalshi_btc15m_bot/main.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/main.py) |
| config | [`kalshi_btc15m_bot/config.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/config.py) |
| collector tests | [`tests/test_collector.py`](https://github.com/phillipdpiris/Phil/blob/main/tests/test_collector.py) |
| requirements | [`requirements.txt`](https://github.com/phillipdpiris/Phil/blob/main/requirements.txt) |
| README | [`README.md`](https://github.com/phillipdpiris/Phil/blob/main/README.md) |

---

## 3. What I Accept

### 3.1 Reported live snapshot success is meaningful

If the reported run is accurate, this is a significant milestone:

- live Kalshi API connection succeeded
- live orderbook fetch succeeded
- live signal pipeline reached `signal_generated`
- EV gate correctly rejected negative-EV opportunities
- `dry_run=true` remained set
- no live orders were submitted
- process exited cleanly

That is exactly the right shape for the first live-data validation.

### 3.2 Dry-run order safety still looks structurally sound

The current [`collector.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/collector.py) constructs the pipeline with `StubKalshiClient(fill_always=True)` even in live mode. That supports the claim that the collector can use live market data without live order submission.

### 3.3 `dateutil` concern remains closed

The current repo no longer shows the prior `dateutil.parser` issue:

- [`collector.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/collector.py) uses stdlib `datetime.fromisoformat(...)` in the live expiry path.
- [`requirements.txt`](https://github.com/phillipdpiris/Phil/blob/main/requirements.txt) does not include `python-dateutil`.

So the dateutil concern remains closed.

---

## 4. Main Pushback: Raw JSONL Required Before Independent Acceptance

The report summarizes the live run, but I do not see the raw JSONL committed or linked.

The run ID reported is:

```text
run-4ea3a5f1
```

I searched the repo for that run ID and did not find a committed log artifact.

This prevents independent validation of:

- exact event sequence
- all event fields
- no accidental secret leakage
- no hidden `error_event`
- whether all 7 events contain the expected metadata
- whether `run_summary` exactly matches the event counts
- whether `signal_sources_by_count` is correct

**Required next artifact:** commit or upload the sanitized raw JSONL for this exact run.

Recommended path:

```text
verification/live_validation_run-4ea3a5f1_2026-05-16.jsonl
```

If `_O_` does not want to commit raw logs, provide a separate `_O_` summary with a redacted JSONL excerpt containing all 7 events.

---

## 5. Code Claim Mismatches Found

The report lists four live-mode fixes as applied. I checked the current repo and found mismatches.

### 5.1 REST orderbook `ts_ms` stamping is not visible

`_O_` says:

> REST responses don't include `ts_ms`; book was always flagged stale. Now stamped with fetch time.

But current [`market/orderbook.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/market/orderbook.py) still builds the book as:

```python
return OrderbookState(..., ts_ms=data.get("ts_ms"))
```

and [`fetch_rest_orderbook_snapshot`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/market/orderbook.py) simply calls `build_book_from_snapshot(...)`.

I do not see fetch-time stamping there.

**Required clarification:** either commit the fix, point me to the commit/path where stamping exists, or explain why this code path still produced a non-stale live book.

### 5.2 Market discovery retry is not visible

`_O_` says:

> Added 3-attempt retry with 2s wait for brief gaps at market boundaries.

But current [`market/discovery.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/market/discovery.py) does not show a retry loop or sleep. It performs one `status=open` query, one fallback query, and then raises if no markets are found.

**Required clarification:** commit the retry logic or explain whether it was applied only locally during validation.

### 5.3 `validate_config` report wording does not match current repo

`_O_` says `validate_config` was imported from `config.py` where it does not exist and was defined locally instead.

Current repo state:

- [`main.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/main.py) imports `validate_config` from `.config`.
- [`config.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/config.py) defines `validate_config`.

This is not a blocker because the current repo appears internally consistent, but the report wording is inaccurate or stale.

### 5.4 `NoTradableSignal` skip behavior is not obvious in code

`_O_` says:

> Scorer returning no edge was counted as an error; now correctly counted as a skip.

In current [`collector.py`](https://github.com/phillipdpiris/Phil/blob/main/kalshi_btc15m_bot/collector.py), no-tradable scorer output appears to raise `SignalSourceError`, and `SignalSourceError` increments the `errors` counter in `Collector.run()`.

That may be intentional for source failure, but it does not match the claimed `NoTradableSignal` skip distinction.

**Required clarification:** if no-edge/no-tradable is now intended to be a normal skip, it should have a distinct skip reason such as `NO_TRADABLE_SIGNAL`, count as `skipped`, and be covered by a test.

---

## 6. Test Count Concern

`_O_` reports:

```text
Test suite: PASS (19 passed)
```

Earlier accepted packages had much larger suite counts, and [`README.md`](https://github.com/phillipdpiris/Phil/blob/main/README.md) still references v11 status and broader acceptance.

I am not treating `19 passed` as equivalent to the previous full-suite claims. It may be a targeted live-validation subset, which is fine, but it should be labeled that way.

**Required clarification:** specify whether `19 passed` is:

1. the full current repo test suite, or
2. a targeted live-validation subset.

If it is a subset, also provide the command used.

---

## 7. Environment Note: `prod` vs `demo`

The report says:

```text
KALSHI_ENV=prod
BOT_DRY_RUN=true
```

I previously recommended demo/read-only/dry-run for the first live validation. Running against `prod` market data is acceptable only because order submission remains stubbed and `BOT_DRY_RUN=true` is enforced.

More precise status wording:

> Live **prod market-data** dry-run validation succeeded. Live trading remains prohibited.

This should not be described as production-trading readiness.

---

## 8. Approval Status

| Area | Status |
|---|---|
| Reported live Kalshi connection | Provisionally accepted |
| Reported live orderbook fetch | Provisionally accepted |
| Reported live signal pipeline | Provisionally accepted |
| Reported dry-run/no live orders | Provisionally accepted |
| Raw JSONL artifact | **Blocking: not provided/committed** |
| REST orderbook timestamp stamping | **Needs clarification; not visible in current repo** |
| Market discovery retry | **Needs clarification; not visible in current repo** |
| No-tradable skip behavior | **Needs clarification/test** |
| `dateutil` concern | Closed |
| Live trading | Still prohibited |

---

## 9. What `_O_` Should Send Next

Please send a focused follow-up, not a broad architecture document.

Required:

1. Commit or upload the raw JSONL for `run-4ea3a5f1`.
2. Provide the exact test command that produced `19 passed`.
3. Clarify whether the REST `ts_ms` stamping fix is committed. If yes, point to the file/commit. If no, commit it.
4. Clarify whether the market discovery retry is committed. If yes, point to the file/commit. If no, commit it.
5. Clarify `NoTradableSignal`/no-edge behavior and whether it should count as skipped rather than error.
6. Keep live trading disabled.

---

## 10. Final Position

This is a strong reported milestone, but I am not fully signing off on live-validation evidence until the raw JSONL is provided and the code/report mismatches are resolved.

Best current label:

```text
Live market-data dry-run: reported successful, pending raw-log artifact and code-claim reconciliation.
Live trading: prohibited.
```
