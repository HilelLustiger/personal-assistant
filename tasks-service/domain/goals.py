from datetime import datetime

from domain.habits import count_completions_in_range


def get_goal_progress(
    goal, habits_with_logs: list, tasks: list, start: datetime, end: datetime
) -> dict:
    habit_results = []
    for habit, logs in habits_with_logs:
        count = count_completions_in_range(habit.id, logs, start, end)
        rate = (
            min(count / habit.frequency_target, 1.0) if habit.frequency_target else 0.0
        )
        habit_results.append(
            {
                "id": habit.id,
                "completion_rate": rate,
                "completions_in_range": count,
            }
        )

    tasks_completed = sum(1 for task in tasks if task.completed_at is not None)
    return {
        "habits": habit_results,
        "tasks_completed": tasks_completed,
        "tasks_total": len(tasks),
    }
