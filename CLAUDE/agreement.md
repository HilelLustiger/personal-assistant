# Agreement Doc

## Gate 1 — Architecture & Structure
Status: agreed

### Decisions

**Phase 1 scope**
- Tasks Service + Orchestrator (LangGraph agent + Telegram bot)
- Web App, Notes Service, Library Service are out of scope for Phase 1

**Deployable units (Phase 1)**
- `tasks-service` — data API, owns all Tasks/Habits/Reminders data
- `orchestrator` — LangGraph agent + Telegram bot only; no web app concerns

**Future deployable units (later phases)**
- `library-service` (Phase 2)
- `notes-service` (Phase 3)
- `web-app` (Phase 4) — React frontend, talks directly to service APIs, NOT through the orchestrator

**tasks-service internal structure**
- `api/` — FastAPI routers, one per domain (goals, tasks, habits, reminders)
- `domain/` — calculation logic that sits between HTTP and DB: e.g. "which habits are due tonight?", "is this task overdue?", "what is the completion rate this week?", "what is the progress toward this goal?"
- `db/` — ORM models + schema migrations (library TBD in Gate 2)

**tasks-service constraint**
- Never pushes data. Only responds to queries.
- Proactive check-in data is served by dedicated read endpoints — the orchestrator asks, tasks-service answers.
- No knowledge of the orchestrator, Telegram, or LangGraph.

**orchestrator internal structure**
- `agent/` — LangGraph graph: state schema, nodes, edges
- `tools/` — wraps tasks-service HTTP calls as LangGraph tools (one file per service)
- `telegram/` — Telegram handlers (incoming messages, command handlers, inline button callbacks, message sending)
- `proactive/` — HTTP endpoints for cron-job.org; receives scheduled trigger, queries tasks-service, fires Telegram message

**Data flow — reactive (user sends a message)**
```
User → Telegram
  → orchestrator/telegram/handlers.py   (receives message)
    → orchestrator/agent/graph.py        (LangGraph decides what to do)
      → orchestrator/tools/tasks_tool.py (calls tasks-service REST API)
        → tasks-service/api/             (reads/writes DB)
      ← structured response
    ← agent formats reply
  ← Telegram message sent to user
```

**Data flow — proactive (scheduled trigger)**
```
cron-job.org → orchestrator/proactive/triggers.py   (POST /trigger/morning or /trigger/eod)
  → tasks-service/api/habits                         (GET /habits?active=true&date=<today>)
  → orchestrator/agent/graph.py                      (format check-in message)
  → telegram/sender.py                               (send message, inline buttons for EOD)
```

**Data flow — reminder firing**
```
cron-job.org (every minute) → orchestrator/proactive/triggers.py  (POST /trigger/check-reminders)
  → tasks-service/api/reminders                      (GET /reminders?fired=false&due_by=<now>)
  → orchestrator/agent/graph.py                      (format reminder message — same as morning/EOD)
  → telegram/sender.py                               (send reminder message)
  → tasks-service/api/reminders                      (POST /reminders/{id}/fire for each sent)
```

**Data flow — inline button callback (EOD habit Yes/No)**
```
User taps Yes/No button
  → Telegram sends callback query
    → orchestrator/telegram/buttons.py   (receives callback)
      → orchestrator/agent/graph.py      (dispatched as agent event — LangGraph state updated)
        → orchestrator/tools/tasks_tool.py (POST /habits/{id}/log or no-op)
      ← agent formats confirmation reply
    ← telegram/sender.py                 (send confirmation message)
```

**Top-level directory structure**
```
pro/
├── tasks-service/
│   ├── api/
│   │   ├── goals.py
│   │   ├── tasks.py
│   │   ├── habits.py
│   │   └── reminders.py
│   ├── domain/
│   │   ├── goals.py
│   │   ├── tasks.py
│   │   ├── habits.py
│   │   └── reminders.py
│   ├── db/
│   │   ├── models.py
│   │   └── migrations/
│   └── main.py
├── orchestrator/
│   ├── agent/
│   │   ├── graph.py
│   │   ├── state.py
│   │   └── nodes.py
│   ├── tools/
│   │   └── tasks_tool.py
│   ├── telegram/
│   │   ├── handlers.py     ← incoming messages (imports sender)
│   │   ├── buttons.py      ← inline button callbacks (imports sender)
│   │   └── sender.py       ← owns ALL outbound Telegram calls; used by handlers and proactive
│   ├── proactive/
│   │   └── triggers.py     ← imports telegram/sender.py; never calls Telegram API directly
│   └── main.py
└── docker-compose.yml
```

### Open Questions

None.

## Gate 2 — Technologies
Status: agreed

### Decisions

**Language & Runtime**
- Python 3.11+ for both services

**tasks-service libraries**
- HTTP framework: FastAPI
- ORM: SQLModel (built on SQLAlchemy + Pydantic; models double as API schemas, no duplication)
- Migrations: Alembic
- DB driver: psycopg3 (`psycopg[binary]`)

**orchestrator libraries**
- Agent framework: LangGraph
- LLM interface: LiteLLM
- LLM provider: Groq
- Telegram bot: python-telegram-bot v20 (fully async)
- HTTP client: httpx (async-native, used to call tasks-service)
- Proactive trigger server: FastAPI (lightweight, same stack)

**Telegram bot mode + orchestrator startup architecture**
- Uvicorn owns the asyncio event loop. The Telegram Application runs inside it via FastAPI's `lifespan` context manager — NOT via `application.run_polling()` which blocks the loop.
- `orchestrator/main.py` pattern:
  ```python
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      await telegram_app.initialize()
      await telegram_app.start()
      await telegram_app.updater.start_polling()  # dev only
      yield
      await telegram_app.updater.stop()
      await telegram_app.stop()
      await telegram_app.shutdown()

  app = FastAPI(lifespan=lifespan)
  ```
- Dev: `updater.start_polling()` inside lifespan
- Prod: remove updater, add `/webhook` POST route that calls `application.process_update(update)`
- Reference: python-telegram-bot wiki — "Combining PTB with other async frameworks"

**Data model**

```
goals
  id
  parent_goal_id     (FK → goals, nullable — null = top-level goal)
  name
  description        (nullable)
  status             (enum: active / completed / archived)
  target_date        (nullable)
  created_at

habits
  id
  goal_id            (FK → goals, NOT NULL — every habit belongs to a goal)
  name
  frequency_target   (int)
  frequency_unit     (enum: daily / weekly)
  start_date
  active             (bool — pause without deleting history)
  created_at

habit_logs
  id
  habit_id           (FK → habits)
  completed_at
  note               (nullable text)
  INDEX (habit_id, completed_at)   ← required for completion-rate queries; add in first migration

tasks
  id
  goal_id            (FK → goals, nullable — standalone tasks have no goal)
  title
  due_datetime       (nullable)
  completed_at       (nullable — null = open, timestamp = when completed; replaces completed bool)
  created_at

reminders
  id
  title
  trigger_datetime
  fired_at           (nullable timestamp — null = not yet fired, timestamp = when it was sent)
  created_at
```

**External services & credentials**

tasks-service:
- `DATABASE_URL` — PostgreSQL connection string

orchestrator:
- `TELEGRAM_BOT_TOKEN` — Telegram Bot API
- `TELEGRAM_CHAT_ID` — your personal Telegram chat ID; used by `telegram/sender.py` for all proactive sends
- `GROQ_API_KEY` — Groq via LiteLLM
- `PROACTIVE_SECRET` — shared secret to validate cron-job.org pings
- `DATABASE_URL` — PostgreSQL connection string (also needed by orchestrator for LangGraph Postgres checkpointer)

All in `.env`, loaded by Docker Compose via `env_file`, never committed

**Testing approach**
- pytest for both services
- `tasks-service/domain/` — unit tests, pure Python, no DB
- `tasks-service/api/` — FastAPI TestClient against a real test PostgreSQL DB
- `orchestrator/tools/` — pytest with httpx mock
- Full end-to-end (Telegram → agent → tasks-service) — manual testing only for now

### Open Questions

None.

## Gate 3 — Implementation & Order
Status: agreed

### Decisions

**Build order**

- Step 0  — Environment setup: `docker-compose.yml` with Postgres service, `.env.example` with all keys, `.env` filled in locally. Milestone: `alembic upgrade head` exits 0 with tables in DB.
- Step 1  — `tasks-service/db/` — SQLModel models + first Alembic migration for all five entities. Includes `INDEX (habit_id, completed_at)` on `habit_logs`.
- Step 2  — `tasks-service/domain/` — pure Python logic: habit due-tonight calculation, task overdue check, goal progress aggregate. Unit-tested before any HTTP.
- Step 3  — `tasks-service/api/` — all CRUD + query endpoints (goals, tasks, habits, reminders). Milestone: service runs locally, curl returns data from Postgres.
- Step 3b — Orchestrator startup spike: FastAPI app with lifespan, Telegram Application initialized inside it, bot replies "pong" to any message, `POST /trigger/test` returns 200, LangGraph Postgres checkpointer connects and persists a test state across two calls. Milestone: PTB + FastAPI + LangGraph checkpointer all work in one process. If this fails, resolve before Step 4.
- Step 4  — `orchestrator/tools/tasks_tool.py` — wrap tasks-service endpoints as LangGraph tool definitions using the agreed POST/GET shapes.
- Step 5  — `orchestrator/agent/` — LangGraph graph wiring tools together. LangGraph state persistence (checkpointing) proven here. Milestone: send a message programmatically, agent calls correct tool, response returns.
- Step 6  — `orchestrator/telegram/` — connect agent to Telegram bot. Milestone: "add task: buy milk" via Telegram → task in Postgres.
- Step 7  — `orchestrator/proactive/` — morning + EOD trigger endpoints + `/trigger/check-reminders` (fires due reminders, marks them fired). All tested with curl first, then wired to cron-job.org. `/trigger/check-reminders` runs every minute on cron-job.org.

**Risk-first flag**
- LangGraph state persistence (conversation surviving hours between Telegram messages) must be solved in Step 5 before Telegram is wired in Step 6. Do not skip ahead.

**Interface contracts**

tasks-service REST API (must be stable before Step 4):
```
GET  /goals?status=<active|completed|archived|all>

GET  /tasks?completed=<true|false>&due_by=<date>&due_from=<date>
     — all params optional; omit to get everything
     — example: ?completed=false&due_by=2026-06-23 → open tasks due today or earlier

GET  /habits?active=<true|false>&date=<date>
     — date triggers domain logic server-side: returns habits with computed due status
     — example: ?active=true&date=2026-06-23 → active habits + whether each needs a log today
     — Response: list of habit objects, each with:
         { id, name, goal_id, frequency_target, frequency_unit, start_date, active, created_at,
           needs_log_today: bool,       ← computed by domain/habits.py for the given date
           completions_this_week: int   ← how many times logged in the current week
         }
       When date is omitted: needs_log_today and completions_this_week are absent.

GET  /goals/{id}/progress
     — returns goal + computed progress metrics for habits and tasks under it
     — Response: {
         id, name, description, status, target_date, parent_goal_id, created_at,
         habits: [
           { id, name, frequency_target, frequency_unit,
             completions_this_week: int,
             completion_rate: float   ← completions_this_week / frequency_target, capped at 1.0
           }
         ],
         tasks_completed: int,   ← tasks under this goal where completed_at IS NOT NULL
         tasks_total: int
       }

GET  /reminders?fired=<true|false>&due_by=<datetime>
     — all params optional; omit to get everything
     — example: ?fired=false&due_by=2026-06-23T10:00:00 → unfired reminders due by now

POST /goals
  Request:  { name, description?, status?, target_date?, parent_goal_id? }
  Response: { id, name, description, status, target_date, parent_goal_id, created_at }

POST /habits
  Request:  { name, goal_id, frequency_target, frequency_unit, start_date }
  Response: { id, name, goal_id, frequency_target, frequency_unit, start_date, active, created_at }

POST /reminders
  Request:  { title, trigger_datetime }
  Response: { id, title, trigger_datetime, fired_at, created_at }

POST /tasks
  Request:  { title, due_datetime?, goal_id? }
  Response: { id, title, due_datetime, goal_id, completed_at, created_at }

POST /tasks/{id}/complete
  Request:  (empty body)
  Response: updated task object with completed_at set

POST /habits/{id}/log
  Request:  { note? }
  Response: { id, habit_id, completed_at, note }

POST /reminders/{id}/fire
  Request:  (empty body)
  Response: updated reminder object with fired_at set

PATCH /goals/{id}
  Request:  { name?, description?, status?, target_date?, parent_goal_id? }
  Response: updated goal object

PATCH /habits/{id}
  Request:  { name?, frequency_target?, frequency_unit?, active? }
  Response: updated habit object

PATCH /tasks/{id}
  Request:  { title?, due_datetime?, goal_id? }
  Response: updated task object

PATCH /reminders/{id}
  Request:  { title?, trigger_datetime? }
  Response: updated reminder object

DELETE /goals/{id}       → 204 No Content
DELETE /habits/{id}      → 204 No Content
DELETE /tasks/{id}       → 204 No Content
DELETE /reminders/{id}   → 204 No Content
```

Proactive trigger contract (cron-job.org → orchestrator):
```
POST /trigger/morning           { "secret": "..." }   — once daily
POST /trigger/eod               { "secret": "..." }   — once daily
POST /trigger/check-reminders   { "secret": "..." }   — every minute
```

### Open Questions

None.

---

## Challenge Report (Round 1 — resolved, kept for history)

### Gate 1 — Architecture & Structure

#### Issues Found

**1. `goals` is a first-class entity in the data model but absent from the directory structure.**
The data model defines `goals` with its own table, a self-referential FK, and status logic. The domain layer explicitly calls out "goal progress aggregate" as one of its responsibilities. But `api/` lists only `tasks.py`, `habits.py`, `reminders.py` — no `goals.py`. Same for `domain/`. If the manager builds from this file tree, nobody writes the goals layer. This is a structural gap, not a detail.

**2. Telegram-sending responsibility is split between two modules with no owner.**
`orchestrator/telegram/` sends replies to user messages. `orchestrator/proactive/` also sends Telegram messages (check-ins, habit buttons). There is no shared Telegram-sending component. This will cause duplication: formatting, error handling, and rate-limiting logic written twice in different styles with different failure modes. Who owns "send a message to Telegram"?

**3. No answer to: where does the orchestrator get the user's Telegram chat ID for proactive messages?**
Proactive messages are initiated by the orchestrator — no inbound Telegram event triggers them. The orchestrator needs to know *where* to send. This is a single-user system, so the answer is probably a `TELEGRAM_CHAT_ID` env var — but it is not mentioned anywhere in the architecture. If it is missing from the credentials list and the directory structure, it will be discovered at Step 7 and require backtracking.

#### Open Questions Added

- Where does `goals` live in `api/` and `domain/`? Add `goals.py` to both, or explain why goals are served differently.
- Who owns the Telegram message-sending abstraction — and where does it live in the directory structure?
- Where is `TELEGRAM_CHAT_ID` stored and loaded? Add it to the credentials section if it is an env var.

---

### Gate 2 — Technologies

#### Issues Found

**1. `tasks.completed` (bool) and `tasks.completed_at` (nullable timestamp) represent the same state with two fields.**
`completed = true` and `completed_at IS NOT NULL` are equivalent. Two fields for the same fact will get out of sync — a task marked complete via `completed = true` but with `completed_at = null` produces inconsistent query results depending on which field the domain logic checks. One field is enough: use `completed_at` as nullable; null means not done, a timestamp means done and records when.

**2. Running python-telegram-bot v20 and FastAPI in the same process is not "a one-line switch" — it is an unsolved integration problem.**
Both frameworks want to own the asyncio event loop. `application.run_polling()` and `application.run_webhook()` block the event loop. FastAPI's Uvicorn also owns the event loop. Running both requires manually initializing the `Application`, adding it as an asyncio background task, and wiring the Telegram webhook handler into FastAPI's router — or running them as separate processes. The plan states "one-line switch" without addressing this. If this is not resolved before Step 6, the entire orchestrator startup will need to be redesigned.

**3. `habit_logs` will be queried by date range on every check-in, but no index is specified.**
The domain query "how many times did I complete this habit this week?" scans `habit_logs` filtered by `habit_id` and `completed_at` range. Without an index on `(habit_id, completed_at)`, this is a full table scan that grows unbounded as logs accumulate. This needs to be addressed at schema definition time (Step 1), not after data exists.

#### Open Questions Added

- Drop `tasks.completed` and use `completed_at IS NOT NULL` as the completion check — or explicitly explain why both fields are needed.
- How do python-telegram-bot v20 and FastAPI share the asyncio event loop? Define the startup architecture before Step 5.
- Add `INDEX (habit_id, completed_at)` on `habit_logs` to the schema.

---

### Gate 3 — Implementation & Order

#### Issues Found

**1. POST request/response shapes are undefined — but Step 4 (tool definitions) depends on them.**
The interface contract defines GET endpoints with query parameters, but `POST /tasks`, `POST /habits/{id}/log`, and `POST /tasks/{id}/complete` have no defined request bodies or response shapes. The tool definitions in Step 4 need to know exactly what fields to send and what to expect back. "Obvious from the models" is not a contract — it is an assumption that will cause rework when the tool schema and the API implementation diverge.

**2. No environment setup step before Step 1.**
Step 1 assumes a running local Postgres instance, a configured `.env` file, and a working Docker Compose setup. None of this is a task in the build order. Alembic cannot run without a live DB and a valid `DATABASE_URL`. This will block Step 1 until resolved.

**3. The riskiest unknown — python-telegram-bot + FastAPI event loop coexistence — is not addressed until Step 5–6, after three steps of tasks-service work.**
If the orchestrator startup architecture requires two separate processes instead of one, the `orchestrator/main.py` design, the Docker Compose service definition, and the proactive trigger design all change. This should be spiked before Step 4, not discovered at Step 6.

#### Open Questions Added

- Add a Step 0: environment setup — Docker Compose with Postgres, `.env` configured, `alembic upgrade head` succeeds.
- Add POST request/response body definitions to the interface contracts before Step 4 begins.
- Add a spike task between Steps 3 and 4: prove python-telegram-bot v20 and FastAPI can share one process. If they cannot, the orchestrator becomes two processes and the build order changes.

---

### Verdict

**REVISE** — four critical issues must be resolved before the manager can assign tasks:

1. `goals` missing from `api/` and `domain/` in the directory structure
2. `tasks.completed` + `tasks.completed_at` redundancy — data integrity risk
3. Telegram chat ID for proactive messages unaddressed
4. FastAPI + python-telegram-bot event loop coexistence unsolved and on the critical path

Return to architect.

---

## Challenge Report (Round 2 — resolved, kept for history)

### Gate 1 — Architecture & Structure

#### Issues Found

**1. No component owns the reminder firing mechanism.**
`reminders` is a first-class entity in the data model with `trigger_datetime` and `fired` fields. But no component in the architecture is responsible for watching reminders and firing them. The proactive flow handles morning and EOD (two fixed times), but reminders fire at arbitrary times — "wife's birthday on July 14th at 9am" has nothing to trigger it. Without a firing mechanism, reminders are dead data: they can be created but never sent. This is a missing component, not an implementation detail.

#### Open Questions Added

- What component fires reminders at their `trigger_datetime`? Three options: (A) cron-job.org pings `/trigger/check-reminders` every minute and the orchestrator queries for due reminders; (B) an internal polling loop inside the orchestrator; (C) a separate scheduled job. Which approach, and where does it live in the architecture?

---

### Gate 2 — Technologies

#### Issues Found

**1. LangGraph checkpointer backend is unspecified — the default will silently break conversation persistence.**
LangGraph requires a checkpointer to persist conversation state across messages. The default (in-memory) checkpointer loses all state when the orchestrator process restarts. For a server that may restart (deploys, crashes, Oracle Cloud maintenance), this means every restart wipes conversation history and the agent loses context mid-conversation. The right choice for this stack is the LangGraph Postgres checkpointer — it reuses the existing PostgreSQL instance — but this has not been decided. If it is the Postgres checkpointer, the orchestrator needs `DATABASE_URL` in its own environment, which is not currently in its credential list.

#### Open Questions Added

- Which LangGraph checkpointer backend? If Postgres: add `DATABASE_URL` to the orchestrator's credentials and address it in Step 3b (the startup spike), since it must be proven before Step 5.

---

### Gate 3 — Implementation & Order

#### Issues Found

**1. The interface contracts have no UPDATE or DELETE operations — the tool layer will be unable to edit or remove anything.**
The contracts define GET (read) and POST (create + actions). But `PATCH /tasks/{id}` (change due date, edit title), `DELETE /tasks/{id}`, `PATCH /habits/{id}` (rename, change frequency, deactivate), and `DELETE /goals/{id}` are absent. The LangGraph tools are built from these contracts in Step 4. If "update task due date" and "delete habit" are not in the contracts, they will not be in the tools, and the agent will be unable to perform these operations when the user asks — which they will.

**2. No step for the reminder firing mechanism.**
The build order goes through Step 7 (proactive triggers) without any step for reminder firing. Even if the mechanism is decided (see Gate 1 issue), it has no place in the build order. It will either be forgotten or bolted on after Step 7 as an afterthought.

#### Open Questions Added

- Add PATCH and DELETE to the interface contracts for at minimum tasks, habits, and goals.
- Add a build step for the reminder firing mechanism once its architecture is decided.

---

### Verdict

**REVISE** — three issues to resolve before handoff to manager:

1. No component fires reminders — architectural hole, not an implementation detail
2. LangGraph checkpointer backend unspecified — default silently breaks conversation persistence on restart
3. No UPDATE/DELETE in interface contracts — tools layer will be read-and-create only

Return to architect.

---

## Challenge Report (Round 3 — resolved, kept for history)

### Gate 1 — Architecture & Structure

#### Issues Found

**1. The reminder firing flow bypasses the agent — inconsistent with morning/EOD and undocumented.**
The morning/EOD proactive flow passes through `orchestrator/agent/graph.py` to format the check-in message. The reminder firing flow goes directly from `proactive/triggers.py` → `sender.py`, bypassing the agent entirely. This may be intentional (reminders are simple verbatim notifications, not AI-formatted), but it is not stated. A coder seeing two different patterns in `proactive/` without explanation will be confused about which pattern to follow.

#### Open Questions Added

- Is bypassing the agent for reminders intentional? If reminders are always sent verbatim (just the `title` field), state this explicitly. If they should be conversational, they need to go through the agent.

---

### Gate 2 — Technologies

#### Issues Found

**1. `reminders.fired` (bool) and `reminders.fired_at` (nullable timestamp) is the same redundancy that was fixed for `tasks.completed`.**
Round 1 removed `tasks.completed` because `completed_at IS NOT NULL` already captures the boolean — two fields for the same fact will diverge. `reminders` now has the identical problem: `fired = true` ↔ `fired_at IS NOT NULL`. Drop `fired` and use `fired_at IS NOT NULL` as the single source of truth, consistent with how `tasks` handles completion.

#### Open Questions Added

- Drop `reminders.fired` and use `fired_at IS NOT NULL` as the fired check.

---

### Gate 3 — Implementation & Order

#### Issues Found

**1. `GET /reminders` query contract is missing — but the reminder firing flow depends on it.**
The reminder firing flow calls `GET /reminders?fired=false&due_by=<now>` in the data flow diagram, but this endpoint's query parameter contract is not listed in the interface contracts section. The coder building Step 3 (tasks-service API) and the coder building Step 7 (reminder firing) have no shared spec for this endpoint.

#### Open Questions Added

- Add `GET /reminders?fired=<true|false>&due_by=<datetime>` to the interface contracts.

---

### Verdict

**REVISE** — two concrete gaps plus one open question:

1. `reminders.fired` bool is redundant with `fired_at` — same issue as `tasks.completed`, same fix
2. `GET /reminders` query contract missing from interface contracts
3. (Open question) Is bypassing the agent for reminders intentional? Needs to be stated explicitly.

Return to architect.

---

## Challenge Report (Round 4 — resolved, kept for history)

### Gate 1 — Architecture & Structure

#### Issues Found

**1. `buttons.py` has no defined path to tasks-service — the inline button callback flow is architecturally incomplete.**
The EOD check-in sends Yes/No inline buttons. When the user taps "Yes", Telegram sends a callback query handled by `orchestrator/telegram/buttons.py`. That handler must log the habit completion — but `buttons.py` is only described as importing `sender.py`. It has no defined path to tasks-service: it could call tasks-service directly (via httpx), call through the tools layer, or dispatch through the LangGraph agent. These three options have meaningfully different consequences: a direct httpx call bypasses the agent and LangGraph state does not reflect the check-in was resolved; routing through the agent keeps state consistent but adds complexity. The architecture says nothing about which path button callbacks take.

#### Open Questions Added

- When a Yes/No button callback arrives in `buttons.py`, does it dispatch through `agent/graph.py` (LangGraph state reflects the completed check-in), or does it call tasks-service directly? Choose one and document the data flow.

---

### Gate 2 — Technologies

#### Issues Found

**1. `POST /reminders` response still references `fired` — a field removed from the schema in Round 3.**
The interface contract shows `Response: { id, title, trigger_datetime, fired, created_at }` but `reminders.fired` was dropped in favour of `fired_at`. The coder building Step 3 will add a `fired` field that does not exist in the model, and the coder building Step 4 will expect it in the tool response.

#### Open Questions Added

- Fix `POST /reminders` response to `{ id, title, trigger_datetime, fired_at, created_at }` — `fired_at` is null on creation.

---

### Gate 3 — Implementation & Order

#### Issues Found

None.

---

### Verdict

**REVISE** — two issues to close:

1. Inline button callback path in `buttons.py` undefined — a data flow gap that will force an unplanned design decision mid-build
2. `POST /reminders` response still references the removed `fired` field

Return to architect.

---

## Challenge Report (Round 5 — resolved, kept for history)

### Gate 3 — Issues Found (now resolved)

1. `GET /habits?date=<date>` response shape was undefined → fixed: `needs_log_today` and `completions_this_week` added
2. Goal progress had no access path → fixed: `GET /goals/{id}/progress` endpoint added

---

## Challenge Report (Round 6)

### Gate 1 — Architecture & Structure

#### Issues Found

None.

#### Open Questions Added

None.

---

### Gate 2 — Technologies

#### Issues Found

None.

#### Open Questions Added

None.

---

### Gate 3 — Implementation & Order

#### Issues Found

None. Build order is risk-ordered, all milestones are testable, interface contracts are complete for all endpoints the tools layer depends on. The `GET /goals/{id}/progress` endpoint and the `GET /habits?date=<date>` computed response shape are both now defined. No gaps remain.

#### Open Questions Added

None.

---

### Verdict

**PASS** — no critical issues found. All five rounds of revisions have been addressed. The Agreement Doc is complete and consistent across all three gates.

Ready for manager.
