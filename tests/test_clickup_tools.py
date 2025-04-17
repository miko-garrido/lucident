import pytest
from unittest.mock import patch, MagicMock
import os
from dotenv import load_dotenv

# Assuming clickup_tools.py is in harpy_agent/tools/
# Adjust the import path based on your project structure and how you run tests
from harpy_agent.tools import clickup_tools

# Load environment variables for testing (e.g., a dummy API key if needed)
# You might want a separate .env.test file
# load_dotenv() 
# os.environ["CLICKUP_API_KEY"] = "dummy_key_for_testing" # Ensure API key is set for ClickUpAPI init


@pytest.fixture(autouse=True)
def mock_env_api_key(monkeypatch):
    """Ensure CLICKUP_API_KEY is set for tests, preventing init errors."""
    monkeypatch.setenv("CLICKUP_API_KEY", "dummy_test_key")

# Example Test for get_clickup_tasks
@patch('harpy_agent.tools.clickup_tools.requests.get')
def test_get_clickup_tasks_success(mock_get):
    """Test get_clickup_tasks successfully retrieves tasks."""
    # Arrange
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"tasks": [{"id": "task1", "name": "Test Task"}]}
    mock_get.return_value = mock_response
    
    list_id = "test_list_123"
    
    # Act
    tasks = clickup_tools.get_clickup_tasks(list_id=list_id, days=7)
    
    # Assert
    assert tasks == [{"id": "task1", "name": "Test Task"}]
    mock_get.assert_called_once()
    # Add more specific assertions about the URL and params if needed
    call_args, call_kwargs = mock_get.call_args
    assert f"/list/{list_id}/task" in call_args[0]
    assert "params" in call_kwargs
    assert "date_updated_gt" in call_kwargs["params"]

@patch('harpy_agent.tools.clickup_tools.requests.get')
def test_get_clickup_tasks_api_error(mock_get):
    """Test get_clickup_tasks handles API request errors."""
    # Arrange
    mock_get.side_effect = clickup_tools.requests.exceptions.RequestException("API Error")
    
    list_id = "test_list_456"
    
    # Act
    tasks = clickup_tools.get_clickup_tasks(list_id=list_id)
    
    # Assert
    assert tasks == [] # Should return empty list on error
    mock_get.assert_called_once()

# --- Add more tests for other functions here ---

# Example structure for testing class methods if needed
# @patch('harpy_agent.tools.clickup_tools.requests.get')
# def test_clickup_api_get_user_id(mock_get, monkeypatch):
#     monkeypatch.setenv("CLICKUP_API_KEY", "dummy_test_key")
#     api = clickup_tools.ClickUpAPI() 
#     # ... setup mock_get response for /team endpoint ...
#     user_id = api._get_user_id("testuser")
#     # ... assertions ... 