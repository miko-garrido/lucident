# MCP Tools

MCP (Multi-Cloud Platform) tools in ADK enable agents to interact with multi-cloud resources and APIs.

## Examples
- Cross-cloud data access
- Multi-cloud orchestration
- Federated queries

## Usage
Import and add MCP tools to your agent:
```python
from google.adk.tools import mcp_tools
agent = Agent(..., tools=[mcp_tools.cross_cloud_query])
```

See the official docs for supported platforms and configuration.

[Source](https://google.github.io/adk-docs/tools/mcp-tools/) 