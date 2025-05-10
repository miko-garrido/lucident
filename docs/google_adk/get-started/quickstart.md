# Quickstart

This quickstart guides you through installing ADK, creating a basic agent with tools, and running it locally.

## 1. Set up Environment & Install ADK

Create and activate a virtual environment:
```sh
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows CMD: .venv\Scripts\activate.bat
# Windows PowerShell: .venv\Scripts\Activate.ps1
```
Install ADK:
```sh
pip install google-adk
```

## 2. Create Agent Project

Project structure:
```
parent_folder/
    multi_tool_agent/
        __init__.py
        agent.py
        .env
```

Create the folder and files:
```sh
mkdir multi_tool_agent
cd multi_tool_agent
# Create __init__.py, agent.py, .env
```

### __init__.py
```python
from . import agent
```

### agent.py
```python
import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent

def get_weather(city: str) -> dict:
    if city.lower() == "new york":
        return {
            "status": "success",
            "report": "The weather in New York is sunny with a temperature of 25°C (77°F)."
        }
    else:
        return {
            "status": "error",
            "error_message": f"Weather information for '{city}' is not available."
        }

def get_current_time(city: str) -> dict:
    if city.lower() == "new york":
        tz_identifier = "America/New_York"
    else:
        return {
            "status": "error",
            "error_message": f"Sorry, I don't have timezone information for {city}."
        }
    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    report = f"The current time in {city} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"
    return {"status": "success", "report": report}

root_agent = Agent(
    name="weather_time_agent",
    model="gemini-2.0-flash",
    description="Agent to answer questions about the time and weather in a city.",
    instruction="You are a helpful agent who can answer user questions about the time and weather in a city.",
    tools=[get_weather, get_current_time],
)
```

### .env
For Gemini via Google AI Studio:
```
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=PASTE_YOUR_ACTUAL_API_KEY_HERE
```
For Gemini via Vertex AI:
```
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_CLOUD_LOCATION=LOCATION
```

## 3. Run Your Agent

Navigate to the parent directory and launch the dev UI:
```sh
adk web
```
Open the provided URL (usually http://localhost:8000), select `multi_tool_agent`, and chat with your agent.

To use the CLI:
```sh
adk run multi_tool_agent
```

### Example prompts
- What is the weather in New York?
- What is the time in New York?
- What is the weather in Paris?
- What is the time in Paris?

You have now created and run your first ADK agent. 