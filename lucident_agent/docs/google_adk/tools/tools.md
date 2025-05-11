# Tools

A Tool in ADK is a specific capability provided to an agent, usually as a Python function, class method, or another agent. Tools let agents perform actions beyond text generation, such as querying APIs, searching, or executing code.

## How Agents Use Tools
1. LLM reasons about the task
2. Selects a tool and arguments
3. Invokes the tool
4. Observes the result
5. Uses the result for next steps

## Tool Types
- **Function Tools:** Custom Python functions or methods
- **Built-in Tools:** Provided by ADK (e.g., Search, Code Exec)
- **Third-Party Tools:** Integrate with libraries like LangChain
- **Agents-as-Tools:** Use another agent as a tool

## Tool Context
- Access to session state, memory, artifacts, and authentication
- Tools can request additional context or permissions

## Best Practices
- Keep tools stateless and idempotent
- Validate inputs and handle errors
- Use clear, descriptive names and docstrings

See the official docs for advanced tool integration and examples. 