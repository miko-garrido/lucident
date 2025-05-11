# Safety and Security

Building safe, secure agents is critical. ADK and Vertex AI provide multiple layers of protection to reduce risks from misaligned actions, harmful content, and data leaks.

## Risks
- Ambiguous instructions, model hallucination, prompt injection, and tool misuse can cause unsafe or harmful behavior.
- Risks include misalignment, harmful content, unsafe actions (e.g., unauthorized access, data exfiltration).

## Best Practices
### Identity and Authorization
- **Agent-Auth:** Tools act as the agent's identity (e.g., service account). Restrict permissions to only what's needed.
- **User Auth:** Tools act as the user's identity (e.g., OAuth). Ensures agents only do what the user could do.

### Guardrails
- **In-tool guardrails:** Validate tool arguments and context to enforce policies.
- **Gemini Safety Features:** Use built-in content filters and system instructions for safety.
- **Callbacks:** Use before/after tool/model callbacks to validate or block unsafe actions.
- **LLM as Guardrail:** Use a fast LLM (e.g., Gemini Flash Lite) to screen inputs/outputs for safety.

### Sandboxed Code Execution
- Run model-generated code in isolated environments to prevent security issues.

### Evaluation and Tracing
- Use evaluation tools to test agent behavior and tracing to monitor actions.

### Network Controls
- Use VPC-SC and network perimeters to confine agent activity and prevent data leaks.

### UI Safety
- Always escape model-generated content in UIs to prevent XSS or data exfiltration.

Follow these patterns to build trustworthy, robust agents. 