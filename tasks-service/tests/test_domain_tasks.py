"""Tests for domain/tasks.py — TDD for T03."""
from datetime import datetime, timezone


def _make_task(due=None, completed_at=None):
    class T:
        pass
    t = T()
    t.due_datetime = due
    t.completed_at = completed_at
    return t


NOW = datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc)


def test_is_overdue_true_when_past_due_and_open():
    from domain.tasks import is_overdue
    task = _make_task(due=datetime(2026, 6, 20, 9, 0, tzinfo=timezone.utc))
    assert is_overdue(task, NOW) is True


def test_is_overdue_false_when_no_due_datetime():
    from domain.tasks import is_overdue
    task = _make_task(due=None)
    assert is_overdue(task, NOW) is False


def test_is_overdue_false_when_already_completed():
    from domain.tasks import is_overdue
    task = _make_task(
        due=datetime(2026, 6, 20, 9, 0, tzinfo=timezone.utc),
        completed_at=datetime(2026, 6, 21, 8, 0, tzinfo=timezone.utc),
    )
    assert is_overdue(task, NOW) is False


def test_is_overdue_false_when_due_in_future():
    from domain.tasks import is_overdue
    task = _make_task(due=datetime(2026, 6, 25, 9, 0, tzinfo=timezone.utc))
    assert is_overdue(task, NOW) is False
