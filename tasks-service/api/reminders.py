import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, SQLModel, select

from db.models import Reminder
from db.session import get_session

router = APIRouter(prefix="/reminders", tags=["reminders"])


class ReminderCreate(SQLModel):
    title: str
    trigger_datetime: datetime


class ReminderUpdate(SQLModel):
    title: Optional[str] = None
    trigger_datetime: Optional[datetime] = None


@router.get("")
def list_reminders(
    fired: Optional[bool] = None,
    due_by: Optional[datetime] = None,
    session: Session = Depends(get_session),
):
    query = select(Reminder)
    if fired is True:
        query = query.where(Reminder.fired_at.isnot(None))
    elif fired is False:
        query = query.where(Reminder.fired_at.is_(None))
    if due_by is not None:
        query = query.where(Reminder.trigger_datetime <= due_by)
    return session.exec(query).all()


@router.post("", status_code=201)
def create_reminder(data: ReminderCreate, session: Session = Depends(get_session)):
    reminder = Reminder(**data.model_dump())
    session.add(reminder)
    session.commit()
    session.refresh(reminder)
    return reminder


@router.patch("/{reminder_id}")
def update_reminder(reminder_id: uuid.UUID, data: ReminderUpdate, session: Session = Depends(get_session)):
    reminder = session.get(Reminder, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(reminder, field, value)
    session.add(reminder)
    session.commit()
    session.refresh(reminder)
    return reminder


@router.delete("/{reminder_id}", status_code=204)
def delete_reminder(reminder_id: uuid.UUID, session: Session = Depends(get_session)):
    reminder = session.get(Reminder, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    session.delete(reminder)
    session.commit()


@router.post("/{reminder_id}/fire")
def fire_reminder(reminder_id: uuid.UUID, session: Session = Depends(get_session)):
    reminder = session.get(Reminder, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    reminder.fired_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.add(reminder)
    session.commit()
    session.refresh(reminder)
    return reminder
