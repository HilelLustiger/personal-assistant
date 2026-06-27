"""Tests for domain/goals.py."""
import uuid
from datetime import datetime


def _make_goal():
    class G:
        id = uuid.uuid4()
        name = "Test Goal"
    return G()


def _make_task(completed_at=None):
    class T:
        pass
    t = T()
    t.completed_at = completed_at
    return t


WEEK_START = datetime(2026, 6, 21, 0, 0, 0)    # Sunday
WEEK_END   = datetime(2026, 6, 27, 23, 59, 59)  # Saturday


def test_get_goal_progress_completion_rate_capped_at_one():
    from domain.goals import get_goal_progress
    goal = _make_goal()
    h_id = uuid.uuid4()

    class H:
        id = h_id
        frequency_target = 2
        frequency_unit = "weekly"

    class L:
        habit_id = h_id
        completed_at = datetime(2026, 6, 22, 9, 0)

    logs = [L(), L(), L()]  # 3 completions for target=2 → rate capped at 1.0
    result = get_goal_progress(goal, [(H(), logs)], [], WEEK_START, WEEK_END)
    assert result["habits"][0]["completion_rate"] == 1.0


def test_get_goal_progress_partial_rate():
    from domain.goals import get_goal_progress
    goal = _make_goal()
    h_id = uuid.uuid4()

    class H:
        id = h_id
        frequency_target = 4
        frequency_unit = "weekly"

    class L:
        habit_id = h_id
        completed_at = datetime(2026, 6, 22, 9, 0)

    logs = [L(), L()]  # 2 of 4
    result = get_goal_progress(goal, [(H(), logs)], [], WEEK_START, WEEK_END)
    assert result["habits"][0]["completion_rate"] == 0.5


def test_get_goal_progress_tasks_completed_and_total():
    from domain.goals import get_goal_progress
    goal = _make_goal()
    tasks = [
        _make_task(completed_at=datetime(2026, 6, 22, 9, 0)),
        _make_task(),
        _make_task(completed_at=datetime(2026, 6, 23, 10, 0)),
    ]
    result = get_goal_progress(goal, [], tasks, WEEK_START, WEEK_END)
    assert result["tasks_completed"] == 2
    assert result["tasks_total"] == 3


def test_get_goal_progress_empty():
    from domain.goals import get_goal_progress
    goal = _make_goal()
    result = get_goal_progress(goal, [], [], WEEK_START, WEEK_END)
    assert result["habits"] == []
    assert result["tasks_completed"] == 0
    assert result["tasks_total"] == 0


def test_get_goal_progress_excludes_logs_outside_range():
    from domain.goals import get_goal_progress
    goal = _make_goal()
    h_id = uuid.uuid4()

    class H:
        id = h_id
        frequency_target = 2
        frequency_unit = "weekly"

    class LIn:
        habit_id = h_id
        completed_at = datetime(2026, 6, 23, 9, 0)  # inside range

    class LOut:
        habit_id = h_id
        completed_at = datetime(2026, 6, 15, 9, 0)  # prior week — outside

    logs = [LIn(), LOut()]
    result = get_goal_progress(goal, [(H(), logs)], [], WEEK_START, WEEK_END)
    assert result["habits"][0]["completions_in_range"] == 1
    assert result["habits"][0]["completion_rate"] == 0.5
