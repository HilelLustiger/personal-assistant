"""LangGraph StateGraph for the personal assistant agent."""
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from agent.nodes import call_model, call_tools, format_response
from agent.state import ConversationState


def _router(state: ConversationState) -> str:
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "call_tools"
    return "format_response"


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    builder = StateGraph(ConversationState)

    builder.add_node("call_model", call_model)
    builder.add_node("call_tools", call_tools)
    builder.add_node("format_response", format_response)

    builder.set_entry_point("call_model")
    builder.add_conditional_edges(
        "call_model",
        _router,
        {"call_tools": "call_tools", "format_response": "format_response"},
    )
    builder.add_edge("call_tools", "call_model")
    builder.add_edge("format_response", END)

    return builder.compile(checkpointer=checkpointer)
