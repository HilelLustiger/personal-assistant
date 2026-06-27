import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from langgraph.checkpoint.base import empty_checkpoint
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")


def _pg_conn_string(url: str) -> str:
    """Strip SQLAlchemy driver prefix so psycopg3 can use the URL directly."""
    return url.replace("postgresql+psycopg://", "postgresql://")


@asynccontextmanager
async def lifespan(app: FastAPI):
    telegram_app = None

    if TELEGRAM_BOT_TOKEN:
        from telegram import Update
        from telegram.ext import ApplicationBuilder, MessageHandler, filters

        async def pong_handler(update: Update, context) -> None:
            await update.message.reply_text("pong")

        telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, pong_handler))
        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.updater.start_polling()

    app.state.telegram_app = telegram_app

    from agent.graph import build_graph

    conn_string = _pg_conn_string(DATABASE_URL)
    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        await checkpointer.setup()
        app.state.agent_graph = build_graph(checkpointer)
        try:
            yield
        finally:
            if telegram_app is not None:
                await telegram_app.updater.stop()
                await telegram_app.stop()
                await telegram_app.shutdown()


app = FastAPI(title="Orchestrator", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/trigger/test")
def trigger_test():
    """Prove that FastAPI + LangGraph Postgres checkpointer work together.
    Writes a state and reads it back — returns 200 only if both succeed."""
    conn_string = _pg_conn_string(DATABASE_URL)
    thread_id = f"spike-{uuid.uuid4()}"

    with PostgresSaver.from_conn_string(conn_string) as checkpointer:
        checkpointer.setup()

        config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        checkpoint = empty_checkpoint()
        saved_config = checkpointer.put(
            config,
            checkpoint,
            {"source": "input", "step": 0, "parents": {}},
            {},
        )

        result = checkpointer.get_tuple(saved_config)

    if result is None:
        raise HTTPException(status_code=500, detail="Checkpointer failed to persist state")

    return {"status": "ok"}
