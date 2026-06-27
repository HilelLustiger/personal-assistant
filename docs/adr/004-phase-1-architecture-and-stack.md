# ADR 004 — Phase 1 system architecture and technology stack

**Date:** 2026-06-27
**Status:** Decided

## Context

Phase 1 of the personal assistant system covers the daily-use core:
task/habit/reminder management via Telegram with proactive check-ins.
Several foundational architectural and technology decisions were made
during planning (Agreement Doc Gates 1–2) that apply across all
Phase 1 components.

## Decisions

### 1. Microservices with a central orchestrator

The system is composed of independent services (tasks-service in Phase 1;
library-service and notes-service in later phases) coordinated by a single
orchestrator. Services never call each other directly — only the orchestrator
is aware of all services and routes requests between them.

**Why:** Each service owns one responsibility implemented with the technology
suited to it. Direct service-to-service calls would create coupling that makes
each service harder to replace or evolve independently.

### 2. Technology stack

| Layer | Choice | Reason |
|---|---|---|
| HTTP framework | FastAPI | Async-native, lightweight, Pydantic integration |
| ORM | SQLModel | Models double as API schemas — no duplication |
| Migrations | Alembic | Industry standard for SQLAlchemy-based stacks |
| Agent framework | LangGraph | Stateful multi-turn conversations natively |
| LLM interface | LiteLLM | Provider-agnostic — swap Groq/Claude/OpenAI by changing one string |
| LLM provider | Groq | Free tier sufficient for personal use |
| Telegram bot | python-telegram-bot v20 | Fully async, maintained |
| HTTP client | httpx | Async-native, used to call tasks-service from orchestrator |

### 3. Nullable timestamps instead of boolean flags

`tasks.completed_at` (nullable datetime) replaces a `completed` boolean.
`reminders.fired_at` (nullable datetime) replaces a `fired` boolean.
Null = not done / not fired; a timestamp = done and records when.

**Why:** Two fields for the same fact will diverge. A timestamp captures
both the state and the time it changed — strictly more information than
a boolean, with no added complexity.

### 4. UUID primary keys

All tables use UUID PKs generated client-side, not integer auto-increment.

**Why:** UUIDs are safe to generate without a DB round-trip, portable
across services, and do not leak row counts.

### 5. FastAPI lifespan + PTB v20 event loop pattern

Uvicorn owns the asyncio event loop. The Telegram Application is
initialized inside FastAPI's lifespan context manager, not via
`application.run_polling()` which blocks the loop.

**Why:** Both FastAPI (via Uvicorn) and python-telegram-bot v20 require
the same asyncio event loop. Running PTB inside the lifespan is the
only supported pattern for sharing one process.

### 6. LangGraph Postgres checkpointer for conversation state

The LangGraph agent uses the Postgres checkpointer (same PostgreSQL
instance as tasks-service) to persist conversation state across messages
and process restarts.

**Why:** The in-memory checkpointer loses all state on restart. A personal
assistant that forgets the conversation after every deploy is unusable.
Reusing the existing Postgres instance avoids adding a new infrastructure
dependency.

### 7. External cron via cron-job.org

Proactive check-ins (morning, EOD, reminder firing) are triggered by
HTTP POST requests from cron-job.org to `/trigger/*` endpoints on the
orchestrator. No internal scheduler runs inside the process.

**Why:** The target hosting (Oracle Cloud Free Tier) is always-on, so
sleep-on-inactivity is not a concern. An external cron is simpler to
configure, observable (cron-job.org has a dashboard), and requires no
additional library in the orchestrator.

## Consequences

- tasks-service and orchestrator are deployed as separate processes
  (separate Docker containers); the orchestrator depends on tasks-service
  being reachable via `TASKS_SERVICE_URL`.
- Adding a new LLM provider requires only a model string change in
  `GROQ_MODEL` env var — no code changes.
- Conversation history is durable but stored in the same Postgres as
  business data — monitor table growth if usage scales.
- `/trigger/*` endpoints must validate `PROACTIVE_SECRET` on every request
  to prevent unauthorized proactive messages.
