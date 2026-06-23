from fastapi import FastAPI

from api.goals import router as goals_router
from api.habits import router as habits_router
from api.reminders import router as reminders_router
from api.tasks import router as tasks_router

app = FastAPI(title="Tasks Service")

app.include_router(goals_router)
app.include_router(habits_router)
app.include_router(tasks_router)
app.include_router(reminders_router)
