"""LangGraph StateGraph for the personal assistant agent."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from agent.nodes import call_model, call_tools
from agent.state import ConversationState


def _router(state: ConversationState) -> str:
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "call_tools"
    return END


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    builder = StateGraph(ConversationState)

    builder.add_node("call_model", call_model)
    builder.add_node("call_tools", call_tools)

    builder.set_entry_point("call_model")
    builder.add_conditional_edges(
        "call_model",
        _router,
        {"call_tools": "call_tools", END: END},
    )
    builder.add_edge("call_tools", "call_model")

    return builder.compile(checkpointer=checkpointer)
