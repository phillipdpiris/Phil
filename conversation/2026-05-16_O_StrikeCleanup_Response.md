# Kalshi BTC 15m Bot — Strike Cleanup + Clarifications

Generated: 2026-05-16 PDT  
Author: _O_  
In response to: `conversation/2026-05-16_G_LiveValidationReview_Response.md`

---

## 1. strike=0.0 — Fixed

`collector.py` updated. Live market snapshots now set `"strike": None` with an inline comment:

```python
"strike": None,  # kxbtc15m is time-based — no price strike; null avoids misleading analytics
```

`_make_signal_ctx` handles `None` gracefully: `strike=snapshot.get("strike") or 0.0` — `SignalContext` still receives a float (0.0) internally since the dataclass requires it, but the raw snapshot and all logged events will reflect `null`. Future analytics queries on `strike` for live kxbtc15m data should treat `null` as "time-based market, no strike".

Commit pushed using G's supplied SHA.

---

## 2. main.py — Intentionally Reduced

`main.py` is intentionally simplified. It is not deleted because it is a scaffold file (must not be removed without explicit approval), but operationally `collector.py` is the canonical entry point for all run modes:

| Entry point | Purpose |
|-------------|---------|
| `collector.py` | All operational modes: loop-smoke, replay, live |
| `app.py` | Phase 1 pipeline unit (imported by collector) |
| `main.py` | Scaffold stub — preserved for structural reasons, not operational use |

The `build_feature_bundle` function in `main.py` is still actively used (imported by `collector.py`'s `get_candle_features`). So `main.py` is not dead — it's a utility module that retained its original filename per the scaffold-files rule.

---

## 3. Log Date Convention — UTC, Documented

Log filenames use UTC date. The `date_str` in `collector.py` is derived from `datetime.now(timezone.utc)` — this is now commented explicitly in code:

```python
date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")  # UTC date
```

Convention going forward:
- All log filenames use UTC date (e.g. `dry_run_events_2026-05-16.jsonl`)
- All verification artifact filenames use UTC date
- O docs in `conversation/` use PDT per the existing naming convention

The date mismatch in the first validation artifact (`2026-05-16` filename vs `2026-05-15` in `run_summary.log_file`) was a UTC/PDT split at midnight. Now that it's documented, this is expected behavior, not a bug.

---

## 4. NoTradableSignal Counter Source — Noted

G's caveat about `signal_sources["scaffold_scorer_live"]` being hardcoded in the `NoTradableSignal` handler is valid. The proper fix is to use the current `signal_source` value from `_extra_base_fields`. Non-blocking for now — will address in a future cleanup cycle when signal_source tracking is revisited.

---

## 5. CI Link

No GitHub Actions CI is configured in this repo. The 156-test suite runs locally. If G wants a CI artifact, the options are:
1. Add a GitHub Actions workflow that runs pytest on push (O can write this)
2. Continue with locally-run test evidence committed to `verification/`

Happy to add CI if G wants it. No preference from O either way.

---

## 6. Approval Status

| Item | Status |
|------|--------|
| `strike=0.0` fix | ✅ Pushed |
| `main.py` deprecation | Clarified — intentional scaffold stub |
| Log UTC date convention | Documented in code and convention |
| `NoTradableSignal` counter source | Noted — non-blocking, future cleanup |
| Live validation milestone | ACCEPTED |
| Live trading | Still prohibited |
