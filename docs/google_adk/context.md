# Context

In ADK, "context" is the bundle of information available to agents and tools during operations. It provides the background knowledge and resources needed to handle a task or conversation turn.

## Why Context Matters
- **Maintains State:** Remembers details across steps (user preferences, workflow progress) via session state.
- **Passes Data:** Shares info between steps using session state.
- **Accesses Services:** Interacts with artifact storage, memory, authentication, etc.
- **Identity/Tracking:** Knows which agent is running and tracks invocation for logging/debugging.
- **Tool Actions:** Enables tools to request authentication, search memory, and more.

## Types of Context
- **InvocationContext:** Full context for an agent's core logic. Access to session, state, events, agent, invocation_id, services, and user input.
- **ReadonlyContext:** Read-only view for scenarios where mutation is not allowed (e.g., instruction providers).
- **CallbackContext:** Used in agent/model callbacks. Allows reading/writing state, loading/saving artifacts, and accessing user input.
- **ToolContext:** Used in tools/tool-callbacks. Adds authentication methods, artifact listing, memory search, function_call_id, and actions.

## Common Tasks
- **Access State:** `context.state['key']` to read/write data.
- **Get Identifiers:** `context.agent_name`, `context.invocation_id`, `context.function_call_id` (ToolContext).
- **Access User Input:** `context.user_content` for the initial message.
- **Manage Artifacts:** `context.save_artifact(filename, part)`, `context.load_artifact(filename)`, `context.list_artifacts()`.
- **Handle Auth:** `context.request_credential(auth_config)`, `context.get_auth_response(auth_config)`.
- **Search Memory:** `context.search_memory(query)`.
- **Control Flow:** Set `ctx.end_invocation = True` in InvocationContext to stop execution.

## Best Practices
- Use the most specific context object provided.
- Use `context.state` for data flow and memory.
- Use artifacts for files and large data.
- Changes to state/artifacts are tracked and persisted automatically.
- Start simple with state and artifacts; use advanced features as needed.

Context is essential for building stateful, capable agents in ADK. 