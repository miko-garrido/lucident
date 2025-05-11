# Built-in Tools

ADK provides built-in tools for common tasks, ready to use with agents. These tools cover basic utilities, search, math, and more.

## Examples
- **Search tools**: Web search, Wikipedia lookup
- **Math tools**: Calculator, unit conversion
- **Date/time tools**: Current time, date formatting
- **String tools**: Manipulation, parsing

## Usage
Add built-in tools to your agent's `tools` list:
```python
from google.adk.tools import builtins
agent = Agent(..., tools=[builtins.search, builtins.calculator])
```

See the official docs for the full list and details.

[Source](https://google.github.io/adk-docs/tools/built-in-tools/) 