# LLM Agents

`LlmAgent` is the core ADK agent for reasoning, decision-making, and tool use via a Large Language Model (LLM).

## Identity & Purpose
- `name` (required): Unique agent identifier.
- `description` (optional): Summary of capabilities, used for agent routing.
- `model` (required): LLM model string (e.g., "gemini-2.0-flash").

## Instructions
- `instruction`: String or function guiding agent behavior, persona, constraints, tool use, and output format.
- Use `{var}` or `{artifact.var}` for dynamic values from state/artifacts.

## Tools
- `tools`: List of Python functions, tool classes, or other agents. Enables the agent to perform actions beyond LLM text.

## Advanced Config
- `generate_content_config`: Fine-tune LLM generation.
- `input_schema`, `output_schema`, `output_key`: Structure input/output, enforce formats, and store results in state.
- `include_contents`: Control access to conversation history.
- `planner`, `code_executor`: Enable multi-step reasoning and code execution.

## Example
```python
from google.adk.agents import LlmAgent

def get_capital_city(country: str) -> str:
    capitals = {"france": "Paris", "japan": "Tokyo"}
    return capitals.get(country.lower(), f"Unknown for {country}")

capital_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="capital_agent",
    description="Answers questions about capital cities.",
    instruction="You are an agent that provides the capital city of a country. Use the get_capital_city tool.",
    tools=[get_capital_city]
)
```

See the [official docs](https://google.github.io/adk-docs/agents/llm-agents/) for full details. 