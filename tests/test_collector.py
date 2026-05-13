import json, os, time
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from kalshi_btc15m_bot.collector import Collector, SignalSourceError, SnapshotTimestampInvalid, _parse_book_ts_ms

def read_events(log_file):
    with open(log_file) as f:
        return [json.loads(l) for l in f if l.strip()]

SAMPLE_SNAPSHOT = [
    {"market_ticker":"KXBTC-TEST-T95000","strike":95000.0,"expiry":"2099-01-01T00:07:00Z",
     "minutes_to_expiry":7.0,"best_yes_bid":46.0,"best_yes_ask":50.0,"best_no_bid":50.0,
     "best_no_ask":54.0,"spread_cents":4.0,"depth_bid":80.0,"depth_ask":80.0,
     "book_timestamp":"2099-01-01T00:00:00Z","spot_price":95000.0,"p_raw":0.72,"side":"yes"},
    {"market_ticker":"KXBTC-TEST-T95000","strike":95000.0,"expiry":"2099-01-01T00:07:00Z",
     "minutes_to_expiry":6.5,"best_yes_bid":44.0,"best_yes_ask":56.0,"best_no_bid":44.0,
     "best_no_ask":56.0,"spread_cents":12.0,"depth_bid":40.0,"depth_ask":40.0,
     "book_timestamp":"2099-01-01T00:00:30Z","spot_price":94850.0,"p_raw":0.65,"side":"yes"},
    {"market_ticker":"KXBTC-TEST-T95000","strike":95000.0,"expiry":"2099-01-01T00:07:00Z",
     "minutes_to_expiry":6.0,"best_yes_bid":47.0,"best_yes_ask":51.0,"best_no_bid":49.0,
     "best_no_ask":53.0,"spread_cents":4.0,"depth_bid":90.0,"depth_ask":85.0,
     "book_timestamp":"2099-01-01T00:01:00Z","spot_price":94780.0,"p_raw":0.50,"side":"yes"},
]

def make_collector(tmp_path, mode="loop-smoke", max_cycles=3, snapshots=None, poll_seconds=0):
    log_file = str(tmp_path / "dry_run_events_YYYY-MM-DD.jsonl")
    c = Collector(mode=mode, log_file=log_file, duration_minutes=60, poll_seconds=poll_seconds,
                  max_cycles=max_cycles, run_id="test-run-001")
    if snapshots is not None: c.snapshots = snapshots
    return c

class TestLoopSmoke:
    def test_max_cycles_stops_loop(self, tmp_path):
        c = make_collector(tmp_path, max_cycles=4); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        assert len([e for e in events if e["event_type"]=="signal_generated"]) == 4

    def test_run_summary_logged_at_exit(self, tmp_path):
        c = make_collector(tmp_path, max_cycles=3); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        summary = [e for e in events if e["event_type"]=="run_summary"]
        assert len(summary) == 1
        assert summary[0]["total_cycles"] == 3
        assert summary[0]["run_id"] == "test-run-001"

    def test_run_id_and_cycle_id_on_every_event(self, tmp_path):
        c = make_collector(tmp_path, max_cycles=2); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        for e in events:
            if e["event_type"] == "run_summary": continue
            assert e.get("run_id") == "test-run-001"
            assert "cycle_id" in e

    def test_signal_source_logged(self, tmp_path):
        c = make_collector(tmp_path, max_cycles=2); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        for e in [e for e in events if e["event_type"]=="signal_generated"]:
            assert e.get("signal_source") == "fixed_signal"

    def test_log_file_named_with_date(self, tmp_path):
        c = make_collector(tmp_path, max_cycles=1); c.run()
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert today in list(tmp_path.glob("*.jsonl"))[0].name

    def test_no_live_orders_submitted(self, tmp_path):
        from kalshi_btc15m_bot.app import StubKalshiClient
        c = make_collector(tmp_path, max_cycles=5); c.run()
        assert isinstance(c.pipeline.client, StubKalshiClient)

class TestReplayMode:
    def test_replay_cycles_through_snapshots(self, tmp_path):
        c = make_collector(tmp_path, mode="replay", max_cycles=3, snapshots=SAMPLE_SNAPSHOT); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        assert len([e for e in events if e["event_type"]=="signal_generated"]) == 3

    def test_replay_produces_three_required_scenario_types(self, tmp_path):
        c = make_collector(tmp_path, mode="replay", max_cycles=3, snapshots=SAMPLE_SNAPSHOT); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        assert len([e for e in events if e["event_type"]=="trade_skipped"]) >= 1
        assert len([e for e in events if e["event_type"]=="order_filled"]) >= 1

    def test_replay_signal_source_logged(self, tmp_path):
        c = make_collector(tmp_path, mode="replay", max_cycles=2, snapshots=SAMPLE_SNAPSHOT); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        for e in [e for e in events if e["event_type"]=="signal_generated"]:
            assert e.get("signal_source") == "snapshot_stored"

    def test_replay_wraps_around_snapshots(self, tmp_path):
        c = make_collector(tmp_path, mode="replay", max_cycles=6, snapshots=SAMPLE_SNAPSHOT); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        assert len([e for e in events if e["event_type"]=="signal_generated"]) == 6

class TestSignalSourceError:
    def test_empty_snapshots_logs_signal_source_error(self, tmp_path):
        c = make_collector(tmp_path, mode="replay", max_cycles=2, snapshots=[]); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        assert any(e.get("skip_reason")=="SIGNAL_SOURCE_ERROR" for e in events if e["event_type"]=="trade_skipped")

    def test_signal_source_error_does_not_crash_loop(self, tmp_path):
        c = make_collector(tmp_path, mode="replay", max_cycles=3, snapshots=[]); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        summary = [e for e in events if e["event_type"]=="run_summary"]
        assert len(summary) == 1
        assert summary[0]["errors"] == 3

class TestSnapshotTimestampInvalid:
    def test_replay_mode_raises_on_malformed_book_timestamp(self):
        with pytest.raises(SnapshotTimestampInvalid):
            _parse_book_ts_ms("not-a-timestamp", 1_700_000_000_000, "replay")

    def test_live_mode_raises_on_missing_book_timestamp(self):
        with pytest.raises(SnapshotTimestampInvalid):
            _parse_book_ts_ms(None, 1_700_000_000_000, "live")

    def test_loop_smoke_mode_uses_fallback_for_malformed_book_timestamp(self):
        assert _parse_book_ts_ms("not-a-timestamp", 1_700_000_000_000, "loop-smoke") == 1_699_999_999_500

    def test_replay_cycle_skips_malformed_timestamp_without_signal(self, tmp_path):
        bad_snapshot = [dict(SAMPLE_SNAPSHOT[0], book_timestamp="not-a-timestamp")]
        c = make_collector(tmp_path, mode="replay", max_cycles=1, snapshots=bad_snapshot)
        c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        assert not [e for e in events if e["event_type"] == "signal_generated"]
        assert any(e.get("skip_reason") == "SNAPSHOT_TIMESTAMP_INVALID" for e in events if e["event_type"] == "trade_skipped")
        summary = next(e for e in events if e["event_type"] == "run_summary")
        assert summary["skipped"] == 1
        assert summary["errors"] == 0

class TestRunSummary:
    def test_run_summary_counts_accurate(self, tmp_path):
        c = make_collector(tmp_path, mode="replay", max_cycles=3, snapshots=SAMPLE_SNAPSHOT); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        summary = next(e for e in events if e["event_type"]=="run_summary")
        assert summary["total_cycles"] == 3
        assert summary["filled"]+summary["skipped"]+summary["errors"] == 3
        assert summary["mode"] == "replay"

TRADABLE_SCORER_SNAPSHOT = [
    {"market_ticker":"KXBTC-SCORER-TRADABLE","strike":95000.0,"expiry":"2099-01-01T00:07:00Z",
     "minutes_to_expiry":7.0,"best_yes_bid":75.0,"best_yes_ask":79.0,"best_no_bid":21.0,
     "best_no_ask":25.0,"spread_cents":4.0,"depth_bid":80.0,"depth_ask":80.0,
     "book_timestamp":"2099-01-01T00:00:00Z","spot_price":95000.0,
     "features":{"ret_1m":-0.008,"ret_3m":-0.015,"realized_vol":0.001,"momentum_score":-2.5,"meanrev_score":0.0},
     "context":{"outcome_yes_rate":0.2,"open_mid_continuation_rate":0.3,"mid_close_reversal_rate":0.7},
     "phase":"phase2"}
]

class TestScaffoldScorerReplay:
    def test_snapshot_without_p_raw_triggers_scorer_path(self, tmp_path):
        c = make_collector(tmp_path, mode="replay", max_cycles=1, snapshots=TRADABLE_SCORER_SNAPSHOT); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        summary = [e for e in events if e["event_type"]=="run_summary"]
        assert len(summary) == 1
        signal_events = [e for e in events if e["event_type"]=="signal_generated"]
        skips = [e for e in events if e["event_type"]=="trade_skipped"]
        assert any(e.get("signal_source")=="scaffold_scorer" for e in signal_events) or \
               any(e.get("skip_reason")=="SIGNAL_SOURCE_ERROR" for e in skips)

    def test_deterministic_fixture_produces_scaffold_scorer_signal(self, tmp_path):
        c = make_collector(tmp_path, mode="replay", max_cycles=1, snapshots=TRADABLE_SCORER_SNAPSHOT); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        signal_events = [e for e in events if e["event_type"]=="signal_generated"]
        assert len(signal_events) == 1
        sig = signal_events[0]
        assert sig["signal_source"] == "scaffold_scorer"
        assert sig["side"] == "no"
        assert sig.get("p_raw", 1.0) < 0.2

    def test_snapshot_with_p_raw_uses_stored_not_scorer(self, tmp_path):
        c = make_collector(tmp_path, mode="replay", max_cycles=1, snapshots=SAMPLE_SNAPSHOT[:1])
        with patch("kalshi_btc15m_bot.collector.generate_p_raw_from_scaffold") as mock_scorer:
            c.run(); mock_scorer.assert_not_called()

STALE_SNAPSHOT = [
    {"market_ticker":"KXBTC-STALE-T95000","strike":95000.0,"expiry":"2099-01-01T00:07:00Z",
     "minutes_to_expiry":7.0,"best_yes_bid":75.0,"best_yes_ask":79.0,"best_no_bid":21.0,
     "best_no_ask":25.0,"spread_cents":4.0,"depth_bid":80.0,"depth_ask":80.0,
     "book_timestamp":"2020-01-01T00:00:00Z","spot_price":95000.0,"p_raw":0.72,"side":"yes"}
]

class TestStaleBookReplayIntegration:
    def test_stale_book_snapshot_triggers_stale_orderbook_skip(self, tmp_path):
        c = make_collector(tmp_path, mode="replay", max_cycles=1, snapshots=STALE_SNAPSHOT); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        skips = [e for e in events if e["event_type"]=="trade_skipped"]
        assert len([e for e in events if e["event_type"]=="order_filled"]) == 0
        assert any(e.get("skip_reason")=="STALE_ORDERBOOK" for e in skips)

    def test_fresh_book_snapshot_is_not_stale(self, tmp_path):
        c = make_collector(tmp_path, mode="replay", max_cycles=1, snapshots=TRADABLE_SCORER_SNAPSHOT); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        assert len([e for e in events if e.get("skip_reason")=="STALE_ORDERBOOK"]) == 0

class TestRunSummaryMetadata:
    def test_run_summary_has_null_cycle_id(self, tmp_path):
        c = make_collector(tmp_path, mode="loop-smoke", max_cycles=3); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        summary = next(e for e in events if e["event_type"]=="run_summary")
        assert summary.get("cycle_id") is None

    def test_run_summary_has_null_signal_source(self, tmp_path):
        c = make_collector(tmp_path, mode="loop-smoke", max_cycles=3); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        summary = next(e for e in events if e["event_type"]=="run_summary")
        assert summary.get("signal_source") is None

    def test_run_summary_has_signal_sources_by_count(self, tmp_path):
        c = make_collector(tmp_path, mode="loop-smoke", max_cycles=3); c.run()
        events = read_events(list(tmp_path.glob("*.jsonl"))[0])
        summary = next(e for e in events if e["event_type"]=="run_summary")
        assert "signal_sources_by_count" in summary
        assert summary["signal_sources_by_count"].get("fixed_signal", 0) == 3
