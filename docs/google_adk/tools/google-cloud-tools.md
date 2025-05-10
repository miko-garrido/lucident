# Google Cloud Tools

ADK provides tools for integrating with Google Cloud services, enabling agents to access cloud resources and APIs.

## Examples
- Vertex AI (model inference, data)
- Google Cloud Storage (file access)
- BigQuery (data queries)

## Usage
Import and add Google Cloud tools to your agent:
```python
from google.adk.tools import google_cloud_tools
agent = Agent(..., tools=[google_cloud_tools.vertex_ai, google_cloud_tools.bigquery])
```

See the official docs for setup, authentication, and available tools.

[Source](https://google.github.io/adk-docs/tools/google-cloud-tools/) 