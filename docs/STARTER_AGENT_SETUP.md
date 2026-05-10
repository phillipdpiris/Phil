# Kalshi BTC 15m Bot — Detailed AI Agent Handoff Document

This document is meant to be pasted into another AI coding agent so it can continue implementation with minimal ambiguity.

## Mission

Finish wiring a Python bot scaffold for Kalshi BTC 15-minute markets.

The bot should:
1. discover the active BTC 15-minute market
2. maintain a correct local orderbook
3. price YES and NO using a fair-value model
4. enter only when net edge survives fees and execution costs
5. manage exits with partial profits and late-stage flattening
6. use recent settled market behavior as a context layer
7. stay in dry-run mode by default unless explicitly configured for live trading

## What already exists

All scaffold modules are implemented in v11. See the package structure in the README.

## Non-negotiable implementation rules

### 1. Stay dry-run by default
Do not enable live order submission unless credentials are present, `BOT_DRY_RUN=false`, logging is active, and local/live state have been reconciled.

### 2. Treat Kalshi orderbooks correctly
The Kalshi orderbook returns bids only. Asks must be inferred from the reciprocal side:
- best YES ask = 100 - best NO bid
- best NO ask = 100 - best YES bid

### 3. Sign requests correctly
Authenticated REST requests must sign: `timestamp_ms + HTTP_METHOD + path_from_root`
The path must exclude query params in the signing string.

### 4. Use market metadata for close timing
Do not hardcode "15 minutes from now". Use the market's own open/close metadata.

### 5. Final-minute logic is forced evaluation, not forced participation
Evaluate both YES and NO. Trade only if net edge survives costs. Otherwise remain flat.

### 6. Recent market behavior is a context layer only
Use last 20 outcomes to tilt weights. Do not let this override orderbook conditions.

## Current strategy design

- **Phase 1** (first 3 min): momentum / breakout primary
- **Phase 2** (3–8 min): fair value / mispricing primary
- **Phase 3** (8 min to final): time-aware management, selective entries
- **Final minute**: exit protection, optional fallback entry only if edge clearly positive

## Required coding standards

- Python 3.11+
- Small, testable functions
- Typed dataclasses for state
- No hardcoded secrets
- No silent exception swallowing
- Structured logs for every decision
- Every trade decision must have a human-readable reason string

## Minimum acceptance tests

The implementation is not "done" until:
1. Signing path strips query parameters
2. Reciprocal ask math is correct
3. Spreads are non-negative and sensible
4. Stale websocket detection works
5. No entry fires when edge is below threshold
6. Final-minute fallback stays flat when net edge is negative
7. TP1 and TP2 reduce contracts correctly
8. Stop-loss exits everything
9. Phase timing reflects actual market close time
10. Bot can run one full dry-run session without crashing

## What not to do yet

- Do NOT add machine learning first
- Do NOT add multiple simultaneous positions first
- Do NOT optimize for theoretical win rate over fee-adjusted EV
- Do NOT force trades every market
- Do NOT assume web UI and API always expose data in the same shape

## Recommended command sequence for the next agent

1. Inspect the scaffold and explain gaps file by file
2. Implement websocket book maintenance with tests
3. Implement recent-context path analysis
4. Integrate the scorer into `main.py`
5. Integrate exit engine into `main.py`
6. Add reconciliation for live positions
7. Add JSONL logging and replay-friendly state dumps
8. Run tests and fix import/type issues
9. Leave the bot in dry-run mode unless explicitly asked otherwise

## Final instruction to the next agent

When making changes:
- Preserve the existing module boundaries
- Do not collapse everything back into one file
- Prefer explicit and inspectable heuristics
- Optimize for correctness and debuggability before sophistication
- Document any place where the live Kalshi API response differs from the assumed scaffold shape
