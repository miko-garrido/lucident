# Evaluate

Agent evaluation in ADK goes beyond simple pass/fail tests. Because LLM agents are probabilistic, you must assess both the final output and the agent's trajectory (the sequence of steps and tool uses).

## Why Evaluate?
- Traditional tests are not enough for LLM agents due to variability.
- Evaluation covers both the quality of the final response and the reasoning process.
- Automated evaluation is essential for moving from prototype to production.

## What to Evaluate
- **Trajectory & Tool Use:** Did the agent take the right steps and use the right tools?
- **Final Response:** Is the output correct, relevant, and high quality?

## Evaluation Methods
- **Test Files:** Simple, unit-test-like files for single sessions or turns. Each test includes user query, expected tool use, intermediate responses, and reference output.
- **Evalset Files:** Larger datasets for integration tests, supporting multi-turn, complex sessions. Each eval has a name, turns, and initial session state.

## Metrics
- `tool_trajectory_avg_score`: Measures how closely the agent's tool usage matches the expected sequence.
- `response_match_score`: Measures similarity of the agent's final response to the reference (using ROUGE or similar).

## How to Run Evaluation
- **Web UI (`adk web`):** Interactive evaluation and dataset creation.
- **Programmatic (`pytest`):** Integrate with CI/CD and run as part of test suites.
- **CLI (`adk eval`):** Run eval sets from the command line for automation.

## Best Practices
- Define clear success criteria and metrics before evaluating.
- Use test files for fast iteration, evalsets for complex scenarios.
- Integrate evaluation into your development workflow.

Evaluation ensures your agents are reliable, effective, and ready for real-world use. 