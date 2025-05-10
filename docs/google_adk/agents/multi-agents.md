# Multi-Agent Systems

Multi-agent systems in ADK enable complex workflows by composing multiple agents that can delegate, collaborate, or compete.

## Key Concepts
- **Agent Delegation:** Agents can call other agents as tools (AgentTool), enabling modular, hierarchical workflows.
- **Global Instructions:** Use `global_instruction` to set system-wide behavior for all agents.
- **Transfer Control:** Control agent-to-agent transfer with `disallow_transfer_to_parent` and `disallow_transfer_to_peers`.
- **Planning:** Use a `planner` for advanced multi-step reasoning and task assignment.

## Example
```python
from google.adk.agents import LlmAgent, AgentTool

child_agent = LlmAgent(name="child", model="gemini-2.0-flash", instruction="...")
parent_agent = LlmAgent(
    name="parent",
    model="gemini-2.0-flash",
    instruction="...",
    tools=[AgentTool(child_agent)]
)
```

See the [official docs](https://google.github.io/adk-docs/agents/multi-agents/) for more. 