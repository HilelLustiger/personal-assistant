from datetime import date, datetime, timedelta


def find_week_bounds(day: date) -> tuple[datetime, datetime]:
    sunday = day - timedelta(days=day.isoweekday() % 7)
    saturday = sunday + timedelta(days=6)
    week_start = datetime(sunday.year, sunday.month, sunday.day, 0, 0, 0)
    week_end = datetime(saturday.year, saturday.month, saturday.day, 23, 59, 59)
    return week_start, week_end


def count_completions_in_range(
    habit_id, logs: list, start: datetime, end: datetime
) -> int:
    return sum(
        1
        for log in logs
        if log.habit_id == habit_id
        and start <= log.completed_at.replace(tzinfo=None) <= end
    )


def is_habit_hit_in_range(habit, logs: list, start: datetime, end: datetime) -> bool:
    return (
        count_completions_in_range(habit.id, logs, start, end) < habit.frequency_target
    )
