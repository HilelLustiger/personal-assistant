from telegram import InlineKeyboardMarkup

_bot = None


def set_bot(bot) -> None:
    global _bot
    _bot = bot


async def send_message(chat_id: str, text: str) -> None:
    await _bot.send_message(chat_id=chat_id, text=text)


async def send_message_with_buttons(
    chat_id: str,
    text: str,
    buttons: list,
) -> None:
    markup = InlineKeyboardMarkup(buttons)
    await _bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)
