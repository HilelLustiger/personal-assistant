from datetime import date, datetime, timedelta


def find_week_bounds(day: date) -> tuple[datetime, datetime]:
    monday = day - timedelta(days=day.weekday())
    sunday = monday + timedelta(days=6)
    week_start = datetime(monday.year, monday.month, monday.day, 0, 0, 0)
    week_end = datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59)
    return week_start, week_end


def completions_in_range(habit_id, logs: list, start: datetime, end: datetime) -> int:
    return sum(
        1 for log in logs
        if log.habit_id == habit_id
        and start <= log.completed_at.replace(tzinfo=None) <= end
    )


def needs_log_in_range(habit, logs: list, start: datetime, end: datetime) -> bool:
    return completions_in_range(habit.id, logs, start, end) < habit.frequency_target
