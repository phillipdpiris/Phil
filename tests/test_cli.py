from pathlib import Path
from kalshi_btc15m_bot.cli import main as cli_main

def _write_minimal_log(path: Path) -> None:
    path.write_text(
        "\n".join([
            '{"event_type": "order_submission", "mode": "entry", "dry_run": true, "ticker": "TEST", "phase": "phase2", "payload": {"ticker": "TEST", "side": "yes", "action": "buy", "type": "limit", "count": 10, "yes_price": 40}, "skipped": false, "reason": null}',
            '{"event_type": "exit", "ticker": "TEST", "phase": "phase2", "remaining_seconds": 300, "exit_decision": "tp1", "action": "sell_partial", "contracts": 5, "residual_edge_cents": 1.0, "dry_run": true, "payload": {"ticker": "TEST", "side": "yes", "action": "sell", "type": "limit", "count": 5, "yes_price": 45}, "skipped": false, "reason": null}',
        ]), encoding="utf-8")

def test_cli_replay_outputs_json(tmp_path: Path, capsys):
    path = tmp_path / "session.jsonl"
    _write_minimal_log(path)
    code = cli_main(["replay", str(path)])
    assert code == 0
    out = capsys.readouterr().out
    assert '"status": "ok"' in out
    assert '"TEST"' in out

def test_cli_compare_exits_outputs_baseline(tmp_path: Path, capsys):
    path = tmp_path / "session.jsonl"
    _write_minimal_log(path)
    code = cli_main(["compare-exits", str(path)])
    assert code == 0
    out = capsys.readouterr().out
    assert '"status": "baseline_only"' in out
    assert '"recorded"' in out
