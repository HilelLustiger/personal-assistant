# ADR-005: Telegram bot wiring — sender isolation and lifespan injection

date: 2026-06-27
status: accepted
feature: telegram-bot-and-proactive-triggers

---

## Context

T08 (bot handlers) and T09 (proactive triggers) both send messages to Telegram.
Three modules initiate sends: `bot/handlers.py`, `bot/buttons.py`, and
`proactive/triggers.py`. Two objects must reach handlers at runtime without
circular imports: the `Bot` object (from python-telegram-bot) and the compiled
LangGraph graph. Neither is available at module import time — both are created
during the FastAPI lifespan startup.

## Decision

1. All outbound Telegram sends go through `bot/sender.py`. No other module calls
   the Telegram API directly.
2. `sender.py` holds a module-level `_bot = None`, initialized via `set_bot(bot)`
   called in `main.py` lifespan after `ApplicationBuilder().build()`.
3. The agent graph is injected into handlers via `context.bot_data["agent_graph"]`
   (set in lifespan after the graph is built), not imported directly.
4. Inline button callbacks are dispatched through the agent (not directly to
   tasks-service) to keep LangGraph conversation state consistent.

## Key choices

| Choice | Alternatives considered | Reason |
|---|---|---|
| `sender.py` as sole Telegram output channel | Each module calls Telegram directly | Single testable interface; one place for error handling and future rate-limiting |
| Module-level `_bot` + `set_bot()` | Import `Bot` object at module level | `Bot` isn't available at import time; avoids circular imports between `main.py` and `bot/` |
| `context.bot_data["agent_graph"]` for agent injection | Direct import of `build_graph` in handlers | PTB's `context` is per-request; importing the graph would create tight coupling and make unit testing handlers harder |
| Button callbacks dispatched through agent | Direct tasks-service HTTP call from `buttons.py` | LangGraph state reflects the check-in outcome; conversation continuity preserved across turns |

## Consequences

- All Telegram sends go through one interface — `sender._bot` can be replaced in
  tests via direct assignment, without patching Telegram APIs.
- Handlers are stateless at definition time: they receive `update` + `context`,
  read the graph from `context.bot_data`, and call `sender.send_message` — no
  module-level globals needed in `handlers.py` or `buttons.py`.
- Circular import risk eliminated: `bot/` never imports `agent/`; the graph
  arrives at runtime via `main.py`.
- Dev mode uses `updater.start_polling()` inside lifespan; production switches
  to webhook by removing the updater and adding a `/webhook` POST route (no
  code changes to `bot/` required).
