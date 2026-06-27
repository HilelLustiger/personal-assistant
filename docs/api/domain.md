# Module: tasks-service/domain

## domain/habits.py

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `find_week_bounds(day)` | `day: date` | `tuple[datetime, datetime]` | Returns `(sunday_00:00, saturday_23:59:59)` for the week containing `day` |
| `count_completions_in_range(habit_id, logs, start, end)` | `habit_id: UUID`, `logs: list`, `start: datetime`, `end: datetime` | `int` | Count of log entries for this habit within the datetime range |
| `is_habit_hit_in_range(habit, logs, start, end)` | `habit`, `logs: list`, `start: datetime`, `end: datetime` | `bool` | True if `count_completions_in_range < habit.frequency_target` — habit still needs a log |

## domain/tasks.py

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `is_overdue(task, now)` | `task`, `now: datetime` | `bool` | True if `due_datetime` is set, task is not completed, and `due_datetime < now` |

## domain/goals.py

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `get_goal_progress(goal, habits_with_logs, tasks, start, end)` | `goal`, `habits_with_logs: list[tuple]`, `tasks: list`, `start: datetime`, `end: datetime` | `dict` | Returns `{habits: [{id, completion_rate, completions_in_range}], tasks_completed, tasks_total}` |

## domain/reminders.py

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `is_due(reminder, now)` | `reminder`, `now: datetime` | `bool` | True if `fired_at` is None and `trigger_datetime <= now` |
