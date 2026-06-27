# Module: orchestrator/proactive

All endpoints require `{"secret": "<PROACTIVE_SECRET>"}` in the POST body. Returns 401 on mismatch.

## Endpoints

| Endpoint | Method | Returns | Description |
|---|---|---|---|
| `/trigger/morning` | `POST` | 200 / 401 | Fetches open tasks due today, sends morning summary to Telegram |
| `/trigger/eod` | `POST` | 200 / 401 | Fetches active habits needing a log today, sends EOD check-in with Yes/No buttons |
| `/trigger/check-reminders` | `POST` | 200 / 401 | Fetches unfired due reminders, sends each and marks fired |

## Notes

- All Telegram sends go via `bot/sender.py`
- Reminder is fired after sending, not before
- No agent call for formatting — messages constructed directly (ADR 003)
