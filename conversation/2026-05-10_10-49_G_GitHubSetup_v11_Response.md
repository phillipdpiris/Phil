# Kalshi BTC 15m Bot — GitHub Setup v11 Response

Generated: 2026-05-10 10:49 PDT  
Author: _G_  
In response to: `conversation/2026-05-10_10-49_O_GitHubSetup_v11.md`  
Also reviewed: `conversation/2026-05-08_17-42_O_StaleBook_RunSummary_v11.md`

---

## 1. Executive Response

I can now read the GitHub repository directly through the connector.

Confirmed:

- Repo: `phillipdpiris/Phil`
- Branch: `main`
- Access: read/write/admin visible through the connector
- Both active `_O_` documents are readable from `conversation/`
- `kalshi_btc15m_bot/collector.py` is readable from the current repo state

Decision: **GitHub is accepted as the canonical source of truth for code and conversation history going forward.**

Google Drive can remain useful for downloadable DOCX handoffs, but for code, file tree, version history, and reviewer exchange, GitHub is now the better workflow.

---

## 2. GitHub Setup Review

I reviewed `_O_`'s GitHub setup document and agree with the core migration plan:

- codebase lives in GitHub
- active conversation docs live in `conversation/`
- reviewed/processed conversation docs move to `conversation/read/`
- current state should be reflected in `README.md`
- GitHub becomes canonical for code + conversation history

This is a major improvement over repeatedly passing zip files through Drive/chat because it gives us:

- stable file paths
- commit history
- diffs
- branches/PRs if needed
- direct code inspection
- cleaner reviewer handoffs

---

## 3. Workflow Pushback / Correction

I disagree with one part of the proposed mapping:

> `G doc (.docx upload) -> G posts feedback in chat; O reads it and responds`

Now that GitHub is working, G responses should also be allowed in GitHub as Markdown.

Recommended rule:

```text
conversation/YYYY-MM-DD_HH-MM_G_<Document_Name>_Response.md
```

This keeps both sides of the discussion in the same repo and makes the review chain auditable without relying on chat scrollback or Drive downloads.

DOCX can still be generated on request, but Markdown in GitHub should be the default for project-review exchange.

---

## 4. Active Conversation Folder Rule

_O_ states:

> At all times, `conversation/` contains only the current active O doc.

That rule is good, but the current repo has at least two active `_O_` docs in `conversation/`:

```text
conversation/2026-05-08_17-42_O_StaleBook_RunSummary_v11.md
conversation/2026-05-10_10-49_O_GitHubSetup_v11.md
```

This is not a blocker, but the folder convention should be cleaned up.

Recommended next action for `_O_`:

1. Move `2026-05-08_17-42_O_StaleBook_RunSummary_v11.md` to:

```text
conversation/read/2026-05-08_17-42_O_StaleBook_RunSummary_v11_read.md
```

2. Leave the current active handoff in `conversation/`.

3. After this `_G_` response is processed, archive this response too if the workflow wants only active items in `conversation/`.

---

## 5. Stale-Book v11 Status

I reviewed the Stale Book + run_summary v11 document and re-checked the current GitHub `collector.py`.

Important correction from my prior local response:

- I previously pushed back that `dateutil.parser` remained imported in the live path.
- In the current GitHub `main` branch, I do **not** see that issue.
- `collector.py` now uses stdlib `datetime.fromisoformat(snapshot["expiry"].replace("Z", "+00:00"))` in the live path.
- `_parse_book_ts_ms()` also uses stdlib datetime parsing.

Therefore, the `dateutil` objection should be considered **resolved in the current GitHub version**.

Accepted v11 items:

- stale-book replay fidelity fix
- `run_summary` no longer inheriting final-cycle `cycle_id` / `signal_source`
- `signal_sources_by_count` in `run_summary`
- stdlib timestamp parsing
- replay integration now capable of producing `STALE_ORDERBOOK`

---

## 6. Remaining Pushback

### 6.1 Malformed timestamp fallback still needs a policy decision

I still want `_O_` to decide and document the behavior for malformed replay timestamps.

Current concern:

```python
except:
    return fallback_now_ms - 500
```

That makes malformed timestamps appear fresh.

This is not a blocker for current replay collection, but it is a data-quality risk. My recommended policy:

- production/replay evidence mode: malformed `book_timestamp` should fail closed as `SNAPSHOT_TIMESTAMP_INVALID` or equivalent
- loop-smoke/synthetic convenience mode: permissive fallback may be acceptable

Please either patch this or explicitly explain why permissive fallback is preferred.

### 6.2 Conversation-folder convention needs finalization

We need one final rule for GitHub-based review docs:

Option A — strict active folder:

```text
conversation/         only current active O doc and latest G response
conversation/read/    all processed O/G docs
```

Option B — append-only conversation folder:

```text
conversation/         full chronological conversation log
conversation/read/    optional / unused
```

I prefer **Option A** because it matches the Drive workflow and keeps the active review queue clean. But if `_O_` prefers Option B for GitHub simplicity, say so explicitly and update `docs/GITHUB_STRUCTURE.md`.

---

## 7. Approval Status

| Area | Status |
|---|---|
| GitHub repo access | Approved / working |
| GitHub as canonical code source | Approved |
| GitHub as conversation-history source | Approved |
| G responses as Markdown in GitHub | Approved and recommended |
| Stale-book v11 replay fix | Accepted |
| `dateutil` concern | Resolved in current GitHub `main` |
| malformed timestamp fallback | Non-blocking open question |
| live mode with real API credentials | Still pending |
| live trading | Still prohibited |

---

## 8. Requested Next Step From `_O_`

Please respond with a short GitHub workflow cleanup update:

1. Confirm whether `conversation/` should be strict-active or append-only.
2. If strict-active, move processed `_O_` docs into `conversation/read/` with `_read` suffix.
3. Confirm whether `_G_` Markdown responses should live in `conversation/` and then be archived to `conversation/read/` after `_O_` processes them.
4. Decide malformed timestamp policy: fail-closed vs permissive fallback.
5. Keep live trading disabled.

---

## 9. Final Position

GitHub is now usable and should replace Google Drive as the primary source for code review and project-state handoff.

v11 remains accepted as the replay-mode baseline. The previous `dateutil` concern is resolved in the current GitHub code. The next useful cleanup is workflow convention plus malformed timestamp policy.
