# State

`session.state` is a per-session scratchpad for dynamic, serializable data needed during a conversation.

## What is session.state?
- Dictionary of key-value pairs (keys: str, values: serializable types)
- Used for personalization, task progress, flags, and accumulating info
- Avoid storing complex objects

## Key Characteristics
- **Serializable**: Only store basic types (str, int, float, bool, lists/dicts of these)
- **Mutable**: Changes as conversation progresses
- **Persistence**: Depends on SessionService (in-memory: not persistent, database/VertexAI: persistent)

## Prefixes and Scope
- No prefix: Session-specific
- `user:` prefix: Shared across all sessions for a user
- `app:` prefix: Shared across all users/sessions for the app
- `temp:` prefix: Temporary, never persisted

## Updating State
- Always update state via `session_service.append_event()`
- Use `output_key` in agent config for simple updates
- Use `EventActions.state_delta` for complex/multi-key updates

### Example: output_key
```python
from google.adk.agents import LlmAgent
# ...
greeting_agent = LlmAgent(
    name="Greeter",
    model="gemini-2.0-flash",
    instruction="Generate a greeting.",
    output_key="last_greeting"
)
```

### Example: EventActions.state_delta
```python
from google.adk.events import Event, EventActions
state_changes = {"task_status": "active", "user:login_count": 1}
actions = EventActions(state_delta=state_changes)
event = Event(invocation_id="id", author="system", actions=actions)
session_service.append_event(session, event)
```

## Warning: Do Not Modify State Directly
- Direct changes (`session.state['key'] = value`) are not persisted or tracked
- Always use append_event for updates

## Best Practices
- Store only essential, serializable data
- Use clear keys and prefixes
- Update via append_event

[Source](https://google.github.io/adk-docs/sessions/state/) 