# Models

ADK supports multiple LLMs for agents. Choose the right model for your use case based on capability, cost, and integration.

## Supported Models
- **Gemini:** Google's flagship LLM, supports text, code, and multimodal tasks.
- **OpenAI GPT:** Use GPT-3.5, GPT-4, etc. via LiteLLM integration.
- **Anthropic Claude:** Supported via LiteLLM.
- **Custom Models:** Integrate other models using the ADK API.

## Model Selection
- Specify the model string (e.g., "gemini-2.0-flash") in your agent config.
- Consider latency, cost, and feature support (e.g., streaming, multimodal).

## Configuration Example
```python
agent = LlmAgent(
    name="my_agent",
    model="gemini-2.0-flash",
    instruction="..."
)
```

See the [official docs](https://google.github.io/adk-docs/agents/models/) for more details and model options. 