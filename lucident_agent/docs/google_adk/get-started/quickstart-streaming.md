# Quickstart (Streaming)

This guide shows how to create an agent with ADK Streaming for real-time voice and video.

## Supported Models
Use Gemini models that support the Live API (see Google AI Studio or Vertex AI docs for model IDs).

## 1. Setup Environment & Install ADK
```sh
python -m venv .venv
source .venv/bin/activate
pip install google-adk
```

## 2. Project Structure
```
adk-streaming/
└── app/
    ├── .env
    └── google_search_agent/
        ├── __init__.py
        └── agent.py
```

### agent.py
```python
from google.adk.agents import Agent
from google.adk.tools import built_in_google_search

root_agent = Agent(
   name="basic_search_agent",
   model="gemini-2.0-flash-exp",
   description="Agent to answer questions using Google Search.",
   instruction="You are an expert researcher. You always stick to the facts.",
   tools=[built_in_google_search]
)
```

### __init__.py
```python
from . import agent
```

## 3. Set up the Platform
- For Google AI Studio: set `.env` with your API key:
  ```
  GOOGLE_GENAI_USE_VERTEXAI=FALSE
  GOOGLE_API_KEY=PASTE_YOUR_ACTUAL_API_KEY_HERE
  ```
- For Vertex AI: set `.env` with your project info:
  ```
  GOOGLE_GENAI_USE_VERTEXAI=TRUE
  GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
  GOOGLE_CLOUD_LOCATION=us-central1
  ```

## 4. Try the Agent with `adk web`
```sh
cd app
export SSL_CERT_FILE=$(python -m certifi)
adk web
```
Open the provided URL and select `google_search_agent`.

- Try with text: type questions in the UI.
- Try with voice: enable the microphone and ask questions.
- Try with video: enable the camera and ask "What do you see?"

Stop with Ctrl-C.

## 5. Build a Custom Streaming App (Optional)
See the official docs for FastAPI and WebSocket integration for advanced streaming apps.

## 6. Interact with Your Streaming App
- Start FastAPI: `uvicorn main:app --reload`
- Access the UI at the provided URL.

You now have a streaming agent with real-time, bidirectional communication. 