import uuid
from datetime import date as Date
from datetime import datetime, timezone
from typing import Optional

from db.models import Task
from db.session import get_session
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, SQLModel, select

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(SQLModel):
    title: str
    due_datetime: Optional[datetime] = None
    goal_id: Optional[uuid.UUID] = None


class TaskUpdate(SQLModel):
    title: Optional[str] = None
    due_datetime: Optional[datetime] = None
    goal_id: Optional[uuid.UUID] = None


@router.get("")
def list_tasks(
    completed: Optional[bool] = None,
    due_by: Optional[Date] = None,
    due_from: Optional[Date] = None,
    session: Session = Depends(get_session),
):
    query = select(Task)
    if completed is True:
        query = query.where(Task.completed_at.isnot(None))
    elif completed is False:
        query = query.where(Task.completed_at.is_(None))
    if due_by is not None:
        deadline = datetime(due_by.year, due_by.month, due_by.day, 23, 59, 59)
        query = query.where(Task.due_datetime <= deadline)
    if due_from is not None:
        from_dt = datetime(due_from.year, due_from.month, due_from.day)
        query = query.where(Task.due_datetime >= from_dt)
    return session.exec(query).all()


@router.post("", status_code=201)
def create_task(data: TaskCreate, session: Session = Depends(get_session)):
    task = Task(**data.model_dump())
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.patch("/{task_id}")
def update_task(
    task_id: uuid.UUID, data: TaskUpdate, session: Session = Depends(get_session)
):
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: uuid.UUID, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    session.delete(task)
    session.commit()


@router.post("/{task_id}/complete")
def complete_task(task_id: uuid.UUID, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task
