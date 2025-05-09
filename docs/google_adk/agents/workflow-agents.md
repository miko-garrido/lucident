# Workflow Agents

Workflow agents in ADK orchestrate other agents or tools in a deterministic sequence, loop, or parallel pattern.

## Types
- **SequentialAgent:** Runs agents/tools in a fixed order.
- **LoopAgent:** Repeats an agent/tool until a condition is met.
- **ParallelAgent:** Runs multiple agents/tools concurrently and aggregates results.

## Use Cases
- Pipelines with clear, repeatable steps
- Batch processing or iterative tasks
- Combining results from multiple sources

## Configuration Example
```python
from google.adk.agents import SequentialAgent

seq_agent = SequentialAgent(
    name="pipeline_agent",
    steps=[agent1, agent2, tool1],
    description="Runs a multi-step pipeline."
)
```

See the [official docs](https://google.github.io/adk-docs/agents/workflow-agents/) for more details. 