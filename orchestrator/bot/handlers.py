import logging

from langchain_core.messages import HumanMessage
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot import sender

logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.effective_message.text
    if not text:
        return

    chat_id = str(update.effective_chat.id)
    agent_graph = context.bot_data["agent_graph"]

    try:
        result = await agent_graph.ainvoke(
            {"messages": [HumanMessage(content=text)]},
            config={"configurable": {"thread_id": chat_id}},
        )
        reply = result["messages"][-1].content
    except Exception:
        logger.exception("Error handling message from chat_id=%s", chat_id)
        reply = "Sorry, something went wrong. Please try again."

    await sender.send_message(chat_id, reply)


def register_handlers(application: Application) -> None:
    from bot.buttons import handle_button_callback

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    application.add_handler(CallbackQueryHandler(handle_button_callback))
