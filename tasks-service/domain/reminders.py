from datetime import datetime


def is_due(reminder, now: datetime) -> bool:
    if reminder.fired_at is not None:
        return False
    trigger = reminder.trigger_datetime
    if trigger.tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=trigger.tzinfo)
    elif trigger.tzinfo is None and now.tzinfo is not None:
        trigger = trigger.replace(tzinfo=now.tzinfo)
    return trigger <= now
