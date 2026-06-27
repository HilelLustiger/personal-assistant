from langchain_core.messages import HumanMessage
from telegram import Update
from telegram.ext import ContextTypes

from bot import sender


async def handle_button_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    chat_id = str(update.effective_chat.id)
    agent_graph = context.bot_data["agent_graph"]

    parts = (query.data or "").split(":")
    if len(parts) != 3 or parts[0] != "habit_log":
        await sender.send_message(chat_id, "Sorry, I didn't understand that button.")
        return

    habit_id = parts[1]
    action = parts[2]

    if action == "yes":
        message_text = f"Please log the habit completion for habit {habit_id}."
        try:
            result = await agent_graph.ainvoke(
                {"messages": [HumanMessage(content=message_text)]},
                config={"configurable": {"thread_id": chat_id}},
            )
            reply = result["messages"][-1].content
        except Exception:
            reply = "Sorry, something went wrong logging your habit."
        await sender.send_message(chat_id, reply)
    else:
        await sender.send_message(chat_id, "No problem, skipped for today.")
