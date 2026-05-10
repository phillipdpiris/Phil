# Kalshi BTC 15m Bot – Risk & Review Guide

This document explains the trading rules, risk controls, and logging that govern the BTC 15m bot, and provides a checklist for third-party review before any live deployment.

---

## 1. Strategy summary

**Instruments:** Kalshi BTC 15-minute markets. Binary contracts with YES/NO outcomes and 0–100 cent payoff.

**Positioning rules:** At most one open position per market at a time. Long YES or long NO only. Fixed size per phase (`order_size` / `final_minute_order_size`).

**Information inputs:**
1. Kalshi orderbook (YES/NO bid ladders, spread, depth)
2. Coinbase BTC candles (returns at 1m/3m/5m/10m, realized vol)
3. Recent Kalshi contract context (outcome rates, continuation/reversal rates)
4. Clock / phase within each 15-minute expiry (phase1/phase2/phase3/final_minute)

**Decision logic:** Fair YES/NO probs → fair prices → net edge per side → choose best side → guard checks → entry if all pass.

---

## 2. Entry criteria and cost modeling

```
net_edge_cents = fair_value_cents - market_price_cents - estimated_fee - spread_cents - slippage_buffer
```

- **Edge thresholds:** `normal_min_edge_cents` (phase1–3), `final_minute_min_edge_cents` (final minute)
- **YES bias penalty:** YES is only chosen if its net edge exceeds NO edge by `YES_EDGE_PENALTY_CENTS` (historical dry-run correction)
- **Guards:** spread_ok, depth_ok, time_ok (blocks if ≤20s remaining outside final_minute), single_position_ok

---

## 3. Exit rules

- **TP1:** `gross_pct >= 8%` → sell ~50% of contracts
- **TP2:** TP1 done and `gross_pct >= 12%` → sell ~30% of remaining
- **Stop-loss:** `gross_pct <= -6%` → sell_all
- **Late flatten:** `remaining ≤ 60s` and edge below final_minute threshold → sell_all; `remaining ≤ 180s` and edge negative → sell_all

---

## 4. Risk guardrails

- **Per-expiry cooldown:** if a ticker accumulates `realized_pnl_cents ≤ -150` AND `stop_losses ≥ 8`, new entries are blocked for that expiry
- **Single position:** no pyramiding or averaging down
- **Not yet implemented:** daily loss limit, trade count cap, Kelly sizing — add via `BotState.metadata` wrapper if needed

---

## 5. Dry-run, logging, replay

- `BOT_DRY_RUN=true` (default): no live orders submitted. Position state simulated from logged prices.
- All events logged to `bot_events.jsonl`: market_snapshot, signal_snapshot, order_submission, exit
- **Replay:** `python -m kalshi_btc15m_bot.cli replay bot_events.jsonl` — computes synthetic realized PnL from logs
- **Compare exits:** `python -m kalshi_btc15m_bot.cli compare-exits` — baseline + extensible variant runner

---

## 6. Third-party review checklist

### Configuration
- [ ] `KALSHI_ENV=demo` for initial tests
- [ ] `BOT_DRY_RUN=true` until fully comfortable
- [ ] API key and private key via secure mechanisms (not committed)

### API correctness
- [ ] Validate REST endpoints match current Kalshi spec
- [ ] Confirm websocket URL and headers
- [ ] Confirm orderbook payload shape (bids only, reciprocal ask logic)

### Strategy
- [ ] Review `strategy/fair_value.py` feature weights and phase behaviors
- [ ] Review `strategy/scorer.py` edge calculation, YES penalty, thresholds
- [ ] Run all tests: `python -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/pytest`

### Risk and exits
- [ ] Confirm stop-loss threshold (−6%) is acceptable
- [ ] Confirm TP1/TP2 levels and partial sizes
- [ ] Review late flatten conditions
- [ ] Review per-expiry cooldown parameters

### Deployment
- [ ] Process supervisor with restart-on-failure and log rotation
- [ ] Manual kill-switch procedure defined
- [ ] Daily loss caps if desired (add via `BotState.metadata`)

> **Important:** Do not disable `BOT_DRY_RUN` until dry-run logs have been replayed, analyzed, and risk parameters tuned to your tolerance.
