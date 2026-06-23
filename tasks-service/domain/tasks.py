from datetime import datetime


def is_overdue(task, now: datetime) -> bool:
    if task.due_datetime is None:
        return False
    if task.completed_at is not None:
        return False
    due = task.due_datetime
    if due.tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=due.tzinfo)
    elif due.tzinfo is None and now.tzinfo is not None:
        due = due.replace(tzinfo=now.tzinfo)
    return due < now
