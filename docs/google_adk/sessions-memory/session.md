# Session

A `Session` tracks an individual conversation thread between a user and an agent. It stores context, history, and state for continuity across turns.

## The Session Object
- **id**: Unique session identifier
- **app_name**: Agent application name
- **user_id**: User identifier
- **events**: List of all interaction events (user, agent, tool)
- **state**: Per-session scratchpad for temporary data
- **last_update_time**: Timestamp of last event

### Example: Examining Session Properties
```python
from google.adk.sessions import InMemorySessionService, Session

temp_service = InMemorySessionService()
example_session: Session = temp_service.create_session(
    app_name="my_app",
    user_id="example_user",
    state={"initial_key": "initial_value"}
)

print(example_session.id)
print(example_session.app_name)
print(example_session.user_id)
print(example_session.state)
print(example_session.events)
print(example_session.last_update_time)

temp_service.delete_session(app_name=example_session.app_name, user_id=example_session.user_id, session_id=example_session.id)
```

## Managing Sessions with SessionService
Use a `SessionService` to manage session lifecycle:
- **create_session**: Start a new conversation
- **get_session**: Resume an existing session
- **append_event**: Add events and update state
- **list_sessions**: List active sessions
- **delete_session**: Clean up session data

## SessionService Implementations
- **InMemorySessionService**: Stores sessions in memory (no persistence)
  ```python
  from google.adk.sessions import InMemorySessionService
  session_service = InMemorySessionService()
  ```
- **DatabaseSessionService**: Stores sessions in a database (persistent)
  ```python
  from google.adk.sessions import DatabaseSessionService
  db_url = "sqlite:///./my_agent_data.db"
  session_service = DatabaseSessionService(db_url=db_url)
  ```
- **VertexAiSessionService**: Uses Google Cloud Vertex AI (scalable, managed)
  ```python
  from google.adk.sessions import VertexAiSessionService
  PROJECT_ID = "your-gcp-project-id"
  LOCATION = "us-central1"
  REASONING_ENGINE_APP_NAME = "projects/your-gcp-project-id/locations/us-central1/reasoningEngines/your-engine-id"
  session_service = VertexAiSessionService(project=PROJECT_ID, location=LOCATION)
  # Use REASONING_ENGINE_APP_NAME as app_name
  ```

## Session Lifecycle
1. **Start/Resume**: `create_session` or `get_session`
2. **Context**: Agent receives session object
3. **Process**: Agent uses state/events to generate response
4. **Update**: Agent response and state changes are packaged as an event
5. **Save**: `append_event` updates session history and state
6. **Next Turn**: Session is ready for the next user message
7. **End**: `delete_session` cleans up session data

[Source](https://google.github.io/adk-docs/sessions/session/) 