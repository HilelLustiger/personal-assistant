# Module: orchestrator/bot

## bot/sender.py

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `send_message(chat_id, text)` | `chat_id: str`, `text: str` | `None` | Send plain text to a Telegram chat |
| `send_message_with_buttons(chat_id, text, buttons)` | `chat_id: str`, `text: str`, `buttons: list[list[InlineKeyboardButton]]` | `None` | Send message with inline keyboard |

## bot/handlers.py

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `handle_message(update, context)` | `update: Update`, `context: ContextTypes` | `None` | Handles incoming text messages — passes to agent, sends reply via sender |
| `register_handlers(application)` | `application: Application` | `None` | Registers all handlers with the Telegram Application |

## bot/buttons.py

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `handle_button_callback(update, context)` | `update: Update`, `context: ContextTypes` | `None` | Handles inline button callbacks — dispatches to agent, sends confirmation via sender |

## callback_data format

`habit_log:<habit_id>:yes` — log the habit via agent  
`habit_log:<habit_id>:no`  — acknowledge, no agent call
