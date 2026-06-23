# Work Order
# Created by: manager
# Read by: coder, devops, reviewer

date: "2026-06-23"
based_on: "CLAUDE/agreement.md"
status: in-progress

---

```yaml
work_order:
  summary: >
    Build Phase 1 of the Personal Agentic Assistant — a Tasks Service (FastAPI + PostgreSQL)
    and an Orchestrator (LangGraph agent + Telegram bot) that lets the user manage tasks,
    habits, reminders, and goals via Telegram, with proactive morning and EOD check-ins.
  agreement_doc: "CLAUDE/agreement.md"

  conventions:
    - "Each task ends with a git commit and push to main once acceptance criteria are met"
    - "Commit message format: '<TXX>: <short description>' e.g. 'T02: add SQLModel models and Alembic migration'"
    - "Repo is public — verify .gitignore excludes .env and all secrets before every push"

  tasks:
    - id: T01
      assigned_to: devops
      component: Environment & Project Scaffold
      status: complete
      description: >
        Set up the project scaffold, local development environment, and GitHub repository.
        Create the top-level directory structure (tasks-service/, orchestrator/,
        docker-compose.yml). Write docker-compose.yml with a PostgreSQL 15 service
        (named 'db', port 5432, with a named volume). Write .env.example listing all
        required environment variables with empty values (DATABASE_URL,
        TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GROQ_API_KEY, PROACTIVE_SECRET).
        Write tasks-service/requirements.txt (fastapi, sqlmodel, psycopg[binary],
        alembic, uvicorn, pytest, httpx). Write orchestrator/requirements.txt
        (fastapi, uvicorn, langgraph, langgraph-checkpoint-postgres, litellm,
        python-telegram-bot[webhooks], httpx, pytest). Initialize Alembic in
        tasks-service/ with alembic init alembic, configure alembic.ini to read
        DATABASE_URL from the environment.
        Write a thorough .gitignore covering: .env, __pycache__/, *.pyc, *.pyo,
        .pytest_cache/, *.egg-info/, dist/, .venv/, venv/, .DS_Store.
        Initialize git, create a public GitHub repository named 'personal-assistant'
        (via gh repo create), make an initial commit of the scaffold, and push to main.
      acceptance_criteria:
        - "docker compose up db starts Postgres with no errors"
        - "alembic upgrade head connects to the DB and reports no errors (empty but connected)"
        - "pip install -r tasks-service/requirements.txt completes without errors"
        - "pip install -r orchestrator/requirements.txt completes without errors"
        - ".env.example is committed; .env is in .gitignore and never committed"
        - "GitHub repo exists, scaffold is pushed to main, .env does not appear in git history"
      constraints:
        - "PostgreSQL version 15"
        - "Python 3.11+"
        - "All credentials in .env only — never committed"
        - "Repo is public — double-check .gitignore excludes .env and any secrets before pushing"
      depends_on: []
      notes: >
        Convention for all subsequent tasks: each task ends with a commit and push
        to main once its acceptance criteria are met. Commit message should reference
        the task ID (e.g. 'T02: add SQLModel models and first Alembic migration').

    - id: T02
      assigned_to: coder
      component: tasks-service/db — SQLModel models + Alembic migration
      description: >
        Implement all five SQLModel database models in tasks-service/db/models.py
        and generate the first Alembic migration.
        Models: Goal (id UUID PK, parent_goal_id FK→goals nullable, name str,
        description str nullable, status enum active/completed/archived default active,
        target_date datetime nullable, created_at datetime server_default now).
        Habit (id UUID PK, goal_id FK→habits NOT NULL, name str,
        frequency_target int, frequency_unit enum daily/weekly, start_date date,
        active bool default True, created_at datetime server_default now).
        HabitLog (id UUID PK, habit_id FK→habits NOT NULL, completed_at datetime,
        note str nullable — add composite index on (habit_id, completed_at)).
        Task (id UUID PK, goal_id FK→goals nullable, title str, due_datetime datetime
        nullable, completed_at datetime nullable, created_at datetime server_default now).
        Reminder (id UUID PK, title str, trigger_datetime datetime, fired_at datetime
        nullable, created_at datetime server_default now).
        Also create tasks-service/db/session.py with engine creation from DATABASE_URL
        and a get_session() FastAPI dependency.
      acceptance_criteria:
        - "alembic upgrade head creates all five tables in PostgreSQL with correct columns"
        - "habit_logs table has a composite index on (habit_id, completed_at)"
        - "alembic downgrade base drops all tables cleanly"
        - "SQLModel models can be imported without errors"
      constraints:
        - "Use SQLModel, not raw SQLAlchemy"
        - "UUIDs as primary keys (not integer auto-increment)"
        - "No completed bool on tasks — use completed_at IS NOT NULL as the completion check"
        - "No fired bool on reminders — use fired_at IS NOT NULL"
      depends_on: [T01]

    - id: T03
      assigned_to: coder
      component: tasks-service/domain — business logic layer
      description: >
        Implement the domain layer in tasks-service/domain/ as pure Python functions
        with no FastAPI or database dependencies. Write tests first (TDD).
        domain/habits.py: needs_log_today(habit, logs_this_week: list, date) -> bool
        (true if completions_this_week < frequency_target for the given date's week);
        completions_this_week(habit_id, logs: list, date) -> int.
        domain/tasks.py: is_overdue(task, now: datetime) -> bool
        (due_datetime is set, < now, and completed_at is None).
        domain/goals.py: goal_progress(goal, habits_with_logs: list, tasks: list) -> dict
        returns {habits: [{id, completion_rate: float}], tasks_completed: int, tasks_total: int}.
        domain/reminders.py: is_due(reminder, now: datetime) -> bool
        (trigger_datetime <= now and fired_at is None).
        All functions take plain Python objects — no DB sessions.
      acceptance_criteria:
        - "pytest tasks-service/domain/ passes with all tests green"
        - "needs_log_today returns True when completions_this_week < frequency_target"
        - "needs_log_today returns False when completions_this_week >= frequency_target"
        - "is_overdue returns False for tasks with no due_datetime"
        - "goal_progress completion_rate is capped at 1.0"
        - "No FastAPI, SQLModel, or database imports in any domain/ file"
      constraints:
        - "Pure Python functions only — no side effects, no DB calls"
        - "Domain logic must not import from api/ or db/"
      depends_on: [T02]

    - id: T04
      assigned_to: coder
      component: tasks-service/api — REST API layer
      description: >
        Implement all FastAPI routers in tasks-service/api/ using the interface contracts
        from the Agreement Doc. One router file per domain: goals.py, habits.py,
        tasks.py, reminders.py. Wire them into tasks-service/main.py.
        Each router implements the full contract: GET (with query filters), POST, PATCH,
        DELETE. Special endpoints: POST /tasks/{id}/complete, POST /habits/{id}/log,
        POST /reminders/{id}/fire. Computed endpoints: GET /habits?date=<date> must
        return needs_log_today and completions_this_week (call domain/habits.py);
        GET /goals/{id}/progress must return full progress shape (call domain/goals.py).
        Use get_session() dependency from db/session.py.
        Write API-level tests using FastAPI TestClient against a real test Postgres DB.
      acceptance_criteria:
        - "GET /habits?active=true&date=2026-06-23 returns habit objects with needs_log_today and completions_this_week fields"
        - "GET /goals/{id}/progress returns {habits: [{completion_rate}], tasks_completed, tasks_total}"
        - "POST /tasks creates a task and returns the full task object"
        - "POST /tasks/{id}/complete sets completed_at and returns the updated task"
        - "DELETE /tasks/{id} returns 204"
        - "PATCH /tasks/{id} with {title: 'new title'} updates only that field"
        - "GET /reminders?fired=false&due_by=<datetime> returns only unfired reminders due by that time"
        - "All API tests pass against a test Postgres database"
        - "uvicorn tasks-service.main:app starts with no errors"
      constraints:
        - "Follow interface contracts exactly as specified in CLAUDE/agreement.md"
        - "Call domain/ functions for computed fields — no business logic in routers"
        - "tasks-service has no knowledge of the orchestrator, Telegram, or LangGraph"
        - "Use get_session() FastAPI dependency for all DB access"
      depends_on: [T03]
      review_checkpoint: >
        After basic CRUD for all four entities is working and tested, before implementing
        the computed endpoints (GET /habits?date and GET /goals/{id}/progress).

    - id: T05
      assigned_to: coder
      component: Orchestrator startup spike
      description: >
        Prove that python-telegram-bot v20, FastAPI, and the LangGraph Postgres
        checkpointer can all run together in a single Uvicorn process before any
        agent logic is written. This is a spike — build the minimum to validate
        the architecture, then keep the result as the real orchestrator/main.py.
        Implement orchestrator/main.py using FastAPI lifespan:
        initialize and start the Telegram Application inside lifespan (using
        updater.start_polling() for development), add a POST /trigger/test endpoint
        that returns {status: ok}, configure the LangGraph PostgresSaver checkpointer
        with DATABASE_URL, write a test state to the checkpointer and read it back
        in the same request to confirm persistence. The Telegram bot should reply
        "pong" to any message during the spike.
        If any of the three components fail to coexist, escalate to architect before
        proceeding.
      acceptance_criteria:
        - "uvicorn orchestrator.main:app starts with no errors"
        - "Telegram bot replies 'pong' to a test message"
        - "POST /trigger/test returns {status: ok}"
        - "LangGraph checkpointer writes and reads a test state successfully in one request"
        - "No event loop conflicts or RuntimeError on startup"
      constraints:
        - "Uvicorn owns the event loop — do NOT call application.run_polling() directly"
        - "Use FastAPI lifespan context manager as specified in CLAUDE/agreement.md Gate 2"
        - "LangGraph checkpointer uses DATABASE_URL (same Postgres as tasks-service)"
        - "If the pattern fails, escalate — do not work around it with threads or subprocesses"
      depends_on: [T01]
      notes: >
        T05 only needs Postgres running (from T01) — it does not need tasks-service
        to be built. It can run in parallel with T02/T03/T04 if desired.
        T06 cannot start until both T04 AND T05 are complete.

    - id: T06
      assigned_to: coder
      component: orchestrator/tools — LangGraph tool definitions
      description: >
        Implement orchestrator/tools/tasks_tool.py — all LangGraph tool definitions
        that wrap the tasks-service REST API. Define one tool per logical operation
        using httpx for async HTTP calls to tasks-service. Tools must cover the full
        interface contract: list/create/update/delete for goals, tasks, habits, reminders;
        complete a task; log a habit; fire a reminder; get goal progress; get habits with
        due status. Each tool should have a clear docstring describing its purpose
        (this is what the LLM reads to decide which tool to call).
        Write tests using httpx mock (no live tasks-service needed).
      acceptance_criteria:
        - "All tool functions are importable as LangGraph tools"
        - "Each tool has a descriptive docstring"
        - "Tool for POST /tasks sends correct request body and returns parsed response"
        - "Tool for GET /habits with date parameter includes needs_log_today in result"
        - "Tool for GET /goals/{id}/progress returns completion_rate per habit"
        - "pytest orchestrator/tools/ passes with httpx mock"
      constraints:
        - "Use httpx AsyncClient for all HTTP calls — no requests library"
        - "tools/tasks_tool.py must not import from agent/ — no circular dependencies"
        - "Tasks-service base URL read from environment variable TASKS_SERVICE_URL"
        - "Follow request/response shapes exactly as in CLAUDE/agreement.md interface contracts"
      depends_on: [T04, T05]

    - id: T07
      assigned_to: coder
      component: orchestrator/agent — LangGraph graph + state persistence
      description: >
        Implement the LangGraph agent in orchestrator/agent/.
        state.py: define the conversation state schema (messages list, thread_id,
        current_intent or similar).
        graph.py: define the LangGraph StateGraph — nodes for intent routing, tool
        calling, and response formatting. Wire in the tools from tasks_tool.py.
        nodes.py: implement node functions (call_model, call_tools, format_response).
        Configure the Postgres checkpointer (from T05's main.py) as the graph's
        checkpointer so state persists across process restarts.
        The graph must handle at minimum: create task, list open tasks, complete task,
        log habit, create reminder, show goal progress.
      acceptance_criteria:
        - "Sending 'add task: buy milk' programmatically results in a POST /tasks call to tasks-service"
        - "Sending 'show my open tasks' results in a GET /tasks?completed=false call"
        - "Two sequential messages share state via the Postgres checkpointer"
        - "Restarting the orchestrator process and continuing a conversation works (state persisted)"
        - "Agent returns a formatted reply string, not raw JSON"
      constraints:
        - "Use LangGraph StateGraph — not a custom loop"
        - "LiteLLM + Groq as the LLM backend"
        - "State must survive process restarts — memory checkpointer is NOT acceptable"
        - "Do not wire Telegram in this task — test programmatically only"
      depends_on: [T06]
      review_checkpoint: >
        After basic tool calling works (create task and list tasks round-trip),
        before implementing state persistence across restarts.

    - id: T08
      assigned_to: coder
      component: orchestrator/telegram — Telegram bot handlers
      description: >
        Wire the LangGraph agent to Telegram in orchestrator/telegram/.
        handlers.py: handle incoming text messages — pass to agent/graph.py with
        the Telegram chat_id as thread_id, send the agent's reply via sender.py.
        buttons.py: handle inline button callback queries (EOD habit Yes/No) —
        dispatch to agent/graph.py as an agent event so LangGraph state reflects
        the completed check-in, send confirmation via sender.py.
        sender.py: owns all outbound Telegram API calls (send_message,
        send_message_with_buttons). Used by handlers.py, buttons.py, and proactive/.
        Register all handlers with the Telegram Application in main.py.
      acceptance_criteria:
        - "Sending 'add task: buy milk' in Telegram results in the task appearing in Postgres"
        - "The bot replies with a confirmation message in Telegram"
        - "Tapping a Yes/No inline button triggers a POST /habits/{id}/log call"
        - "Button callback reply is sent to Telegram via sender.py"
        - "All outbound Telegram calls go through sender.py — handlers never call Telegram API directly"
      constraints:
        - "Use telegram/sender.py for ALL outbound Telegram calls — no direct bot.send_message() in handlers"
        - "Thread ID for LangGraph must be the Telegram chat_id (string)"
        - "proactive/ must not be modified in this task — that is T09"
      depends_on: [T07]
      review_checkpoint: >
        After the reactive text flow works end-to-end (message → agent → tasks-service → reply),
        before implementing the inline button callback handler.

    - id: T09
      assigned_to: coder
      component: orchestrator/proactive — scheduled trigger endpoints
      description: >
        Implement orchestrator/proactive/triggers.py with three FastAPI POST endpoints.
        POST /trigger/morning: validate PROACTIVE_SECRET, call GET /tasks?completed=false
        &due_by=<today>, pass data to agent/graph.py to format a morning summary message,
        send via telegram/sender.py.
        POST /trigger/eod: validate PROACTIVE_SECRET, call GET /habits?active=true
        &date=<today>, pass to agent to format EOD check-in, send via sender.py with
        inline Yes/No buttons for each habit that needs_log_today=true.
        POST /trigger/check-reminders: validate PROACTIVE_SECRET, call
        GET /reminders?fired=false&due_by=<now>, for each due reminder pass to agent
        to format message, send via sender.py, then call POST /reminders/{id}/fire.
        Register all three routes in main.py.
        Test all three endpoints with curl before configuring cron-job.org.
      acceptance_criteria:
        - "POST /trigger/morning with correct secret sends a Telegram message listing open tasks for today"
        - "POST /trigger/eod with correct secret sends a Telegram message with inline Yes/No buttons for due habits"
        - "POST /trigger/check-reminders fires due reminders and marks them fired_at in the DB"
        - "POST /trigger/morning with wrong secret returns 401"
        - "POST /trigger/check-reminders with no due reminders sends no message and returns 200"
      constraints:
        - "Validate PROACTIVE_SECRET on every trigger endpoint — return 401 on mismatch"
        - "All Telegram sends go through telegram/sender.py"
        - "proactive/ must not call the Telegram API directly"
        - "check-reminders must mark each fired reminder via POST /reminders/{id}/fire after sending"
      depends_on: [T08]

  open_questions: []
```
