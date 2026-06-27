# Module Specs
# Created by: code-designer
# Read by: sequencer, coder, reviewer

date: "2026-06-27"
status: complete

---

## Module 1 — `tasks-service/db`

**Purpose:** Own all SQLModel table definitions and provide the single database session dependency used by every API router.

### Public Interface

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `Goal` | (SQLModel table) | — | ORM model for goals |
| `Habit` | (SQLModel table) | — | ORM model for habits |
| `HabitLog` | (SQLModel table) | — | ORM model for habit completion entries |
| `Task` | (SQLModel table) | — | ORM model for tasks |
| `Reminder` | (SQLModel table) | — | ORM model for reminders |
| `get_session()` | — | `Generator[Session, None, None]` | FastAPI dependency; yields one DB session per request |
| `engine` | — | `Engine` | SQLAlchemy engine; used by Alembic and test setup |

### Internal Logic
1. Models defined with `SQLModel, table=True`; all PKs are UUIDs generated client-side
2. `completed_at` / `fired_at` are nullable timestamps — null means not done/not fired; no separate boolean field
3. `engine` created once at module import from `DATABASE_URL` env var
4. `get_session()` opens a `Session` context, yields it, and closes on exit
5. Migration managed by Alembic; composite index `(habit_id, completed_at)` on `habit_logs` applied in first migration

### State / Storage
Owns the schema for all five tables. Writes nothing at runtime — only defines structure.

### Dependencies
None (leaf module).

### Constraints
- UUIDs as PKs, not integers
- No `completed` bool on tasks, no `fired` bool on reminders
- `DATABASE_URL` must be set before import (session.py reads it at module load)
- `default_factory` for datetime fields must use `lambda: datetime.now(timezone.utc).replace(tzinfo=None)` — not `datetime.utcnow` (deprecated)

### Test Spec

**Behaviors to test:**

`get_session()`
- Yields a valid `Session` object when `DATABASE_URL` is set and Postgres is reachable
- Session is closed after the request completes (no connection leak)

`Goal` model
- Instantiates with required field `name` only; `status` defaults to `active`, `parent_goal_id` defaults to `None`
- Persists and reads back a `Goal` with a `parent_goal_id` pointing to another goal (self-referential FK)

`Habit` model
- Instantiates with all required fields; `active` defaults to `True`
- Rejects insert when `goal_id` references a non-existent goal (FK constraint)

`HabitLog` model
- Composite index `(habit_id, completed_at)` exists in the database after migration
- Rejects insert when `habit_id` references a non-existent habit (FK constraint)

`Task` model
- `completed_at` is `None` on creation; `goal_id` is optional (nullable FK)

`Reminder` model
- `fired_at` is `None` on creation

**Edge cases:**
- Two `Goal` rows can share the same `name` (no unique constraint)
- `Habit.frequency_target` accepts any positive integer — no DB-level minimum enforced
- `HabitLog` with a `note` of `None` persists cleanly

**What is NOT tested here:**
- Business logic — belongs to `domain/`
- HTTP request/response shapes — belongs to `api/`
- Migration rollback — verified manually via `alembic downgrade base`

---

## Module 2 — `tasks-service/domain`

**Purpose:** Provide all business logic as pure Python functions — no HTTP, no DB sessions, no side effects. The API layer loads data; this layer computes derived values from it.

### Public Interface

*`domain/habits.py`*

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `find_week_bounds(day)` | `day: date` | `tuple[datetime, datetime]` | Returns `(sunday_00:00, saturday_23:59:59)` for the week containing `day` |
| `count_completions_in_range(habit_id, logs, start, end)` | `habit_id: UUID`, `logs: list`, `start: datetime`, `end: datetime` | `int` | Count of log entries for this habit within the datetime range |
| `is_habit_hit_in_range(habit, logs, start, end)` | `habit`, `logs: list`, `start: datetime`, `end: datetime` | `bool` | True if `count_completions_in_range < habit.frequency_target` — habit still needs a log |

*`domain/tasks.py`*

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `is_overdue(task, now)` | `task`, `now: datetime` | `bool` | True if `due_datetime` is set, task is not completed, and `due_datetime < now` |

*`domain/goals.py`*

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `get_goal_progress(goal, habits_with_logs, tasks, start, end)` | `goal`, `habits_with_logs: list[tuple]`, `tasks: list`, `start: datetime`, `end: datetime` | `dict` | Returns `{habits: [{id, completion_rate, completions_in_range}], tasks_completed, tasks_total}` |

*`domain/reminders.py`*

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `is_due(reminder, now)` | `reminder`, `now: datetime` | `bool` | True if `fired_at` is None and `trigger_datetime <= now` |

### Internal Logic
1. `find_week_bounds` anchors the week to Sunday; API layer calls it once and passes `start`/`end` to all domain functions in the same request
2. `count_completions_in_range` filters the pre-loaded log list by `habit_id` and datetime range; strips `tzinfo` before comparison to handle naive/aware mismatch
3. `is_habit_hit_in_range` delegates to `count_completions_in_range` and compares against `habit.frequency_target`
4. `get_goal_progress` delegates to `count_completions_in_range` per habit; caps `completion_rate` at `1.0`
5. `is_overdue` and `is_due` normalise timezone before comparing datetimes

### State / Storage
None — reads only from the objects passed in, writes nothing.

### Dependencies
`domain/goals.py` imports `count_completions_in_range` from `domain/habits.py`. No other cross-domain imports.

### Constraints
- No imports from `api/` or `db/`
- All functions deterministic given the same inputs
- Filtering stays in Python, not SQL — see ADR 001

### Test Spec

**Behaviors to test:**

`find_week_bounds(day)`
- Given a Wednesday → returns the preceding Sunday at 00:00:00 and the following Saturday at 23:59:59
- Given a Sunday → returns that same Sunday as the start
- Given a Saturday → returns the preceding Sunday as start, that same Saturday as end

`count_completions_in_range(habit_id, logs, start, end)`
- 3 logs within range and 2 outside → returns 3
- Logs for a different `habit_id` within range → returns 0
- Log exactly on `start` → counted (inclusive)
- Log exactly on `end` → counted (inclusive)
- Empty logs list → returns 0

`is_habit_hit_in_range(habit, logs, start, end)`
- `frequency_target=3`, 2 completions → returns `True` (needs a log)
- `frequency_target=3`, 3 completions → returns `False` (hit)
- `frequency_target=3`, 4 completions → returns `False` (exceeded)

`is_overdue(task, now)`
- `due_datetime` in past, `completed_at=None` → `True`
- `due_datetime` in past, `completed_at` set → `False`
- `due_datetime` in future → `False`
- `due_datetime=None` → `False`

`get_goal_progress(goal, habits_with_logs, tasks, start, end)`
- `completion_rate` capped at `1.0` when completions exceed `frequency_target`
- `tasks_completed` counts only tasks with `completed_at` set
- `tasks_total` counts all tasks
- No habits, no tasks → `{habits: [], tasks_completed: 0, tasks_total: 0}`

`is_due(reminder, now)`
- `trigger_datetime` in past, `fired_at=None` → `True`
- `trigger_datetime` in past, `fired_at` set → `False`
- `trigger_datetime` in future → `False`
- `trigger_datetime` exactly equal to `now` → `True` (inclusive)

**Edge cases:**
- All datetime functions handle timezone-naive vs. timezone-aware mismatch without raising
- `count_completions_in_range` with logs from multiple habits → filters correctly by `habit_id`

**What is NOT tested here:**
- DB queries — belongs to `api/`
- HTTP shapes — belongs to `api/`
- Correct week bounds passed in — caller's responsibility

---

## Module 3 — `tasks-service/api`

**Purpose:** Expose all tasks-service data operations as an HTTP REST API. Routers handle request/response translation, delegate business logic to `domain/`, and delegate all DB access to `db/session`.

### Public Interface

*Goals*

| Endpoint | Input | Returns | Notes |
|---|---|---|---|
| `GET /goals` | `?status=active\|completed\|archived\|all` | `list[Goal]` | Omit → return all |
| `POST /goals` | `GoalCreate` body | `Goal` (201) | |
| `PATCH /goals/{goal_id}` | `GoalUpdate` body | `Goal` | Partial update |
| `DELETE /goals/{goal_id}` | — | 204 | Cascade behavior pending design decision — see status.md |
| `GET /goals/{goal_id}/progress` | — | progress dict | Calls `get_goal_progress` from domain |

*Habits*

| Endpoint | Input | Returns | Notes |
|---|---|---|---|
| `GET /habits` | `?active=bool&date=YYYY-MM-DD` | `list[Habit\|dict]` | With `date`: adds `needs_log_today`, `completions_this_week` |
| `POST /habits` | `HabitCreate` body | `Habit` (201) | |
| `PATCH /habits/{habit_id}` | `HabitUpdate` body | `Habit` | |
| `DELETE /habits/{habit_id}` | — | 204 | Cascades habit_logs |
| `POST /habits/{habit_id}/log` | `HabitLogCreate` body | `HabitLog` (201) | Sets `completed_at` to now |

*Tasks*

| Endpoint | Input | Returns | Notes |
|---|---|---|---|
| `GET /tasks` | `?completed=bool&due_by=date&due_from=date` | `list[Task]` | All params optional |
| `POST /tasks` | `TaskCreate` body | `Task` (201) | |
| `PATCH /tasks/{task_id}` | `TaskUpdate` body | `Task` | |
| `DELETE /tasks/{task_id}` | — | 204 | |
| `POST /tasks/{task_id}/complete` | — | `Task` | Sets `completed_at` to now |

*Reminders*

| Endpoint | Input | Returns | Notes |
|---|---|---|---|
| `GET /reminders` | `?fired=bool&due_by=datetime` | `list[Reminder]` | |
| `POST /reminders` | `ReminderCreate` body | `Reminder` (201) | |
| `PATCH /reminders/{reminder_id}` | `ReminderUpdate` body | `Reminder` | |
| `DELETE /reminders/{reminder_id}` | — | 204 | |
| `POST /reminders/{reminder_id}/fire` | — | `Reminder` | Sets `fired_at` to now |

### Internal Logic
1. Every router uses `get_session()` as a FastAPI dependency
2. All 404s raised as `HTTPException(status_code=404)`
3. `GET /habits?date=` calls `find_week_bounds`, loads logs, calls `is_habit_hit_in_range` and `count_completions_in_range` per habit
4. `GET /goals/{id}/progress` calls `get_goal_progress` after loading habits, logs, and tasks
5. `DELETE /goals/{id}` cascades in FK-safe order: habit_logs → habits → tasks → goal

### State / Storage
Reads and writes all five tables via the session dependency.

### Dependencies
`db/models`, `db/session`, `domain/habits`, `domain/goals`.

### Constraints
- No business logic in routers — computed fields always delegated to `domain/`
- No knowledge of the orchestrator, Telegram, or LangGraph
- Schema classes named `<Entity>Create` and `<Entity>Update`

### Test Spec

**Behaviors to test:**

Goals
- `GET /goals` no params → all goals
- `GET /goals?status=active` → active only
- `POST /goals` with `name` only → `status` defaults to `active`
- `POST /goals` with `parent_goal_id` → persists FK reference
- `PATCH /goals/{id}` partial → only named field changes
- `PATCH /goals/{id}` unknown id → 404
- `DELETE /goals/{id}` → 204
- `GET /goals/{id}/progress` → correct shape with `completion_rate`, `tasks_completed`, `tasks_total`
- `GET /goals/{id}/progress` no habits or tasks → `{habits: [], tasks_completed: 0, tasks_total: 0}`

Habits
- `GET /habits?active=true` → active only
- `GET /habits?date=YYYY-MM-DD` → includes `needs_log_today` and `completions_this_week`
- `GET /habits` no date → no computed fields
- `PATCH /habits/{id}` with `active=false` → pauses without deleting logs
- `DELETE /habits/{id}` → 204, all `HabitLog` rows deleted
- `POST /habits/{id}/log` → `HabitLog` with `completed_at` set to now
- `POST /habits/{id}/log` unknown id → 404

Tasks
- `GET /tasks?completed=false` → open tasks only
- `GET /tasks?completed=true` → completed only
- `GET /tasks?due_by=YYYY-MM-DD` → tasks due on or before end of that day
- `GET /tasks?due_from=YYYY-MM-DD` → tasks due on or after that day
- `POST /tasks` title only → `due_datetime` and `goal_id` null
- `POST /tasks/{id}/complete` → `completed_at` set, not null
- `POST /tasks/{id}/complete` twice → idempotent, second call succeeds
- `DELETE /tasks/{id}` → 204

Reminders
- `GET /reminders?fired=false` → unfired only
- `GET /reminders?fired=false&due_by=<now>` → unfired due by now (proactive query)
- `POST /reminders` → `fired_at=null`
- `POST /reminders/{id}/fire` → `fired_at` set
- `DELETE /reminders/{id}` → 204

**Edge cases:**
- `GET /tasks?due_by=` with tasks having `due_datetime=null` → excluded
- `PATCH` with empty body `{}` → 200, no changes
- `DELETE /goals/{id}` with no children → succeeds cleanly

**What is NOT tested here:**
- Domain logic correctness — belongs to `domain/` tests
- Goal deletion with sub-goals or bound tasks — design decision pending
- Pagination — not implemented

---

## Module 4 — `orchestrator/tools`

**Purpose:** Wrap every tasks-service REST endpoint as a LangGraph tool so the agent can call them by name. Thin, typed HTTP wrappers with docstrings the LLM reads to decide which tool to call.

### Public Interface

20 tools exported via `tools/__init__.ALL_TOOLS`. See agreement.md Gate 3 for full endpoint mapping. Groups: goals (5), tasks (5), habits (5), reminders (5).

### Internal Logic
1. Each tool opens an `httpx.AsyncClient`, makes one HTTP call, raises on non-2xx, returns parsed JSON
2. Optional parameters excluded from payload when `None`
3. `TASKS_SERVICE_URL` read from env at module import
4. Every tool has a mandatory docstring written for the LLM

### State / Storage
None.

### Dependencies
`httpx`, `langchain_core.tools.tool`. No imports from `agent/`.

### Constraints
- Must not import from `agent/` — circular dependency risk
- `tools/__init__.py` owns the `ALL_TOOLS` export; `nodes.py` imports from the package — see ADR 002
- Tool docstrings mandatory per conventions.md
- `frequency_unit` values must be `'daily'`/`'weekly'` — not `'day'`/`'week'`

### Test Spec

**Behaviors to test:**

For each of the 20 tools:
- All tools importable as LangGraph tools (`isinstance(tool, BaseTool)`)
- All tools have a non-empty docstring

Per tool group (representative cases):
- `create_task(title="buy milk")` → `POST /tasks` called with `{"title": "buy milk"}`
- `list_tasks(completed=False)` → `GET /tasks?completed=false`
- `list_habits(date="2026-06-27")` → response includes `needs_log_today` field
- `get_goal_progress(goal_id="...")` → response includes `completion_rate` per habit
- `complete_task(task_id="...")` → `POST /tasks/{id}/complete` called
- `log_habit(habit_id="...", note=None)` → request body omits `note` key entirely
- `fire_reminder(reminder_id="...")` → `POST /reminders/{id}/fire` called
- `delete_goal(goal_id="...")` → `DELETE /goals/{id}` called, returns `{"deleted": True}`

**Edge cases:**
- Optional params passed as `None` → excluded from request payload (not sent as `null`)
- tasks-service returns 404 → tool raises `httpx.HTTPStatusError`

**What is NOT tested here:**
- tasks-service business logic — belongs to `api/` tests
- LLM tool selection — belongs to `agent/` tests

---

## Module 5 — `orchestrator/agent`

**Purpose:** Implement the LangGraph conversational agent — the stateful reasoning loop that receives user messages, decides which tools to call, executes them, and produces a reply. Conversation state persists across messages via the Postgres checkpointer.

### Public Interface

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `build_graph(checkpointer?)` | `checkpointer: BaseCheckpointSaver \| None` | compiled `StateGraph` | Constructs and compiles the graph; no checkpointer = no persistence (tests only) |
| `ConversationState` | — | `TypedDict` | `messages: Annotated[list[BaseMessage], add_messages]` — single field |
| `call_model(state)` | `state: ConversationState` | `dict` | Calls LiteLLM with full history + tool schemas; returns new `AIMessage` |
| `call_tools(state)` | `state: ConversationState` | `dict` | Executes tool calls from last `AIMessage` sequentially; returns `ToolMessage` per call |

### Internal Logic
1. Entry point is `call_model`; router checks for tool calls after each model response
2. Tool calls present → `call_tools` → back to `call_model` (ReAct loop)
3. No tool calls → graph ends; caller reads `result["messages"][-1].content`
4. `call_model` converts LangGraph messages to LiteLLM dict format; includes fixed system prompt
5. `call_tools` executes sequentially; unknown tool names return error string, not exception
6. Tool schemas resolved at import time from `tools.ALL_TOOLS`

### State / Storage
`messages` accumulates full conversation history via `add_messages` reducer. Persisted to Postgres via checkpointer keyed by `config["configurable"]["thread_id"]`.

### Dependencies
`tools.ALL_TOOLS`, `litellm`, `langchain_core.messages`.

### Constraints
- LiteLLM + Groq; model swappable via `GROQ_MODEL` env var
- `MemorySaver` only in tests — Postgres checkpointer in production
- No `reply` field in state — callers read `result["messages"][-1].content` (ADR 002)
- No `thread_id` in state — read from LangGraph config (ADR 002)
- Tool calls execute sequentially (ADR 002)

### Test Spec

**Behaviors to test:**

`build_graph`
- No checkpointer → compiles without error
- With `MemorySaver` → state persists across two invocations on same `thread_id`

Graph flow — no tool calls
- Model returns plain text → graph ends, reply in `result["messages"][-1].content`

Graph flow — one tool call
- Model returns tool call → tool executed → model called again with result → plain text reply

Graph flow — ReAct loop
- Two sequential tool calls across two model turns → both resolved, plain text reply at end

`call_model`
- System prompt included as first message in every LiteLLM call
- All prior messages (human, AI, tool) included in correct role order
- Tool schemas from `ALL_TOOLS` included in every call

`call_tools`
- Valid tool name → tool invoked, result as `ToolMessage`
- Unknown tool name → `ToolMessage` with error string, no exception
- Multiple tool calls in one `AIMessage` → one `ToolMessage` per call

State persistence
- Second `ainvoke` on same `thread_id` receives full history from first call
- Prior `AIMessage` appears in messages sent to LiteLLM on second turn

**Edge cases:**
- Tool raises exception during execution → error string in `ToolMessage`, graph continues
- Empty `messages` → `call_model` sends only system prompt

**What is NOT tested here:**
- Actual Groq API — mocked
- tasks-service HTTP — mocked via `respx`
- Postgres checkpointer across process restarts — manual verification
- Telegram integration — belongs to `bot/` tests

---

## Module 6 — `orchestrator/bot`

**Purpose:** Connect the LangGraph agent to Telegram. Owns all inbound message handling and all outbound Telegram calls. Nothing sends to Telegram except `sender.py`.

### Public Interface

*`bot/sender.py`*

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `send_message(chat_id, text)` | `chat_id: str`, `text: str` | `None` | Send plain text to a Telegram chat |
| `send_message_with_buttons(chat_id, text, buttons)` | `chat_id: str`, `text: str`, `buttons: list[list[InlineKeyboardButton]]` | `None` | Send message with inline keyboard |

*`bot/handlers.py`*

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `handle_message(update, context)` | `update: Update`, `context: ContextTypes` | `None` | Handles incoming text messages — passes to agent, sends reply via sender |
| `register_handlers(application)` | `application: Application` | `None` | Registers all handlers with the Telegram Application |

*`bot/buttons.py`*

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `handle_button_callback(update, context)` | `update: Update`, `context: ContextTypes` | `None` | Handles inline button callbacks — dispatches to agent, sends confirmation via sender |

### Internal Logic

`handlers.py`:
1. Extracts text and `chat_id` from `Update`
2. Retrieves `agent_graph` from `context.bot_data["agent_graph"]`
3. Invokes graph with `thread_id=str(chat_id)`
4. Sends `result["messages"][-1].content` via `sender.send_message`

`buttons.py`:
1. Parses `callback_data` — format: `habit_log:<habit_id>:yes` or `habit_log:<habit_id>:no`
2. Answers callback query immediately (clears Telegram loading spinner)
3. `yes` → dispatches synthetic `HumanMessage` to agent to log habit
4. `no` → sends plain acknowledgement, no agent call
5. Sends confirmation via `sender.send_message`

### State / Storage
None. Reads `agent_graph` from `context.bot_data`.

### Dependencies
`agent/graph` (via `context.bot_data`), `bot/sender.py`, `python-telegram-bot`.

### Constraints
- `handlers.py` and `buttons.py` never call Telegram API directly — only via `sender.py`
- Thread ID = `str(chat_id)`
- `agent_graph` injected via `context.bot_data["agent_graph"]` set in `main.py` lifespan

### Test Spec

**Behaviors to test:**

`sender.send_message`
- Calls `bot.send_message` with correct `chat_id` and `text`

`sender.send_message_with_buttons`
- Calls `bot.send_message` with an `InlineKeyboardMarkup` reply markup

`handle_message`
- Incoming text message → agent invoked with `HumanMessage(text)` and `thread_id=str(chat_id)`
- Agent reply sent via `sender.send_message` to the correct `chat_id`
- Agent not called if message is empty

`handle_button_callback` — Yes tap
- `callback_data=habit_log:<habit_id>:yes` → callback query answered → agent invoked with synthetic message → confirmation sent via sender
- `POST /habits/{habit_id}/log` called (via agent tool)

`handle_button_callback` — No tap
- `callback_data=habit_log:<habit_id>:no` → callback query answered → plain acknowledgement sent, no agent call

**Edge cases:**
- Malformed `callback_data` (missing parts) → callback answered, error message sent, no crash
- Agent raises exception during `handle_message` → error message sent to user via sender, no unhandled exception

**What is NOT tested here:**
- Actual Telegram API delivery — bot mocked
- Actual Groq API — mocked
- tasks-service HTTP — mocked via `respx`
- Handler registration with the Application — verified via startup test in `test_spike.py`

---

## Module 7 — `orchestrator/proactive`

**Purpose:** Receive scheduled HTTP triggers from cron-job.org, fetch data from tasks-service, format and send proactive Telegram messages. The only module that initiates contact with the user.

### Public Interface

| Endpoint | Method | Body | Returns | Description |
|---|---|---|---|---|
| `/trigger/morning` | `POST` | `{"secret": "..."}` | 200 / 401 | Fetches open tasks, sends morning summary |
| `/trigger/eod` | `POST` | `{"secret": "..."}` | 200 / 401 | Fetches active habits, sends EOD check-in with Yes/No buttons |
| `/trigger/check-reminders` | `POST` | `{"secret": "..."}` | 200 / 401 | Fetches due reminders, sends each, marks fired |

### Internal Logic

`/trigger/morning`:
1. Validate `PROACTIVE_SECRET` → 401 on mismatch
2. `GET /tasks?completed=false&due_by=<today>` via httpx
3. Format plain text summary
4. `sender.send_message(TELEGRAM_CHAT_ID, text)`

`/trigger/eod`:
1. Validate secret
2. `GET /habits?active=true&date=<today>` via httpx
3. Filter habits where `needs_log_today=true`
4. Build buttons: `callback_data=habit_log:<habit_id>:yes` / `habit_log:<habit_id>:no`
5. `sender.send_message_with_buttons(TELEGRAM_CHAT_ID, text, buttons)` if habits need logging; plain message if all done

`/trigger/check-reminders`:
1. Validate secret
2. `GET /reminders?fired=false&due_by=<now>` via httpx
3. For each due reminder: send `reminder.title` via sender, then `POST /reminders/{id}/fire`
4. No due reminders → 200, no message sent

### State / Storage
None. Reads from tasks-service, writes only via `POST /reminders/{id}/fire`.

### Dependencies
`bot/sender.py`, `httpx`, `TELEGRAM_CHAT_ID` and `TASKS_SERVICE_URL` from env.

### Constraints
- 401 on secret mismatch — no action taken
- All Telegram sends via `sender.py`
- `callback_data` format must match `bot/buttons.py` exactly: `habit_log:<habit_id>:yes` / `habit_log:<habit_id>:no`
- Fire reminder after sending, not before
- No agent call for message formatting (ADR 003)

### Test Spec

**Behaviors to test:**

Secret validation (all endpoints)
- Correct secret → 200
- Wrong secret → 401, no Telegram message, no tasks-service call
- Missing secret field → 401

`POST /trigger/morning`
- tasks-service called with `GET /tasks?completed=false&due_by=<today>`
- Returns 200, sends one Telegram message to `TELEGRAM_CHAT_ID`
- Message contains task titles
- No open tasks → 200, message sent (not silence)

`POST /trigger/eod`
- tasks-service called with `GET /habits?active=true&date=<today>`
- Habits with `needs_log_today=true` → message with inline buttons sent
- `callback_data` format exactly `habit_log:<habit_id>:yes` / `habit_log:<habit_id>:no`
- One button pair per habit needing logging
- All habits already logged → plain message, no buttons
- No active habits → plain message, no buttons

`POST /trigger/check-reminders`
- tasks-service called with `GET /reminders?fired=false&due_by=<now>`
- One due reminder → message sent with `reminder.title`, then fire call made
- Multiple reminders → each sent and fired individually
- Fire call made after send, not before
- No due reminders → 200, no message, no fire call

**Edge cases:**
- tasks-service returns 500 → endpoint returns 500, no partial firing
- tasks-service unreachable → endpoint returns 500, no Telegram message
- EOD: one habit needs logging, one does not → only needing-logging habit gets button pair

**What is NOT tested here:**
- Actual Telegram API — sender mocked
- Actual tasks-service HTTP — mocked via `respx`
- Agent graph — not used (ADR 003)
- cron-job.org configuration — manual setup
