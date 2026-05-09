from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .analytics.replay import compare_exit_variants, load_saved_orderbook_stream, replay_market


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kalshi-btc15m-bot", description="Utility CLI for the BTC 15m bot scaffold.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    replay_parser = subparsers.add_parser("replay", help="Replay a JSONL session log and compute PnL.")
    replay_parser.add_argument("path", nargs="?", default="bot_events.jsonl")
    compare_parser = subparsers.add_parser("compare-exits", help="Run the baseline replay.")
    compare_parser.add_argument("path", nargs="?", default="bot_events.jsonl")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    path = Path(args.path)
    session = load_saved_orderbook_stream(path)
    if args.command == "replay":
        result = replay_market(session, {"source_path": str(path)})
    elif args.command == "compare-exits":
        result = compare_exit_variants(session)
    else:
        parser.error(f"Unknown command: {args.command}")
        return 1
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
