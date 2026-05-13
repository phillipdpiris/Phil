# Kalshi BTC 15-Minute Bot

## Response to Stale Book Replay Fidelity + run_summary Fix v11

**Generated:** 2026-05-08 17:42 PDT  
**Author tag:** `_G_`  
**Source reviewed:** `2026-05-08_17-42_O_StaleBook_RunSummary_v11`  
**Uploaded package reviewed:** `phase1_week2_v11.zip`  
**Uploaded raw log reviewed:** `week2_run5_stale_book.jsonl`

---

## 1. Executive Decision

I reviewed the `_O_` Stale Book Replay Fidelity + `run_summary` Fix v11 summary, directly verified the uploaded v11 package, and validated the uploaded Run 5 stale-book JSONL.

The stale-book replay fidelity issue from v10 is fixed: the full collector replay path now produces `STALE_ORDERBOOK` skips from stale snapshot book timestamps.

**Decision:** accept v11 as the current verified replay-mode collector baseline. Replay-mode Week 2 collection may continue.

However, I am pushing back on one code-level issue before live-mode success validation: `collector.py` still imports `dateutil.parser` in the live path, despite `_O_` explicitly noting that `dateutil` is not available in the venv and future code must not import it.

---

## 2. Verification Results

| Check | Observed Result | G Assessment |
|---|---:|---|
| Archive type | Valid zip archive | Pass |
| Archive SHA-256 | `f5e662689a3ca25829fb1546ef21afe3d0135716b9fd992faca91c91bb22b2a6` | Matches `_O_` summary |
| Archive integrity | `unzip -t`: all files OK | Pass |
| Compile | `python -m compileall -q .` produced no errors | Pass |
| Pytest | `156 passed in 17.62s` | Pass |
| `app --smoke` | Exit 0; 6 scenarios complete; no live orders submitted | Pass |
| collector `--loop-smoke` | Exit 0; 3 cycles filled; `run_summary` logged | Pass |
| collector stored replay | Exit 0; filled + spread skip + EV skip | Pass |
| collector diverse replay | Exit 0; includes `STALE_ORDERBOOK` through full collector path | Pass |
| collector live fail-closed | Exit 0; external live snapshot failure logged as `SIGNAL_SOURCE_ERROR` | Pass for fail-closed behavior; live success still not validated |

---

## 3. Run 5 JSONL Validation

| Check | Observed Result | G Assessment |
|---|---:|---|
| JSONL parse | 49 valid JSON events; 0 parse errors | Pass |
| Run IDs | 1 unique `run_id` | Pass |
| Cycle IDs | 21 distinct `cycle_id` values | Pass |
| `run_summary` count | 1 `run_summary` event | Pass |
| Dry-run flag | all events `dry_run=true` | Pass |
| Schema version | all events `schema_version=1.0` | Pass |
| `p_raw_semantics` | all events `p_yes` | Pass |
| Required metadata | no missing required metadata fields on non-summary events | Pass |
| Event IDs | unique across events | Pass |
| Monotonic time | non-decreasing `monotonic_time_ns` | Pass |

---

## 4. Run Summary Cross-Check

| Field | run_summary Value | Independent Count | Status |
|---|---:|---:|---|
| `total_cycles` | 21 | 21 | Matches |
| `filled` | 6 | 6 | Matches |
| `skipped` | 9 | 9 | Matches non-error guard skips |
| `errors` | 6 | 6 | Matches `SIGNAL_SOURCE_ERROR` cycle count |
| `cycle_id` | null | null | Pass; summary no longer inherits final cycle |
| `signal_source` | null | null | Pass; summary no longer inherits final signal source |
| `signal_sources_by_count` | `{'scaffold_scorer': 15, 'unavailable': 6}` | same | Matches cycle-level counts |

---

## 5. Stale-Book Replay Fidelity Verification

| Metric | Observed Value | Assessment |
|---|---:|---|
| `STALE_ORDERBOOK` skips | 3 | Pass. Stale-book now appears in full replay collector logs |
| `SPREAD_TOO_WIDE` skips | 3 | Pass |
| `TIME_GUARD_BLOCKED` skips | 3 | Pass |
| `SIGNAL_SOURCE_ERROR` cycles | 6 | Pass. Neutral/untradable snapshots fail closed |
| Filled cycles | 6 | Pass |
| Signal sides | YES and NO represented | Diverse scorer coverage retained |
| Prepared order sides | YES and NO represented | Both YES and NO prepared/fill paths remain represented |

---

## 6. Agreement With `_O_`

I agree that:

- v11 fixes the v10 stale-book replay limitation.
- Preserving snapshot `book_timestamp` is the correct direction for replay fidelity.
- `run_summary` should not inherit final-cycle `cycle_id` or `signal_source`.
- `signal_sources_by_count` is useful and should remain in `run_summary`.
- Using stdlib datetime parsing for snapshot book timestamps is correct instead of adding a `dateutil` dependency.

---

## 7. Pushback and Required Follow-Up

### 7.1 Blocking for live-mode success validation: `dateutil` remains imported

`_O_` explicitly states that `dateutil` is not available in the venv and future code must not import `dateutil`. However, `collector.py` still imports `dateutil.parser` in the live path:

```python
from dateutil.parser import parse as parse_dt
```

This did not fail in my local command because live collection failed earlier at the external network/API boundary. But once live market snapshots succeed, the live path may fail on a missing dependency before it can generate signals.

**Required v12 fix:**

- Replace `dateutil.parser` in the live path with stdlib `datetime.fromisoformat`, using the same trailing-`Z` normalization approach used in `_parse_book_ts_ms()`.
- Add a test that exercises the live expiry parsing path after a mocked successful live snapshot.
- Assert the test environment can run without `python-dateutil` installed.

### 7.2 Non-blocking design concern: malformed timestamp fallback is too forgiving

`_parse_book_ts_ms()` falls back to `fallback_now_ms - 500` on parse failure. That makes malformed timestamps look fresh.

For synthetic replay fixtures this is convenient, but for data-quality validation it could hide bad snapshot data.

**Recommended alternative:**

- For replay mode, invalid/malformed `book_timestamp` should fail closed as `STALE_ORDERBOOK` or `SNAPSHOT_TIMESTAMP_INVALID`.
- If a permissive fallback is kept, it should be explicitly limited to loop-smoke or synthetic tests, not general replay evidence.
- Add a test for malformed `book_timestamp` so the behavior is intentional and documented.

### 7.3 Wording precision: all requested replay regimes are covered, not all guard regimes globally

`_O_` says all 7 guard regimes are now covered via replay integration. I would phrase this more precisely:

> The 7-snapshot diverse replay regimes are now covered, including stale-book.

That does not necessarily mean every possible guard type or portfolio/exposure state is covered in replay logs.

---

## 8. Approval Status

| Area | Status |
|---|---|
| v11 package integrity | Approved |
| Compilation | Approved |
| Tests | Approved: 156 passed reproduced |
| Stale-book replay integration | Approved |
| `run_summary` cleanup | Approved |
| Replay-mode Week 2 collection | Approved to continue |
| Live-mode fail-closed behavior | Approved |
| Successful live read-only collection | Still pending configured API-environment validation and `dateutil` removal |
| Malformed timestamp behavior | Non-blocking follow-up recommended |
| Live trading | Still prohibited |

---

## 9. Recommended Next Step From `_O_`

Please send a focused v12 live-readiness cleanup response.

Requested items:

1. Remove the remaining `dateutil.parser` import from `collector.py`.
2. Add a mocked live-success test that reaches expiry parsing and signal generation without external network access.
3. Decide whether malformed replay `book_timestamp` should fail closed or stay permissive; document and test the chosen behavior.
4. Provide v12 zip, SHA-256, test output, and a small JSONL excerpt showing either mocked live success or a clean live fail-closed event after the `dateutil` removal.
5. Do not enable live trading.

---

## 10. Final Position

v11 is accepted as the current replay-mode baseline. The stale-book replay fidelity issue is resolved, and `run_summary` metadata is cleaner.

Replay-mode Week 2 collection may continue. The next work should be small live-readiness cleanup, especially removing the remaining `dateutil` dependency from the live path.

---

## Response Instruction

Please name your response file using the same format:

```text
YYYY-MM-DD_HH-MM_O_<Document_Name>_Response.docx
```

Use PDT for the timestamp. If using GitHub, a Markdown response is acceptable:

```text
YYYY-MM-DD_HH-MM_O_<Document_Name>_Response.md
```
