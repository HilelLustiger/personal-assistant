# Module: orchestrator/tools

All tools exported via `tools.ALL_TOOLS` (20 total). Thin async HTTP wrappers around tasks-service.

## Goals (5)

| Tool | Parameters | Returns | Description |
|---|---|---|---|
| `list_goals` | `status?: str` | `list` | List goals; filter by `active\|completed\|archived` |
| `create_goal` | `name: str`, `description?: str`, `status?: str`, `target_date?: str`, `parent_goal_id?: str` | `dict` | Create a goal |
| `update_goal` | `goal_id: str`, `name?: str`, `description?: str`, `status?: str`, `target_date?: str`, `parent_goal_id?: str` | `dict` | Partial update a goal |
| `delete_goal` | `goal_id: str` | `dict` | Delete a goal permanently |
| `get_goal_progress` | `goal_id: str` | `dict` | Get habit completion rates and task counts for a goal |

## Tasks (5)

| Tool | Parameters | Returns | Description |
|---|---|---|---|
| `list_tasks` | `completed?: bool`, `due_by?: str`, `due_from?: str` | `list` | List tasks with optional filters |
| `create_task` | `title: str`, `due_datetime?: str`, `goal_id?: str` | `dict` | Create a task |
| `update_task` | `task_id: str`, `title?: str`, `due_datetime?: str`, `goal_id?: str` | `dict` | Partial update a task |
| `delete_task` | `task_id: str` | `dict` | Delete a task permanently |
| `complete_task` | `task_id: str` | `dict` | Mark a task completed; records `completed_at` |

## Habits (5)

| Tool | Parameters | Returns | Description |
|---|---|---|---|
| `list_habits` | `active?: bool`, `date?: str` | `list` | List habits; with `date` adds `needs_log_today`, `completions_this_week` |
| `create_habit` | `name: str`, `goal_id: str`, `frequency_target: int`, `frequency_unit: str`, `start_date: str` | `dict` | Create a habit; `frequency_unit` is `'daily'` or `'weekly'` |
| `update_habit` | `habit_id: str`, `name?: str`, `frequency_target?: int`, `frequency_unit?: str`, `active?: bool` | `dict` | Partial update a habit |
| `delete_habit` | `habit_id: str` | `dict` | Delete a habit and all its logs permanently |
| `log_habit` | `habit_id: str`, `note?: str` | `dict` | Log a completion for today |

## Reminders (5)

| Tool | Parameters | Returns | Description |
|---|---|---|---|
| `list_reminders` | `fired?: bool`, `due_by?: str` | `list` | List reminders with optional filters |
| `create_reminder` | `title: str`, `trigger_datetime: str` | `dict` | Create a reminder |
| `update_reminder` | `reminder_id: str`, `title?: str`, `trigger_datetime?: str` | `dict` | Partial update a reminder |
| `delete_reminder` | `reminder_id: str` | `dict` | Delete a reminder permanently |
| `fire_reminder` | `reminder_id: str` | `dict` | Mark a reminder as fired; records `fired_at` |
