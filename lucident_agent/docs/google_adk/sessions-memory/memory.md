# Memory

`MemoryService` provides long-term knowledge for agents, enabling recall of information from past conversations or external sources.

## The MemoryService Role
- Stores and retrieves knowledge beyond a single session
- Used for cross-session recall, knowledge base integration, and persistent facts

## Implementations
- **InMemoryMemoryService**: Stores memory in RAM (not persistent)
- **DatabaseMemoryService**: Persists memory in a database
- **VertexAiMemoryService**: Uses Google Cloud Vertex AI for scalable, managed memory

## How Memory Works
- Add knowledge to memory (e.g., facts, summaries, user info)
- Search memory for relevant info during agent runs
- Memory is separate from session state/history

## Example: Adding and Searching Memory
```python
from google.adk.memory import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai.types import Content, Part

memory_service = InMemoryMemoryService()
session_service = InMemorySessionService()
runner = Runner(agent=agent, app_name="my_app", session_service=session_service, memory_service=memory_service)

# Add a session's content to memory
done_session = ... # completed Session object
memory_service.add_session_to_memory(done_session)

# Search memory in a new session
for event in runner.run(user_id="user1", session_id="session2", new_message=Content(parts=[Part(text="Recall info")])):
    ...
```

[Source](https://google.github.io/adk-docs/sessions/memory/) 