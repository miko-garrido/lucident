# Callback Design Patterns & Best Practices

Callbacks in ADK are powerful for customizing agent behavior. Use these patterns and best practices for robust, maintainable code.

## Patterns
- **Guardrails:** Use before callbacks to validate, block, or modify actions (e.g., restrict tool use, enforce policies).
- **Logging & Monitoring:** Use after callbacks to log inputs, outputs, and errors for observability and debugging.
- **Caching:** Use before tool callbacks to return cached results and skip expensive tool calls.
- **Post-processing:** Use after tool/model callbacks to format, filter, or enrich results before returning to the agent or user.
- **Stateful Control:** Use callbacks to read/write session state, enabling dynamic agent behavior.

## Best Practices
- Keep callbacks fast and side-effect free when possible.
- Avoid heavy computation or blocking I/O in callbacks.
- Use clear, descriptive names and docstrings for callback functions.
- Test callbacks independently.
- Document callback usage and expected context.

See the [official docs](https://google.github.io/adk-docs/callbacks/design-patterns-and-best-practices/) for more examples and advanced usage. 