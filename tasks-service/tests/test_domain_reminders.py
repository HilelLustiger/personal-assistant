"""Tests for domain/reminders.py — TDD for T03."""

from datetime import datetime, timezone


def _make_reminder(trigger_datetime, fired_at=None):
    class R:
        pass

    r = R()
    r.trigger_datetime = trigger_datetime
    r.fired_at = fired_at
    return r


NOW = datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc)


def test_is_due_true_when_past_and_not_fired():
    from domain.reminders import is_due

    r = _make_reminder(
        trigger_datetime=datetime(2026, 6, 23, 11, 0, tzinfo=timezone.utc)
    )
    assert is_due(r, NOW) is True


def test_is_due_true_when_exactly_now():
    from domain.reminders import is_due

    r = _make_reminder(trigger_datetime=NOW)
    assert is_due(r, NOW) is True


def test_is_due_false_when_already_fired():
    from domain.reminders import is_due

    r = _make_reminder(
        trigger_datetime=datetime(2026, 6, 23, 11, 0, tzinfo=timezone.utc),
        fired_at=datetime(2026, 6, 23, 11, 1, tzinfo=timezone.utc),
    )
    assert is_due(r, NOW) is False


def test_is_due_false_when_future():
    from domain.reminders import is_due

    r = _make_reminder(
        trigger_datetime=datetime(2026, 6, 24, 9, 0, tzinfo=timezone.utc)
    )
    assert is_due(r, NOW) is False
