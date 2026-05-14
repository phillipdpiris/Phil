# Kalshi BTC 15-Minute Bot

Phase 1 + Week 2 collector. See `docs/GITHUB_STRUCTURE.md` for full repo layout and G/O workflow.

## Status

| Item | Status |
|------|--------|
| Phase 1 pipeline | ACCEPTED |
| Week 2 loop-smoke | ACCEPTED |
| Week 2 replay (all regimes) | ACCEPTED |
| Stale-book replay fidelity | ACCEPTED (v11) |
| run_summary metadata | ACCEPTED (v11) |
| Malformed timestamp fail-closed | IMPLEMENTED |
| Live mode with API credentials | PENDING |
| Live trading | PROHIBITED |

## Quick Start

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest
python -m kalshi_btc15m_bot.collector --loop-smoke --max-cycles 5
python -m kalshi_btc15m_bot.collector --dry-run --market-source replay \
  --snapshot-file snapshots/sample_week2_diverse_snapshot.json --max-cycles 7
```

## Package

- Version: v11
- SHA-256: `f5e662689a3ca25829fb1546ef21afe3d0135716b9fd992faca91c91bb22b2a6`
- Tests: 156/156
- Python: 3.11+

## Key Rules

- `p_raw` always = P(YES settles). Never side-local probability.
- `StubKalshiClient` always used in collector. No live orders ever.
- `DryRunEnforcementError` raised if `dry_run=False`.
- Never import `dateutil` — use stdlib `datetime.fromisoformat`.
- Scaffold files untouched: `main.py`, `config.py`, `fair_value.py`, `scorer.py`, `guards.py`.
