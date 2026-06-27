# Module: tasks-service/api

## Goals

| Endpoint | Input | Returns | Notes |
|---|---|---|---|
| `GET /goals` | `?status=active\|completed\|archived` | `list[Goal]` | Omit → return all |
| `POST /goals` | `GoalCreate` body | `Goal` (201) | |
| `PATCH /goals/{goal_id}` | `GoalUpdate` body | `Goal` | Partial update |
| `DELETE /goals/{goal_id}` | — | 204 | Cascade behavior pending design decision |
| `GET /goals/{goal_id}/progress` | — | progress dict | `{habits, tasks_completed, tasks_total}` |

## Habits

| Endpoint | Input | Returns | Notes |
|---|---|---|---|
| `GET /habits` | `?active=bool&date=YYYY-MM-DD` | `list[Habit\|dict]` | With `date`: adds `needs_log_today`, `completions_this_week` |
| `POST /habits` | `HabitCreate` body | `Habit` (201) | |
| `PATCH /habits/{habit_id}` | `HabitUpdate` body | `Habit` | |
| `DELETE /habits/{habit_id}` | — | 204 | Cascades habit_logs |
| `POST /habits/{habit_id}/log` | `HabitLogCreate` body | `HabitLog` (201) | Sets `completed_at` to now |

## Tasks

| Endpoint | Input | Returns | Notes |
|---|---|---|---|
| `GET /tasks` | `?completed=bool&due_by=date&due_from=date` | `list[Task]` | All params optional |
| `POST /tasks` | `TaskCreate` body | `Task` (201) | |
| `PATCH /tasks/{task_id}` | `TaskUpdate` body | `Task` | |
| `DELETE /tasks/{task_id}` | — | 204 | |
| `POST /tasks/{task_id}/complete` | — | `Task` | Sets `completed_at` to now |

## Reminders

| Endpoint | Input | Returns | Notes |
|---|---|---|---|
| `GET /reminders` | `?fired=bool&due_by=datetime` | `list[Reminder]` | |
| `POST /reminders` | `ReminderCreate` body | `Reminder` (201) | |
| `PATCH /reminders/{reminder_id}` | `ReminderUpdate` body | `Reminder` | |
| `DELETE /reminders/{reminder_id}` | — | 204 | |
| `POST /reminders/{reminder_id}/fire` | — | `Reminder` | Sets `fired_at` to now |
