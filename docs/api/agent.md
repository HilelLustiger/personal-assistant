# Module: orchestrator/agent

## Public Interface

| Name | Parameters | Returns | Description |
|---|---|---|---|
| `build_graph(checkpointer?)` | `checkpointer: BaseCheckpointSaver \| None` | compiled `StateGraph` | Constructs and compiles the graph; no checkpointer = no persistence (tests only) |
| `ConversationState` | — | `TypedDict` | `messages: Annotated[list[BaseMessage], add_messages]` — single field |
| `call_model(state)` | `state: ConversationState` | `dict` | Calls LiteLLM with full history + tool schemas; returns new `AIMessage` |
| `call_tools(state)` | `state: ConversationState` | `dict` | Executes tool calls from last `AIMessage` sequentially; returns one `ToolMessage` per call |

## Usage

```python
graph = build_graph(checkpointer)
result = await graph.ainvoke(
    {"messages": [HumanMessage(content="...")]},
    config={"configurable": {"thread_id": chat_id}},
)
reply = result["messages"][-1].content
```
