# Third Party Tools

ADK supports integration with third-party tools and APIs, enabling agents to access external services and data.

## Examples
- External APIs (weather, finance, news)
- SaaS integrations (Slack, Google Drive, etc.)
- Custom connectors

## Usage
Wrap third-party API calls as function tools and add to your agent:
```python
def get_weather(city: str) -> dict:
    # Call external weather API
    ...
    return {"status": "success", "weather": "Sunny"}

agent = Agent(..., tools=[get_weather])
```

See the official docs for more integration patterns and security notes.

[Source](https://google.github.io/adk-docs/tools/third-party-tools/) 