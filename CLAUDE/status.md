# Project Status
# Maintained by: manager
# Updated after every agent action

last_updated: "2026-06-27"
current_phase: complete

---

## Where We Are

Setup complete (2026-06-27): conventions, context, Dockerfiles, pyproject.toml, CLAUDE.md written.
Module specs complete (2026-06-27): all 7 modules specced and approved. Module specs written to CLAUDE/module-specs.md.
T01–T08 complete. T09 (proactive triggers) is the final pending task.
Code fixes and refactors identified — see Known Gaps below.

---

## Planning Phase
status: complete

- Gate 1 — Architecture & Structure: agreed
- Gate 2 — Technologies:             agreed
- Gate 3 — Implementation & Order:   agreed
- Challenger sign-off:               PASS (Round 6)

---

## Execution Phase
status: in-progress

| Task | Component | Agent | Status |
|---|---|---|---|
| T01 | Environment & Project Scaffold | devops | complete |
| T02 | tasks-service/db — models + migration | coder | complete |
| T03 | tasks-service/domain — business logic | coder | complete |
| T04 | tasks-service/api — REST API layer | coder | complete |
| T05 | Orchestrator startup spike | coder | complete |
| T06 | orchestrator/tools — LangGraph tools | coder | complete |
| T07 | orchestrator/agent — LangGraph graph | coder | complete |
| T08 | orchestrator/telegram — bot handlers | coder | complete |
| T09 | orchestrator/proactive — trigger endpoints | coder | complete |

---

## Known Gaps (from code review 2026-06-27)

### Resolved (2026-06-27)

G1–G9 implemented and all tests green. See git history for details.

### Must fix before T08/T09 — CLEARED

**G1 — `find_week_bounds` anchors to Monday, should anchor to Sunday** ✓ DONE
File: `tasks-service/domain/habits.py`
Week boundaries must be Sunday 00:00:00 → Saturday 23:59:59.
Fix: replace `day - timedelta(days=day.weekday())` with `day - timedelta(days=day.isoweekday() % 7)`.
The end of week becomes `sunday + timedelta(days=6)` (Saturday), not `monday + timedelta(days=6)` (Sunday).
Update tests in `tests/test_domain_habits.py` to assert Sunday-anchored bounds.

**G2 — Rename two functions in `domain/habits.py`**
File: `tasks-service/domain/habits.py`
- `completions_in_range` → `count_completions_in_range`
- `needs_log_in_range` → `is_habit_hit_in_range`
Update all callers:
- `tasks-service/api/habits.py` (imports and calls both)
- `tasks-service/domain/goals.py` (imports and calls `completions_in_range`)
Update all tests in `tests/test_domain_habits.py` that call these functions by name.

**G3 — Rename `goal_progress` to `get_goal_progress`**
File: `tasks-service/domain/goals.py`
Rename the function. Update caller in `tasks-service/api/goals.py`.
Update tests in `tests/test_domain_goals.py`.

**G4 — `datetime.utcnow()` deprecated**
File: `tasks-service/db/models.py` lines 29, 42, 62, 72
Replace every `default_factory=datetime.utcnow` with:
`default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)`
Also add `from datetime import timezone` to the imports.

**G5 — `frequency_unit` docstring has wrong enum values**
File: `orchestrator/tools/tasks_tool.py`
In `create_habit` and `update_habit` docstrings: replace `'day'`/`'week'` with `'daily'`/`'weekly'`.
The LLM reads these docstrings — wrong values cause API 422 errors.

**G6 — Add `/health` endpoint to both services**
Files: `tasks-service/main.py`, `orchestrator/main.py`
Add `@app.get("/health") def health(): return {"status": "ok"}` to each.

**G7 — Remove `thread_id` from `ConversationState`**
File: `orchestrator/agent/state.py`
Remove the `thread_id: str` field entirely. Thread ID is carried by LangGraph config,
not state.
Also update every `ainvoke` call in `orchestrator/tests/test_agent.py` that passes
`"thread_id": "..."` inside the state dict — remove that key from the dict.
The `thread_id` should only appear in `config={"configurable": {"thread_id": ...}}`.

**G8 — Remove `reply` field and `format_response` node**
Files: `orchestrator/agent/state.py`, `orchestrator/agent/nodes.py`, `orchestrator/agent/graph.py`

In `state.py`: remove `reply: str` field.

In `nodes.py`: delete the `format_response` function entirely.

In `graph.py`: the router currently returns `"format_response"` when no tool calls are
present. Change it to return `END` directly:
```python
def _router(state):
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "call_tools"
    return END
```
Remove `builder.add_node("format_response", format_response)` and
`builder.add_edge("format_response", END)`.

In `orchestrator/tests/test_agent.py`: replace every `result["reply"]` with
`result["messages"][-1].content`. Check all assertions in all test functions.

**G9 — Move `ALL_TOOLS` aggregation to `tools/__init__.py`**
Files: `orchestrator/tools/__init__.py`, `orchestrator/tools/tasks_tool.py`, `orchestrator/agent/nodes.py`

`ALL_TOOLS` list stays in `tasks_tool.py` (keep it there as the module's own export).

In `tools/__init__.py` (currently empty), add:
```python
from tools.tasks_tool import ALL_TOOLS as _tasks_tools

ALL_TOOLS = [*_tasks_tools]
```

In `agent/nodes.py`, change:
```python
# before
from tools.tasks_tool import ALL_TOOLS
# after
from tools import ALL_TOOLS
```

No changes needed to `test_tools.py` — it imports individual tools from `tasks_tool`
directly, which continues to work.

---

### Open design decision — goal deletion (not a blocker for T08/T09)

`DELETE /goals/{id}` behavior is undefined for two cases:

1. **Sub-goals**: fails with FK constraint violation if the goal has children.
2. **Bound tasks**: current code deletes all tasks under a goal — likely wrong.

Options:
- **Hard delete + cascade**: destroys tasks. Probably wrong.
- **Hard delete + unlink**: set `task.goal_id = null`. Tasks survive, lose goal link.
- **Hard delete + block**: 409 if tasks or sub-goals exist.
- **Archive instead**: PATCH `status` to `archived`. Tasks and habits remain linked.
  `GoalStatus.archived` already exists in the schema — no migration needed.

Revisit before shipping. Not a blocker for T08/T09.

---

### Testing gap

**G10 — Process-restart persistence not tested with real Postgres checkpointer**
T07 AC "state survives process restart" uses `MemorySaver` only.
Real Postgres checkpointer path is untested. Verify manually after deploying to Oracle Cloud.

---

## Blockers

None.

---

## Departures from Agreement Doc

- **ADR 003**: Proactive triggers do not call `agent/graph.py` for message formatting.
  Messages formatted directly in `proactive/triggers.py`. Agent only invoked for
  reactive user messages and inline button callbacks.

---

## Decisions Made

- Built from scratch: full architecture, data model, interface contracts, build order
- Key decisions: SQLModel ORM, LangGraph Postgres checkpointer, PTB v20 in FastAPI lifespan,
  goals hierarchy (self-referential FK), completed_at/fired_at as nullable timestamps (no bool),
  button callbacks dispatched through agent for consistent LangGraph state
- Setup (2026-06-27): ruff (88 char, E/F/I), pytest asyncio_mode=auto, separate Dockerfiles,
  uvicorn for local dev, Docker only for Postgres
