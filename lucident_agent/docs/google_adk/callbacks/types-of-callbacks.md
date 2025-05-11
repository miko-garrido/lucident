# Types of Callbacks

ADK provides several callback types that trigger at different stages of agent execution. Use these to observe, modify, or control agent and tool behavior.

## Agent Lifecycle Callbacks
- **Before Agent Callback:** Runs before the agent's main logic. Use for setup, validation, logging, or to skip execution based on session state.
- **After Agent Callback:** Runs after the agent completes. Use for cleanup, logging, or post-processing.

## LLM Interaction Callbacks
- **Before Model Callback:** Runs before the LLM is called. Use to inspect/modify the prompt or block the call.
- **After Model Callback:** Runs after the LLM returns. Use to inspect/modify the model's output.

## Tool Execution Callbacks
- **Before Tool Callback:** Runs before a tool is called. Use to inspect/modify arguments, block or override tool execution, or implement caching.
- **After Tool Callback:** Runs after a tool returns. Use to inspect/modify the result, log, or post-process output.

### Example: Before Agent Callback
```python
def before_agent_callback(context):
    if context.state.get("skip_llm_agent"):
        return Content(parts=[Part(text="Agent skipped.")], role="model")
    return None
```

### Example: Before Tool Callback
```python
def before_tool_callback(tool, args, context):
    if args.get("country") == "BLOCK":
        return {"result": "Blocked by callback."}
    return None
```

See the [official docs](https://google.github.io/adk-docs/callbacks/types-of-callbacks/) for full details and code samples. 