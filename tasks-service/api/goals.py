import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, SQLModel, select

from db.models import Goal, Habit, HabitLog, Task
from db.session import get_session
from domain.goals import goal_progress
from domain.habits import find_week_bounds

router = APIRouter(prefix="/goals", tags=["goals"])


class GoalCreate(SQLModel):
    name: str
    description: Optional[str] = None
    status: Optional[str] = None
    target_date: Optional[datetime] = None
    parent_goal_id: Optional[uuid.UUID] = None


class GoalUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    target_date: Optional[datetime] = None
    parent_goal_id: Optional[uuid.UUID] = None


@router.get("")
def list_goals(status: Optional[str] = None, session: Session = Depends(get_session)):
    query = select(Goal)
    if status is not None and status != "all":
        query = query.where(Goal.status == status)
    return session.exec(query).all()


@router.post("", status_code=201)
def create_goal(data: GoalCreate, session: Session = Depends(get_session)):
    goal_data = data.model_dump(exclude_none=True)
    goal = Goal(**goal_data)
    session.add(goal)
    session.commit()
    session.refresh(goal)
    return goal


@router.patch("/{goal_id}")
def update_goal(goal_id: uuid.UUID, data: GoalUpdate, session: Session = Depends(get_session)):
    goal = session.get(Goal, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)
    session.add(goal)
    session.commit()
    session.refresh(goal)
    return goal


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: uuid.UUID, session: Session = Depends(get_session)):
    goal = session.get(Goal, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    # Delete children in order: habit_logs → tasks → habits → goal
    habits = session.exec(select(Habit).where(Habit.goal_id == goal_id)).all()
    for habit in habits:
        for log in session.exec(select(HabitLog).where(HabitLog.habit_id == habit.id)).all():
            session.delete(log)
        session.delete(habit)
    for task in session.exec(select(Task).where(Task.goal_id == goal_id)).all():
        session.delete(task)
    session.delete(goal)
    session.commit()


@router.get("/{goal_id}/progress")
def get_goal_progress(goal_id: uuid.UUID, session: Session = Depends(get_session)):
    goal = session.get(Goal, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")

    habits = session.exec(select(Habit).where(Habit.goal_id == goal_id)).all()
    tasks = session.exec(select(Task).where(Task.goal_id == goal_id)).all()

    today = datetime.now(timezone.utc).replace(tzinfo=None).date()
    week_start, week_end = find_week_bounds(today)

    habits_with_logs = []
    for habit in habits:
        logs = session.exec(select(HabitLog).where(HabitLog.habit_id == habit.id)).all()
        habits_with_logs.append((habit, logs))

    progress = goal_progress(goal, habits_with_logs, tasks, week_start, week_end)

    progress_by_habit_id = {item["id"]: item for item in progress["habits"]}
    habit_list = [
        {
            "id": habit.id,
            "name": habit.name,
            "frequency_target": habit.frequency_target,
            "frequency_unit": habit.frequency_unit,
            "completions_this_week": progress_by_habit_id[habit.id]["completions_in_range"],
            "completion_rate": progress_by_habit_id[habit.id]["completion_rate"],
        }
        for habit in habits
    ]

    return {
        "id": goal.id,
        "name": goal.name,
        "description": goal.description,
        "status": goal.status,
        "target_date": goal.target_date,
        "parent_goal_id": goal.parent_goal_id,
        "created_at": goal.created_at,
        "habits": habit_list,
        "tasks_completed": progress["tasks_completed"],
        "tasks_total": progress["tasks_total"],
    }
