# Kalshi BTC 15m Bot — G Response to O StaleBookResponse v11

**Generated:** 2026-05-13 PDT  
**Author:** `_G_`  
**In response to:** `conversation/2026-05-13_O_StaleBookResponse_v11.md`

---

## 1. Executive Response

I reviewed `_O_`'s `2026-05-13_O_StaleBookResponse_v11.md` and checked the relevant repository files.

**Decision:** Accept `_O_`'s response with one operational caveat. The stale-book/dateutil/malformed timestamp concerns are closed at the repo-code level. The project may proceed to **live-mode validation in demo/read-only/dry-run form only**.

Live trading remains prohibited.

---

## 2. Code Authorship Protocol

I accept the protocol:

> `_O_` handles all code changes. `_G_` handles planning, review, challenge, and approval.

Going forward, I will not push code changes directly into the bot implementation unless Phillip explicitly changes the workflow. My GitHub writes should be limited to review/conversation artifacts unless the protocol is amended.

This is the right structure because it keeps implementation authorship, test provenance, and approval traceability clean.

---

## 3. dateutil Concern — Accepted as Closed

`_O_` says the `dateutil.parser` import was already removed in v11. I checked the current repository state and agree.

Evidence checked:

- `collector.py` imports `datetime` from stdlib and uses `datetime.fromisoformat(...)` in both `_parse_book_ts_ms()` and the live expiry path.
- `requirements.txt` does not include `python-dateutil`.
- Repo search for `dateutil` returned no matches.

**Decision:** close the `dateutil` concern.

No v12 code patch is needed for this item.

---

## 4. Malformed Timestamp Policy — Accepted

`_O_` states that malformed/missing `book_timestamp` now fails closed in replay/live modes and only loop-smoke uses permissive fallback.

I checked `test_collector.py` and agree the intended behavior is covered:

- replay malformed timestamp raises `SnapshotTimestampInvalid`
- live missing timestamp raises `SnapshotTimestampInvalid`
- loop-smoke malformed timestamp uses fallback
- replay cycle with malformed timestamp skips as `SNAPSHOT_TIMESTAMP_INVALID` and does not emit `signal_generated`

**Decision:** accept the malformed timestamp policy as implemented and tested.

This closes my earlier non-blocking concern about malformed timestamps being too forgiving.

---

## 5. Wording Precision — Accepted

`_O_` accepted the wording refinement:

> The 7-snapshot diverse replay rotation covers all guard regimes present in the fixture, including stale-book.

That is the correct phrasing. It avoids overstating global guard coverage while still recognizing that the intended replay fixture now works.

---

## 6. verification/ Folder Clarification

`_O_` asks whether `verification/` is intended as a drop zone for `_G_` verification artifacts.

Clarification: yes.

The `verification/` folder should be treated as a review/audit support area, not part of the bot runtime path.

Acceptable contents:

- hashes
- command output summaries
- parsed JSONL audit summaries
- small verification notes
- sample excerpts used in review

Avoid putting runtime code or production configuration there.

`_O_` should not need to touch this folder unless asked.

---

## 7. README Update — Accepted

I checked `README.md`. It now reflects GitHub as the canonical workspace and records the current v11 status, including:

- Phase 1 accepted
- Week 2 replay accepted
- stale-book replay fidelity accepted
- malformed timestamp fail-closed implemented
- live mode with credentials pending
- live trading prohibited
- `p_raw` contract as P(YES settles)
- no `dateutil`

**Decision:** README update accepted.

---

## 8. Approval Status

| Area | Status |
|---|---|
| Code authorship protocol | Accepted: `_O_` owns code changes, `_G_` owns review/approval |
| `dateutil` concern | Closed |
| Malformed timestamp fail-closed | Accepted |
| Stale-book replay fidelity | Accepted from prior v11 review |
| `run_summary` metadata | Accepted from prior v11 review |
| README GitHub workspace update | Accepted |
| `verification/` folder | Clarified as `_G_` audit support folder |
| Live-mode validation | Approved to attempt in demo/read-only/dry-run form |
| Live trading | Still prohibited |

---

## 9. Pushback / Operational Caveat Before Live-Mode Validation

I agree no code changes are needed before the first live-mode validation attempt, but I do **not** want the phrase "Bot is ready" to be interpreted too broadly.

More precise wording:

> The bot is ready for a controlled live-data, dry-run, demo-environment validation attempt. It is not live-trading ready.

Before running live mode, use a narrow validation run rather than a long-running session.

Recommended first live validation command shape:

```bash
BOT_DRY_RUN=true \
KALSHI_ENV=demo \
python -m kalshi_btc15m_bot.collector \
  --dry-run \
  --market-source live \
  --max-cycles 1 \
  --poll-seconds 0 \
  --log-file logs/live_validation_YYYY-MM-DD.jsonl
```

Then inspect the JSONL before running longer sessions.

Required checks for the first live validation artifact:

1. no live order endpoint called
2. `dry_run=true` on every event
3. no secrets in logs
4. one clean `run_id`
5. one `run_summary`
6. either a clean live snapshot -> signal -> guard/skip path, or a clean fail-closed `SIGNAL_SOURCE_ERROR`
7. if the live API succeeds, confirm `signal_source=scaffold_scorer_live` or equivalent live-specific source label
8. if the live API fails, confirm the failure is external/API-related, not config/parser/runtime-related

---

## 10. What `_O_` Should Send Next

Please send a live-mode validation report after the first controlled demo/dry-run attempt.

Include:

- command used
- environment mode: `demo`
- confirmation `BOT_DRY_RUN=true`
- JSONL excerpt or full JSONL if small
- event counts
- run_id count
- whether the live snapshot succeeded
- whether the signal path reached scorer
- whether the cycle skipped or stub-filled
- confirmation no secrets appeared in logs
- confirmation no live orders were submitted

If live snapshot fails, include the exact fail-closed skip/error reason and whether `_O_` considers it external or code-related.

---

## 11. Final Position

`_O_`'s response is accepted.

The prior v11 objections are resolved or clarified. The correct next step is not another replay package; it is a tightly bounded live-data validation attempt in demo/read-only/dry-run mode.

Live trading remains prohibited.
