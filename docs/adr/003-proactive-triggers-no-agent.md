# ADR 003 — Proactive triggers format messages directly, no agent call

**Date:** 2026-06-27
**Status:** Decided

## Context

The Agreement Doc data flows show `orchestrator/agent/graph.py` in the proactive
trigger path for all three triggers (morning, EOD, check-reminders). The intent
was for the agent to format the outgoing Telegram messages.

## Decision

Proactive triggers (`proactive/triggers.py`) format messages directly — no call to
`agent/graph.py`. Reminder messages are sent verbatim (just `reminder.title`).

## Reasons

- **Cost**: every cron ping (including `/trigger/check-reminders` which runs every
  minute) would make a Groq API call. At the free tier, this is wasteful and could
  hit rate limits.
- **Simplicity**: morning and EOD messages are simple list formatting — "here are
  your open tasks: ..." and "did you do these habits today?" — no LLM reasoning
  needed.
- **Reminders**: always sent verbatim by design (Agreement Doc §6.1). Routing through
  the agent adds latency with no benefit.
- **State**: invoking the agent with a synthetic message would create conversation
  state entries for proactive turns that serve no purpose — they are never part of
  a real conversation thread.

## Consequences

- `proactive/triggers.py` imports `bot/sender.py` and `httpx` only — no dependency
  on `agent/graph.py`.
- Message formatting logic lives in `proactive/triggers.py` as plain string
  construction.
- The agent is only invoked for reactive user messages (via `bot/handlers.py`) and
  inline button callbacks (via `bot/buttons.py`).
- This is a documented departure from the Agreement Doc data flow diagrams.
  The Agreement Doc is kept as-is (historical record); this ADR takes precedence.
