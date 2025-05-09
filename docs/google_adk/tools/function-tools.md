# Function Tools

Function tools let you add custom logic to agents by wrapping Python functions as tools. Useful for connecting to APIs, databases, or implementing custom algorithms.

## Types
1. **Function Tool**: Wraps a standard function. Params must be JSON-serializable. Return a dict for best results; non-dict returns are wrapped as `{ "result": ... }`.
2. **Long Running Function Tool**: For generator functions that yield progress updates and return a final result. Use `LongRunningFunctionTool`.
3. **Agent-as-a-Tool**: Use another agent as a callable tool via `AgentTool`.

## Function Tool Example
```python
def get_stock_price(symbol: str) -> dict:
    """Get current stock price for a symbol."""
    ...
    return {"status": "success", "price": 123.45}

agent = Agent(..., tools=[get_stock_price])
```

## Long Running Function Tool Example
```python
from google.adk.tools import LongRunningFunctionTool

def process_file(file_path: str):
    yield {"status": "pending", "progress": "50%"}
    ...
    return {"status": "completed", "result": "done"}

long_tool = LongRunningFunctionTool(func=process_file)
```

## Agent-as-a-Tool Example
```python
from google.adk.tools.agent_tool import AgentTool
agent = Agent(...)
root_agent = Agent(..., tools=[AgentTool(agent=agent)])
```

## Best Practices
- Use simple, descriptive names and parameter types
- Return dicts with "status" and clear keys
- Write clear docstrings (used as tool description)

[Source](https://google.github.io/adk-docs/tools/function-tools/) 