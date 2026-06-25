from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ConversationState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    thread_id: str
    reply: str
