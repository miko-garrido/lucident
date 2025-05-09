# OpenAPI Tools

ADK supports OpenAPI tools, allowing agents to call APIs described by OpenAPI specs.

## Examples
- REST API integration
- Automated endpoint discovery
- Dynamic tool generation from OpenAPI

## Usage
Import and configure OpenAPI tools for your agent:
```python
from google.adk.tools import openapi_tools
agent = Agent(..., tools=[openapi_tools.from_spec("openapi.yaml")])
```

See the official docs for details on supported OpenAPI versions and configuration.

[Source](https://google.github.io/adk-docs/tools/openapi-tools/) 