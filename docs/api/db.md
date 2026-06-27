# Module: tasks-service/db

## Models

| Name | Type | Description |
|---|---|---|
| `Goal` | SQLModel table | ORM model for goals |
| `Habit` | SQLModel table | ORM model for habits |
| `HabitLog` | SQLModel table | ORM model for habit completion entries |
| `Task` | SQLModel table | ORM model for tasks |
| `Reminder` | SQLModel table | ORM model for reminders |

## Session

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `get_session()` | — | `Generator[Session, None, None]` | FastAPI dependency; yields one DB session per request |
| `engine` | — | `Engine` | SQLAlchemy engine; used by Alembic and test setup |
