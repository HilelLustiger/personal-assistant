# Phase 1 — Tasks, Habits, Reminders, Goals + Orchestrator

**Status:** Complete (T01–T07)
**Date:** 2026-06-27

## What was built

The full daily-use core of the personal assistant: a tasks-service that
stores and manages tasks, habits, habit logs, reminders, and goals; and an
orchestrator that wraps those capabilities in a conversational LangGraph
agent reachable via Telegram.

## Why it was built

The goal is a personal assistant the user can talk to naturally — "log my
workout", "what's due today?", "remind me at 8pm" — rather than using a
task app manually. Phase 1 establishes the data layer, the agent, and the
Telegram connection so that all further phases build on a working system.

## Modules introduced

| Module | Service | Purpose |
|---|---|---|
| `db/models.py` | tasks-service | SQLModel ORM models: Goal, Habit, HabitLog, Task, Reminder |
| `db/migrations/` | tasks-service | Alembic migrations for the initial schema |
| `domain/habits.py` | tasks-service | Pure Python: week bounds, completion counting, habit hit checks |
| `domain/goals.py` | tasks-service | Pure Python: goal progress aggregation across habits and tasks |
| `api/` | tasks-service | FastAPI routers: full CRUD for all 5 entities + computed endpoints |
| `tools/tasks_tool.py` | orchestrator | 20 LangGraph tools wrapping the tasks-service REST API |
| `agent/` | orchestrator | LangGraph StateGraph: call_model → call_tools loop with Postgres checkpointer |

## Key design decisions

- Domain layer is pure Python (no ORM), for testability — see ADR 001
- `ConversationState` carries only `messages`; `thread_id` lives in LangGraph config — see ADR 002
- Proactive triggers will format messages directly, not via the agent — see ADR 003
- Overall architecture and stack choices — see ADR 004

## What is NOT included in Phase 1

- Telegram bot handlers (T08) — the lifespan wires up the bot but only with a pong stub
- Proactive trigger endpoints (T09)
- Library and notes services (future phases)
