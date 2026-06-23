"""Tests for T02: SQLModel models importability and schema correctness."""
import importlib


def test_models_importable():
    mod = importlib.import_module("db.models")
    for cls in ("Goal", "Habit", "HabitLog", "Task", "Reminder"):
        assert hasattr(mod, cls), f"{cls} not found in db.models"


def test_no_forbidden_imports():
    """domain/ and api/ must not be imported by db/models.py."""
    import ast, pathlib
    src = pathlib.Path(__file__).parent.parent / "db" / "models.py"
    tree = ast.parse(src.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            name = (
                node.module if isinstance(node, ast.ImportFrom) else
                ", ".join(a.name for a in node.names)
            )
            assert name is None or (
                "api" not in (name or "") and "domain" not in (name or "")
            ), f"db/models.py must not import from api/ or domain/: found {name}"


def test_goal_fields():
    from db.models import Goal
    fields = Goal.model_fields
    assert "parent_goal_id" in fields
    assert "status" in fields
    assert "target_date" in fields


def test_habit_fields():
    from db.models import Habit
    fields = Habit.model_fields
    assert "goal_id" in fields
    assert "frequency_target" in fields
    assert "frequency_unit" in fields
    assert "active" in fields


def test_habit_log_fields():
    from db.models import HabitLog
    fields = HabitLog.model_fields
    assert "habit_id" in fields
    assert "completed_at" in fields
    assert "note" in fields


def test_task_no_completed_bool():
    """Tasks must use completed_at (nullable timestamp), never a completed bool."""
    from db.models import Task
    fields = Task.model_fields
    assert "completed_at" in fields
    assert "completed" not in fields


def test_reminder_no_fired_bool():
    """Reminders must use fired_at (nullable timestamp), never a fired bool."""
    from db.models import Reminder
    fields = Reminder.model_fields
    assert "fired_at" in fields
    assert "fired" not in fields
