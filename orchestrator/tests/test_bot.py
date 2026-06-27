from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import HumanMessage


def _make_message_update(chat_id: int, text: str | None):
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_message.text = text
    return update


def _make_callback_update(chat_id: int, callback_data: str):
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.callback_query.data = callback_data
    update.callback_query.answer = AsyncMock()
    return update


def _make_context(agent_graph=None):
    context = MagicMock()
    context.bot_data = {"agent_graph": agent_graph}
    return context


# ── sender ────────────────────────────────────────────────────────────────────


async def test_send_message_calls_bot_send_message():
    import bot.sender as sender_module

    mock_bot = AsyncMock()
    sender_module._bot = mock_bot
    await sender_module.send_message("123", "hello")
    mock_bot.send_message.assert_called_once_with(chat_id="123", text="hello")


async def test_send_message_with_buttons_uses_inline_keyboard_markup():
    import bot.sender as sender_module
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    mock_bot = AsyncMock()
    sender_module._bot = mock_bot
    buttons = [[InlineKeyboardButton("Yes", callback_data="yes")]]
    await sender_module.send_message_with_buttons("123", "check-in", buttons)
    call_kwargs = mock_bot.send_message.call_args[1]
    assert call_kwargs["chat_id"] == "123"
    assert call_kwargs["text"] == "check-in"
    assert isinstance(call_kwargs["reply_markup"], InlineKeyboardMarkup)


# ── handle_message ────────────────────────────────────────────────────────────


async def test_handle_message_invokes_agent_with_human_message():
    from bot.handlers import handle_message

    mock_graph = AsyncMock()
    mock_graph.ainvoke.return_value = {"messages": [MagicMock(content="Done!")]}
    update = _make_message_update(chat_id=42, text="add task: buy milk")
    context = _make_context(mock_graph)

    with patch("bot.handlers.sender") as mock_sender:
        mock_sender.send_message = AsyncMock()
        await handle_message(update, context)

    call_args = mock_graph.ainvoke.call_args
    state = call_args[0][0]
    assert isinstance(state["messages"][0], HumanMessage)
    assert state["messages"][0].content == "add task: buy milk"
    assert call_args[1]["config"]["configurable"]["thread_id"] == "42"


async def test_handle_message_sends_reply_via_sender():
    from bot.handlers import handle_message

    mock_graph = AsyncMock()
    mock_graph.ainvoke.return_value = {"messages": [MagicMock(content="Task added!")]}
    update = _make_message_update(chat_id=42, text="add task: buy milk")
    context = _make_context(mock_graph)

    with patch("bot.handlers.sender") as mock_sender:
        mock_sender.send_message = AsyncMock()
        await handle_message(update, context)
        mock_sender.send_message.assert_called_once_with("42", "Task added!")


async def test_handle_message_skips_agent_when_text_is_empty():
    from bot.handlers import handle_message

    mock_graph = AsyncMock()
    update = _make_message_update(chat_id=42, text=None)
    context = _make_context(mock_graph)

    with patch("bot.handlers.sender") as mock_sender:
        mock_sender.send_message = AsyncMock()
        await handle_message(update, context)

    mock_graph.ainvoke.assert_not_called()
    mock_sender.send_message.assert_not_called()


async def test_handle_message_sends_error_when_agent_raises():
    from bot.handlers import handle_message

    mock_graph = AsyncMock()
    mock_graph.ainvoke.side_effect = Exception("LLM unavailable")
    update = _make_message_update(chat_id=42, text="hello")
    context = _make_context(mock_graph)

    with patch("bot.handlers.sender") as mock_sender:
        mock_sender.send_message = AsyncMock()
        await handle_message(update, context)
        mock_sender.send_message.assert_called_once()
        sent_text = mock_sender.send_message.call_args[0][1]
        assert "sorry" in sent_text.lower() or "error" in sent_text.lower()


# ── handle_button_callback ────────────────────────────────────────────────────


async def test_handle_button_callback_yes_answers_query_and_invokes_agent():
    from bot.buttons import handle_button_callback

    habit_id = "abc-123"
    mock_graph = AsyncMock()
    mock_graph.ainvoke.return_value = {"messages": [MagicMock(content="Logged!")]}
    update = _make_callback_update(
        chat_id=42, callback_data=f"habit_log:{habit_id}:yes"
    )
    context = _make_context(mock_graph)

    with patch("bot.buttons.sender") as mock_sender:
        mock_sender.send_message = AsyncMock()
        await handle_button_callback(update, context)

    update.callback_query.answer.assert_called_once()
    mock_graph.ainvoke.assert_called_once()
    call_state = mock_graph.ainvoke.call_args[0][0]
    assert habit_id in call_state["messages"][0].content


async def test_handle_button_callback_no_answers_query_without_agent_call():
    from bot.buttons import handle_button_callback

    habit_id = "abc-123"
    mock_graph = AsyncMock()
    update = _make_callback_update(chat_id=42, callback_data=f"habit_log:{habit_id}:no")
    context = _make_context(mock_graph)

    with patch("bot.buttons.sender") as mock_sender:
        mock_sender.send_message = AsyncMock()
        await handle_button_callback(update, context)

    update.callback_query.answer.assert_called_once()
    mock_graph.ainvoke.assert_not_called()
    mock_sender.send_message.assert_called_once()


async def test_handle_button_callback_malformed_data_sends_error_without_crash():
    from bot.buttons import handle_button_callback

    mock_graph = AsyncMock()
    update = _make_callback_update(chat_id=42, callback_data="bad_format")
    context = _make_context(mock_graph)

    with patch("bot.buttons.sender") as mock_sender:
        mock_sender.send_message = AsyncMock()
        await handle_button_callback(update, context)

    update.callback_query.answer.assert_called_once()
    mock_graph.ainvoke.assert_not_called()
    mock_sender.send_message.assert_called_once()
