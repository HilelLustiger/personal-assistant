# ADR 002 — Agent state fields and tool aggregation

**Date:** 2026-06-27
**Status:** Decided

---

## Decision 1 — Remove `thread_id` from `ConversationState`

### Context
`ConversationState` had a `thread_id` field alongside `messages` and `reply`.
LangGraph already carries the thread ID in `config["configurable"]["thread_id"]` —
it is how the Postgres checkpointer keys persisted state. Storing it in the state
schema as well creates two sources of truth that could diverge.

### Decision
Remove `thread_id` from `ConversationState`. Read thread ID from LangGraph config
exclusively when needed.

### Consequences
- `ConversationState` only contains fields that are meaningfully part of conversation
  state, not routing metadata.
- Callers pass `thread_id` via `config["configurable"]["thread_id"]` as LangGraph
  intends — no change to how the graph is invoked.

---

## Decision 2 — Remove `reply` from `ConversationState`; callers read last message

### Context
`ConversationState` had a `reply` field populated by the `format_response` node
so callers could read `result["reply"]`. This is unconventional — LangGraph state
is designed to accumulate inputs, not carry output values. It also creates coupling:
every caller must know to read `result["reply"]` rather than the standard
`result["messages"][-1].content`.

### Decision
Remove `reply` from `ConversationState` and the `format_response` node.
Callers (bot handlers, proactive triggers) read the agent's reply as
`result["messages"][-1].content` — the LangGraph default.

### Consequences
- `ConversationState` becomes a single-field TypedDict: `messages` only.
- `format_response` node is no longer needed — the graph ends at `call_model`
  when no tool calls are present.
- All callers use the standard LangGraph pattern; no special knowledge of a
  `reply` field required.

---

## Decision 3 — Tool calls execute sequentially, not in parallel

### Context
`call_tools` executes tool calls in a Python `for` loop — sequentially.
The LLM can request multiple tools in a single turn (e.g. "show my tasks and habits").

### Decision
Keep sequential execution. Do not parallelise tool calls with `asyncio.gather`.

### Reasons
- The agent rarely requests more than one tool per turn in practice.
- Sequential execution is simpler to debug and reason about.
- For a single-user personal assistant, latency from sequential calls is negligible.

### Consequences
- If the model requests two tools, the second runs after the first completes.
- Revisit only if multi-tool turns become a common pattern and latency matters.

---

## Decision 4 — `tools/__init__.py` aggregates all tool lists

### Context
`nodes.py` currently imports `ALL_TOOLS` directly from `tools/tasks_tool.py`.
Phase 2 (library service) and Phase 3 (notes service) will add new tool files.
With a direct import, `nodes.py` must be edited every time a new tool file is added.

### Decision
`tools/__init__.py` owns the single `ALL_TOOLS` export — it imports and concatenates
tool lists from each tool file. `nodes.py` imports `ALL_TOOLS` from `tools` (the
package), not from a specific tool file.

```python
# tools/__init__.py
from tools.tasks_tool import ALL_TOOLS as _tasks_tools

ALL_TOOLS = [
    *_tasks_tools,
    # Phase 2: *_library_tools,
    # Phase 3: *_notes_tools,
]
```

### Consequences
- Adding a new tool file requires only a one-line change to `tools/__init__.py`.
- `nodes.py` is stable — it never needs to change when tools are added.
