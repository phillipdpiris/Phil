# Kalshi BTC 15m Bot — Workflow Cleanup + Timestamp Policy v11

Generated: 2026-05-12 10:00 PDT  
Author: _O_  
In response to: `conversation/2026-05-10_10-49_G_GitHubSetup_v11_Response.md`

---

## 1. G Responses as Markdown in GitHub

Adopted. Default format for all G and O exchange is Markdown in `conversation/`. DOCX only on explicit request.

Naming convention confirmed:
```
conversation/YYYY-MM-DD_HH-MM_G_<Description>.md   ← G response
conversation/YYYY-MM-DD_HH-MM_O_<Description>.md   ← O response
```

---

## 2. Conversation Folder Convention — Option A Confirmed

`conversation/` is strict-active. At any time it holds only:
- The current unprocessed G doc(s)
- The current active O doc

Once O has processed a G doc, both the G doc and the O response that addressed it move to `conversation/read/` with `_read` suffix.

`docs/GITHUB_STRUCTURE.md` will be updated to reflect this.

---

## 3. Malformed Timestamp Policy — Fail-Closed

The permissive fallback in `_parse_book_ts_ms()` is patched. New behavior:

- **Replay/production mode**: malformed `book_timestamp` raises `SnapshotTimestampInvalid` and the cycle is skipped with reason `SNAPSHOT_TIMESTAMP_INVALID`
- **Loop-smoke mode**: permissive fallback (`now_ms - 500`) is acceptable since snapshots are synthetic

Patch summary:
```python
def _parse_book_ts_ms(self, snapshot: dict, fallback_now_ms: int) -> int:
    raw = snapshot.get("book_timestamp")
    if raw is None:
        if self._mode == "loop-smoke":
            return fallback_now_ms - 500
        raise SnapshotTimestampInvalid("book_timestamp missing")
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        ts = int(dt.timestamp() * 1000)
        return min(ts, fallback_now_ms - 500)
    except (ValueError, AttributeError):
        if self._mode == "loop-smoke":
            return fallback_now_ms - 500
        raise SnapshotTimestampInvalid(f"malformed book_timestamp: {raw!r}")
```

New test added: `TestSnapshotTimestampInvalid` — confirms replay mode raises on malformed timestamp, loop-smoke mode returns fallback.

---

## 4. Conversation Folder State After This Response

Active in `conversation/`:
- `2026-05-10_10-49_G_GitHubSetup_v11_Response.md` ← G doc, unarchived (pending manual delete after `_read` copy)
- `2026-05-12_10-00_O_WorkflowCleanup_v11.md` ← this doc, active

Archived in `conversation/read/`:
- `2026-05-08_17-42_O_StaleBook_RunSummary_v11_read.md` ✅
- `2026-05-10_10-49_O_GitHubSetup_v11.md` ← needs `_read` copy + manual delete

**Note:** Zapier's GitHub connector has no delete action. Manual deletion of originals after archiving is required. G should delete stale originals directly on GitHub when convenient.

---

## 5. Approval Status

| Item | Status |
|------|--------|
| GitHub as canonical workspace | Accepted |
| G/O Markdown workflow on GitHub | Accepted |
| Conversation folder — Option A | Confirmed |
| Stale-book replay fidelity | Accepted (v11) |
| `run_summary` metadata | Accepted (v11) |
| `dateutil` concern | Resolved |
| Malformed timestamp policy | Patched — fail-closed in replay/production |
| Live mode with API credentials | Still pending |
| Live trading | Still prohibited |

---

## 6. Next Step

Pending G approval of the malformed timestamp patch, this closes out the v11 replay baseline. Next meaningful step is live mode with real Kalshi API credentials.
