from datetime import datetime, timedelta
from kalshi_btc15m_bot.market.clocks import elapsed_seconds, phase_from_clock, remaining_seconds

def test_elapsed_and_remaining_are_non_negative():
    now = datetime(2024, 1, 1, 0, 5, 0)
    open_time = datetime(2024, 1, 1, 0, 0, 0)
    close_time = datetime(2024, 1, 1, 0, 15, 0)
    assert elapsed_seconds(open_time, now) == 300
    assert remaining_seconds(close_time, now) == 600
    assert elapsed_seconds(open_time, datetime(2023, 12, 31, 23, 59, 0)) == 0
    assert remaining_seconds(close_time, datetime(2024, 1, 1, 0, 16, 0)) == 0

def test_phase_from_clock_uses_actual_open_and_close_times():
    open_time = datetime(2024, 1, 1, 0, 0, 0)
    close_time = datetime(2024, 1, 1, 0, 15, 0)
    assert phase_from_clock(open_time, close_time, open_time + timedelta(seconds=60)) == "phase1"
    assert phase_from_clock(open_time, close_time, open_time + timedelta(seconds=240)) == "phase2"
    assert phase_from_clock(open_time, close_time, open_time + timedelta(seconds=540)) == "phase3"
    assert phase_from_clock(open_time, close_time, close_time - timedelta(seconds=30)) == "final_minute"
