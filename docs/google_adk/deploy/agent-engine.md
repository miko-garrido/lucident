# Agent Engine

Agent Engine is a fully managed Google Cloud service for deploying, managing, and scaling AI agents in production. It handles infrastructure so you can focus on building intelligent applications.

## Install Vertex AI SDK

Agent Engine is part of the Vertex AI SDK for Python.

```sh
pip install google-cloud-aiplatform[adk,agent_engines]
```

*Python >=3.9 and <=3.12 required.*

## Initialization

```python
import vertexai

PROJECT_ID = "your-project-id"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://your-google-cloud-storage-bucket"

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=STAGING_BUCKET,
)
```

## Create Your Agent

```python
import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent

def get_weather(city: str) -> dict:
    if city.lower() == "new york":
        return {"status": "success", "report": "The weather in New York is sunny with a temperature of 25 degrees Celsius (77 degrees Fahrenheit)."}
    else:
        return {"status": "error", "error_message": f"Weather information for '{city}' is not available."}

def get_current_time(city: str) -> dict:
    if city.lower() == "new york":
        tz_identifier = "America/New_York"
    else:
        return {"status": "error", "error_message": f"Sorry, I don't have timezone information for {city}."}
    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    report = f'The current time in {city} is {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}'
    return {"status": "success", "report": report}

root_agent = Agent(
    name="weather_time_agent",
    model="gemini-2.0-flash",
    description="Agent to answer questions about the time and weather in a city.",
    instruction="You are a helpful agent who can answer user questions about the time and weather in a city.",
    tools=[get_weather, get_current_time],
)
```

## Prepare Agent for Agent Engine

```python
from vertexai.preview import reasoning_engines

app = reasoning_engines.AdkApp(
    agent=root_agent,
    enable_tracing=True,
)
```

## Try Locally

```python
session = app.create_session(user_id="u_123")
app.list_sessions(user_id="u_123")
session = app.get_session(user_id="u_123", session_id=session.id)
for event in app.stream_query(user_id="u_123", session_id=session.id, message="whats the weather in new york"):
    print(event)
```

## Deploy to Agent Engine

```python
from vertexai import agent_engines

remote_app = agent_engines.create(
    agent_engine=root_agent,
    requirements=["google-cloud-aiplatform[adk,agent_engines]"]
)
```

Get the resource name:

```python
remote_app.resource_name
# 'projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{RESOURCE_ID}'
```

## Try on Agent Engine

```python
remote_session = remote_app.create_session(user_id="u_456")
remote_app.list_sessions(user_id="u_456")
remote_app.get_session(user_id="u_456", session_id=remote_session["id"])
for event in remote_app.stream_query(user_id="u_456", session_id=remote_session["id"], message="whats the weather in new york"):
    print(event)
```

## Clean Up

```python
remote_app.delete(force=True)
```

*force=True deletes all child resources.*

[Source](https://google.github.io/adk-docs/deploy/agent-engine/) 