# Domain Context

## Project
A personal agentic assistant for a single user. Manages tasks, habits, reminders,
and goals via Telegram, with proactive morning and end-of-day check-ins.
The orchestrator initiates contact — it does not only respond to messages.

## Key domain terms

| Term | Meaning |
|---|---|
| **Task** | A one-off thing to complete. Completion tracked via `completed_at` (null = open, timestamp = done). |
| **Habit** | A recurring behavior tied to a goal, tracked by frequency. Can be paused (`active=False`) without deleting history. |
| **HabitLog** | A single completion entry for a habit with a timestamp and optional note. |
| **Reminder** | A scheduled notification. Not a task — prompts the user to create tasks. Fired status tracked via `fired_at` (null = not yet fired). |
| **Goal** | A personal objective habits and tasks roll up to. Self-referential (sub-goals via `parent_goal_id`). |
| **Proactive check-in** | A message the orchestrator initiates unprompted — morning task summary or EOD habit check with inline Yes/No buttons. |
| **Thread ID** | The Telegram `chat_id` used as LangGraph's conversation identifier for state persistence across messages. |
| **Inline keyboard button** | A Yes/No button sent with the EOD check-in message. Tapping sends a Telegram callback query handled by `bot/buttons.py`. |
| **`callback_data`** | Payload attached to inline keyboard buttons. Format: `habit_log:<habit_id>:yes` or `habit_log:<habit_id>:no`. Parsed by `buttons.py` to identify the habit and the user's choice. |
| **`PROACTIVE_SECRET`** | Shared secret sent in the POST body of every `/trigger/*` request. Validated before any trigger is processed; prevents unauthorized proactive messages. |
