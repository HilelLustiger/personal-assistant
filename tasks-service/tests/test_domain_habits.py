"""Tests for domain/habits.py."""

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


WEEK_START = datetime(2026, 6, 21, 0, 0, 0)  # Sunday
WEEK_END = datetime(2026, 6, 27, 23, 59, 59)  # Saturday


# --- find_week_bounds ---


def test_find_week_bounds_given_wednesday_returns_sunday_to_saturday():
    from domain.habits import find_week_bounds

    bounds_start, bounds_end = find_week_bounds(date(2026, 6, 24))  # Wednesday
    assert bounds_start == datetime(2026, 6, 21, 0, 0, 0)
    assert bounds_end == datetime(2026, 6, 27, 23, 59, 59)


def test_find_week_bounds_given_sunday_returns_same_sunday():
    from domain.habits import find_week_bounds

    bounds_start, bounds_end = find_week_bounds(date(2026, 6, 21))  # Sunday
    assert bounds_start == datetime(2026, 6, 21, 0, 0, 0)
    assert bounds_end == datetime(2026, 6, 27, 23, 59, 59)


def test_find_week_bounds_given_saturday_returns_preceding_sunday():
    from domain.habits import find_week_bounds

    bounds_start, bounds_end = find_week_bounds(date(2026, 6, 27))  # Saturday
    assert bounds_start == datetime(2026, 6, 21, 0, 0, 0)
    assert bounds_end == datetime(2026, 6, 27, 23, 59, 59)


# --- count_completions_in_range ---


def test_count_completions_in_range_counts_logs_within_range():
    from domain.habits import count_completions_in_range

    h = _make_habit()
    logs = [
        _make_log(h.id, datetime(2026, 6, 22, 9, 0)),
        _make_log(h.id, datetime(2026, 6, 23, 10, 0)),
        _make_log(uuid.uuid4(), datetime(2026, 6, 22, 8, 0)),  # different habit
    ]
    assert count_completions_in_range(h.id, logs, WEEK_START, WEEK_END) == 2


def test_count_completions_in_range_excludes_logs_outside_range():
    from domain.habits import count_completions_in_range

    h = _make_habit()
    logs = [
        _make_log(h.id, datetime(2026, 6, 15, 9, 0)),  # prior week
        _make_log(h.id, datetime(2026, 6, 22, 9, 0)),  # this week
        _make_log(h.id, datetime(2026, 6, 29, 9, 0)),  # next week
    ]
    assert count_completions_in_range(h.id, logs, WEEK_START, WEEK_END) == 1


def test_count_completions_in_range_includes_boundary_timestamps():
    from domain.habits import count_completions_in_range

    h = _make_habit()
    logs = [
        _make_log(h.id, WEEK_START),
        _make_log(h.id, WEEK_END),
    ]
    assert count_completions_in_range(h.id, logs, WEEK_START, WEEK_END) == 2


def test_count_completions_in_range_empty_logs():
    from domain.habits import count_completions_in_range

    assert count_completions_in_range(uuid.uuid4(), [], WEEK_START, WEEK_END) == 0


def test_count_completions_in_range_custom_range():
    from domain.habits import count_completions_in_range

    h = _make_habit()
    start = datetime(2026, 6, 22, 0, 0)
    end = datetime(2026, 6, 22, 23, 59, 59)
    logs = [
        _make_log(h.id, datetime(2026, 6, 22, 8, 0)),
        _make_log(h.id, datetime(2026, 6, 22, 20, 0)),
        _make_log(h.id, datetime(2026, 6, 23, 8, 0)),  # next day — excluded
    ]
    assert count_completions_in_range(h.id, logs, start, end) == 2


# --- is_habit_hit_in_range ---


def test_is_habit_hit_in_range_true_when_under_target():
    from domain.habits import is_habit_hit_in_range

    h = _make_habit(freq_target=3)
    logs = [_make_log(h.id, datetime(2026, 6, 22, 9, 0))]  # 1 of 3
    assert is_habit_hit_in_range(h, logs, WEEK_START, WEEK_END) is True


def test_is_habit_hit_in_range_false_when_at_target():
    from domain.habits import is_habit_hit_in_range

    h = _make_habit(freq_target=2)
    logs = [
        _make_log(h.id, datetime(2026, 6, 22, 9, 0)),
        _make_log(h.id, datetime(2026, 6, 23, 10, 0)),
    ]
    assert is_habit_hit_in_range(h, logs, WEEK_START, WEEK_END) is False


def test_is_habit_hit_in_range_false_when_over_target():
    from domain.habits import is_habit_hit_in_range

    h = _make_habit(freq_target=2)
    logs = [
        _make_log(h.id, datetime(2026, 6, 22, 9, 0)),
        _make_log(h.id, datetime(2026, 6, 23, 9, 0)),
        _make_log(h.id, datetime(2026, 6, 24, 9, 0)),
    ]
    assert is_habit_hit_in_range(h, logs, WEEK_START, WEEK_END) is False
