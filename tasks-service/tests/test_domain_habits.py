"""Tests for domain/habits.py — TDD for T03."""
import uuid
from datetime import date, datetime


def _make_habit(freq_target=3, freq_unit="weekly"):
    class H:
        id = uuid.uuid4()
        frequency_target = freq_target
        frequency_unit = freq_unit
    return H()


def _make_log(habit_id, completed_at: datetime):
    class L:
        pass
    log = L()
    log.habit_id = habit_id
    log.completed_at = completed_at
    return log


WEEK_START = datetime(2026, 6, 22, 0, 0, 0)   # Monday
WEEK_END   = datetime(2026, 6, 28, 23, 59, 59) # Sunday


# --- completions_in_range ---

def test_completions_in_range_counts_logs_within_range():
    from domain.habits import completions_in_range
    h = _make_habit()
    logs = [
        _make_log(h.id, datetime(2026, 6, 22, 9, 0)),
        _make_log(h.id, datetime(2026, 6, 23, 10, 0)),
        _make_log(uuid.uuid4(), datetime(2026, 6, 22, 8, 0)),  # different habit
    ]
    assert completions_in_range(h.id, logs, WEEK_START, WEEK_END) == 2


def test_completions_in_range_excludes_logs_outside_range():
    from domain.habits import completions_in_range
    h = _make_habit()
    logs = [
        _make_log(h.id, datetime(2026, 6, 15, 9, 0)),  # prior week
        _make_log(h.id, datetime(2026, 6, 22, 9, 0)),  # this week
        _make_log(h.id, datetime(2026, 6, 29, 9, 0)),  # next week
    ]
    assert completions_in_range(h.id, logs, WEEK_START, WEEK_END) == 1


def test_completions_in_range_includes_boundary_timestamps():
    from domain.habits import completions_in_range
    h = _make_habit()
    logs = [
        _make_log(h.id, WEEK_START),  # exactly at start
        _make_log(h.id, WEEK_END),    # exactly at end
    ]
    assert completions_in_range(h.id, logs, WEEK_START, WEEK_END) == 2


def test_completions_in_range_empty_logs():
    from domain.habits import completions_in_range
    assert completions_in_range(uuid.uuid4(), [], WEEK_START, WEEK_END) == 0


def test_completions_in_range_custom_range():
    from domain.habits import completions_in_range
    h = _make_habit()
    start = datetime(2026, 6, 22, 0, 0)
    end   = datetime(2026, 6, 22, 23, 59, 59)  # single day
    logs = [
        _make_log(h.id, datetime(2026, 6, 22, 8, 0)),
        _make_log(h.id, datetime(2026, 6, 22, 20, 0)),
        _make_log(h.id, datetime(2026, 6, 23, 8, 0)),  # next day — excluded
    ]
    assert completions_in_range(h.id, logs, start, end) == 2


# --- needs_log_in_range ---

def test_needs_log_in_range_true_when_under_target():
    from domain.habits import needs_log_in_range
    h = _make_habit(freq_target=3)
    logs = [_make_log(h.id, datetime(2026, 6, 22, 9, 0))]  # 1 of 3
    assert needs_log_in_range(h, logs, WEEK_START, WEEK_END) is True


def test_needs_log_in_range_false_when_at_target():
    from domain.habits import needs_log_in_range
    h = _make_habit(freq_target=2)
    logs = [
        _make_log(h.id, datetime(2026, 6, 22, 9, 0)),
        _make_log(h.id, datetime(2026, 6, 23, 10, 0)),
    ]
    assert needs_log_in_range(h, logs, WEEK_START, WEEK_END) is False


def test_needs_log_in_range_false_when_over_target():
    from domain.habits import needs_log_in_range
    h = _make_habit(freq_target=2)
    logs = [
        _make_log(h.id, datetime(2026, 6, 22, 9, 0)),
        _make_log(h.id, datetime(2026, 6, 23, 9, 0)),
        _make_log(h.id, datetime(2026, 6, 24, 9, 0)),
    ]
    assert needs_log_in_range(h, logs, WEEK_START, WEEK_END) is False
