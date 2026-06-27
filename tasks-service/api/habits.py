import uuid
from datetime import date as Date
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, SQLModel, select

from db.models import Habit, HabitLog
from db.session import get_session
from domain.habits import count_completions_in_range, find_week_bounds, is_habit_hit_in_range

router = APIRouter(prefix="/habits", tags=["habits"])


class HabitCreate(SQLModel):
    name: str
    goal_id: uuid.UUID
    frequency_target: int
    frequency_unit: str
    start_date: Date


class HabitUpdate(SQLModel):
    name: Optional[str] = None
    frequency_target: Optional[int] = None
    frequency_unit: Optional[str] = None
    active: Optional[bool] = None


class HabitLogCreate(SQLModel):
    note: Optional[str] = None


@router.get("")
def list_habits(
    active: Optional[bool] = None,
    date: Optional[Date] = None,
    session: Session = Depends(get_session),
):
    query = select(Habit)
    if active is not None:
        query = query.where(Habit.active == active)
    habits = session.exec(query).all()

    if date is None:
        return habits

    week_start, week_end = find_week_bounds(date)
    results = []
    for habit in habits:
        logs = session.exec(select(HabitLog).where(HabitLog.habit_id == habit.id)).all()
        count = count_completions_in_range(habit.id, logs, week_start, week_end)
        needs_log = is_habit_hit_in_range(habit, logs, week_start, week_end)
        habit_dict = habit.model_dump()
        habit_dict["needs_log_today"] = needs_log
        habit_dict["completions_this_week"] = count
        results.append(habit_dict)
    return results


@router.post("", status_code=201)
def create_habit(data: HabitCreate, session: Session = Depends(get_session)):
    habit = Habit(**data.model_dump())
    session.add(habit)
    session.commit()
    session.refresh(habit)
    return habit


@router.patch("/{habit_id}")
def update_habit(habit_id: uuid.UUID, data: HabitUpdate, session: Session = Depends(get_session)):
    habit = session.get(Habit, habit_id)
    if habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(habit, field, value)
    session.add(habit)
    session.commit()
    session.refresh(habit)
    return habit


@router.delete("/{habit_id}", status_code=204)
def delete_habit(habit_id: uuid.UUID, session: Session = Depends(get_session)):
    habit = session.get(Habit, habit_id)
    if habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    for log in session.exec(select(HabitLog).where(HabitLog.habit_id == habit_id)).all():
        session.delete(log)
    session.delete(habit)
    session.commit()


@router.post("/{habit_id}/log", status_code=201)
def log_habit(habit_id: uuid.UUID, data: HabitLogCreate, session: Session = Depends(get_session)):
    habit = session.get(Habit, habit_id)
    if habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    log = HabitLog(habit_id=habit_id, completed_at=datetime.now(timezone.utc).replace(tzinfo=None), note=data.note)
    session.add(log)
    session.commit()
    session.refresh(log)
    return log
