import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class GoalStatus(str, Enum):
    active = "active"
    completed = "completed"
    archived = "archived"


class FrequencyUnit(str, Enum):
    daily = "daily"
    weekly = "weekly"


class Goal(SQLModel, table=True):
    __tablename__ = "goals"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    parent_goal_id: Optional[uuid.UUID] = Field(default=None, foreign_key="goals.id")
    name: str
    description: Optional[str] = None
    status: GoalStatus = Field(default=GoalStatus.active)
    target_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class Habit(SQLModel, table=True):
    __tablename__ = "habits"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    goal_id: uuid.UUID = Field(foreign_key="goals.id")
    name: str
    frequency_target: int
    frequency_unit: FrequencyUnit
    start_date: date
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class HabitLog(SQLModel, table=True):
    __tablename__ = "habit_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    habit_id: uuid.UUID = Field(foreign_key="habits.id")
    completed_at: datetime
    note: Optional[str] = None


class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    goal_id: Optional[uuid.UUID] = Field(default=None, foreign_key="goals.id")
    title: str
    due_datetime: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class Reminder(SQLModel, table=True):
    __tablename__ = "reminders"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str
    trigger_datetime: datetime
    fired_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
