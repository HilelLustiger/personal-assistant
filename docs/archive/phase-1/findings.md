# Findings

**Mode:** checkpoint
**Scope:** Full Phase 1 implementation — tasks-service (T01–T04) and orchestrator (T05–T09)
**Date:** 2026-06-27
**Reviewer:** reviewer skill

---

## Summary

The Phase 1 implementation is structurally sound: the microservice split is respected, domain logic is pure Python, the LangGraph agent correctly uses the Postgres checkpointer, and the Telegram bot wiring follows the spec. One real bug was found in `api/goals.py` — a name collision that makes the progress endpoint infinitely recursive at runtime. Several ruff lint violations exist across both services (unsorted imports, lines over 88 chars, one E402, one unused import). All are fixable with a single ruff pass plus one rename.

---

## Key Findings

### 1. BUG — `GET /goals/{id}/progress` infinitely recurses (F811)

**File:** `tasks-service/api/goals.py`, lines 10 and 81
**Severity:** Critical — endpoint crashes on every call

```python
from domain.goals import get_goal_progress  # line 10 — import shadowed immediately below

@router.get("/{goal_id}/progress")
def get_goal_progress(goal_id: uuid.UUID, ...):  # line 81 — shadows the import at global scope
    ...
    progress = get_goal_progress(goal, habits_with_logs, ...)  # line 97 — calls the route handler, not the domain function
```

When line 97 resolves `get_goal_progress`, Python finds the route handler in the global scope (the import was overwritten when the function was defined). The call fails with `TypeError` (wrong argument types). No API-level test covers this endpoint, so it passed CI.

**Fix:** Rename the router function to `goal_progress_endpoint` (or any name that doesn't collide), or alias the domain import: `from domain.goals import get_goal_progress as compute_goal_progress`.

---

### 2. Ruff lint violations — auto-fixable

`ruff check` reports 124 violations across both services, almost entirely cosmetic:

| Code | Count | Description | Fix |
|---|---|---|---|
| I001 | 23 | Import blocks unsorted | `ruff check --fix` |
| E501 | ~90 | Lines over 88 chars | `ruff format` |
| E402 | 15 | Module-level import not at top of file | Move imports to top |
| F401 | 1 | `ConversationState` possibly unused in `nodes.py` | Verify or add `# noqa` |
| F811 | 1 | Name collision in `api/goals.py` | See Finding 1 |
| E401 | 2 | Multiple imports on one line | Split |

The E402 violations are mostly in `main.py` because `from proactive.triggers import router` was added after the `app = FastAPI(...)` line. Move it to the top of the imports block.

---

### 3. `GET /goals/{id}/progress` has no API-level test

The domain function `get_goal_progress` is unit-tested in `test_domain_goals.py`, but there is no integration test for the HTTP endpoint `GET /goals/{id}/progress`. This is how Finding 1 went undetected.

**Fix:** Add one integration test for the progress endpoint in `tasks-service/tests/test_main.py`.

---

### 4. `sender.py` crashes if called before `set_bot` (no guard)

`send_message` and `send_message_with_buttons` call `_bot.send_message(...)` where `_bot` is `None` at import time. If a trigger fires before the lifespan completes (e.g. in tests or a race), it raises `AttributeError: 'NoneType' object has no attribute 'send_message'`. The tests mock `_bot` directly so this is only a runtime concern, not a test concern. A guard is worth adding for production hardening but is not a blocker.

---

### 5. Architecture and conventions — PASS

- Domain layer has no imports from `api/` or `db/` ✓
- All `@tool` functions have docstrings ✓
- Boolean prefixes (`is_`, `has_`, `needs_`) applied correctly ✓
- `ConversationState` has only `messages` — `thread_id` and `reply` correctly removed ✓
- `tools/__init__.py` owns `ALL_TOOLS` aggregation ✓
- All Telegram sends go through `sender.py` ✓
- Proactive triggers format messages directly, no agent call (ADR 003) ✓
- `callback_data` format matches between `proactive/triggers.py` and `bot/buttons.py` ✓
- `find_week_bounds` correctly anchors to Sunday ✓
- `completed_at` / `fired_at` nullable timestamps, no boolean flags ✓

---

## Risks & Unknowns

- Goal deletion (`DELETE /goals/{id}`) deletes all bound tasks — open design question noted in status.md, not blocking but should be resolved before shipping
- Postgres checkpointer persistence across process restarts (G10) — not tested with a real DB, only `MemorySaver` in tests
- `TELEGRAM_CHAT_ID` is a single string — the system is single-user by design, but worth documenting explicitly

---

## Recommended Next Step

**REVISE** — return to `/coder` to fix:
1. Rename `get_goal_progress` route handler in `tasks-service/api/goals.py` to avoid the F811 collision
2. Add one API-level test for `GET /goals/{id}/progress`
3. Run `ruff check --fix` and `ruff format` on both services and commit the result

After those three are done, Phase 1 is ready to ship.
