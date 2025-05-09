# Custom Agents

Custom agents in ADK let you define unique logic by subclassing `BaseAgent`.

## When to Use
- You need agent behavior not covered by LLM or workflow agents.
- You want to integrate with external systems or APIs in a custom way.

## How to Create
1. Subclass `BaseAgent`.
2. Implement `_run_async_impl` (core logic) or `_run_live_impl` (for streaming).
3. Use the provided context, state, and tools as needed.

## Example
```python
from google.adk.agents import BaseAgent

class MyCustomAgent(BaseAgent):
    async def _run_async_impl(self, context):
        # Custom logic here
        return "Custom result"
```

See the [official docs](https://google.github.io/adk-docs/agents/custom-agents/) for more. 