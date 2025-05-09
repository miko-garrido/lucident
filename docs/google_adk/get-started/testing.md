# Testing

Test your agent using the ADK CLI:

```sh
adk run my_agent
```

You can also write unit tests for your tools and agent logic using pytest or unittest. Example:

```python
def test_hello_tool():
    from agent import hello_tool
    result = hello_tool()
    assert result["message"] == "Hello from ADK!"
```

Automated tests help ensure your agent behaves as expected. 