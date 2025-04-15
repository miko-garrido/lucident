from typing import List, Dict, Any, Optional
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ClickUpAPI:
    def __init__(self):
        self.api_key = os.getenv("CLICKUP_API_KEY")
        if not self.api_key:
            raise ValueError("CLICKUP_API_KEY not found in environment variables")
            
        self.base_url = "https://api.clickup.com/api/v2"
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }

    def _get_user_id(self, username: str) -> Optional[str]:
        """Helper method to get user ID from username (used by get_clickup_user_tasks)"""
        response = requests.get(
            f"{self.base_url}/team",
            headers=self.headers
        )
        teams = response.json()["teams"]
        
        for team in teams:
            members = team.get("members", [])
            for member in members:
                user = member.get("user", {})
                if user and user.get("username") and user["username"].lower() == username.lower():
                    return user["id"]
        return None

# --- Standalone Function Tools ---

def get_clickup_tasks(list_id: str, days: int = 7) -> List[Dict[str, Any]]:
    """
    ADK Tool: Get tasks from a specific ClickUp list updated in the last N days.
    
    Args:
        list_id: The ID of the ClickUp list.
        days: Number of past days to filter tasks by update date (default: 7).

    Returns:
        A list of task dictionaries.
    """
    api = ClickUpAPI()
    return api.get_tasks(list_id, days)

def get_clickup_task_details(task_id: str) -> Dict[str, Any]:
    """
    ADK Tool: Get detailed information about a specific ClickUp task.

    Args:
        task_id: The ID of the ClickUp task.

    Returns:
        A dictionary containing task details.
    """
    api = ClickUpAPI()
    return api.get_task_details(task_id)

def get_clickup_comments(task_id: str) -> List[Dict[str, Any]]:
    """
    ADK Tool: Get all comments associated with a ClickUp task.

    Args:
        task_id: The ID of the ClickUp task.

    Returns:
        A list of comment dictionaries.
    """
    api = ClickUpAPI()
    return api.get_comments(task_id)

def get_clickup_user_tasks(username: str, days: int = 7) -> List[Dict[str, Any]]:
    """
    ADK Tool: Get tasks assigned to a specific ClickUp user updated in the last N days.

    Args:
        username: The username of the ClickUp user.
        days: Number of past days to filter tasks by update date (default: 7).

    Returns:
        A list of task dictionaries assigned to the user.
    """
    api = ClickUpAPI()
    return api.get_user_tasks(username, days)

def get_clickup_time_entries(team_id: str, task_id: Optional[str] = None, user_id: Optional[str] = None,
                           start_date: Optional[int] = None, end_date: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    ADK Tool: Get ClickUp time entries with optional filters.

    Args:
        team_id: The ID of the ClickUp team/workspace (required).
        task_id: Optional ID of the task to filter entries for.
        user_id: Optional ID of the user to filter entries for.
        start_date: Optional start date (Unix timestamp) for filtering.
        end_date: Optional end date (Unix timestamp) for filtering.

    Returns:
        A list of time entry dictionaries.
    """
    api = ClickUpAPI()
    # Note: team_id is required by the underlying API method call structure here
    return api.get_time_entries(task_id=task_id, user_id=user_id, team_id=team_id, 
                                start_date=start_date, end_date=end_date)

def create_clickup_task(list_id: str, name: str, description: Optional[str] = None, 
                      assignees: Optional[List[int]] = None, status: Optional[str] = None,
                      priority: Optional[int] = None, due_date: Optional[int] = None,
                      tags: Optional[List[str]] = None, custom_fields: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """
    ADK Tool: Create a new task in a specific ClickUp list.

    Args:
        list_id: The ID of the target ClickUp list.
        name: The name of the new task.
        description: Optional description for the task.
        assignees: Optional list of user IDs to assign.
        status: Optional status for the task.
        priority: Optional priority level (1-4).
        due_date: Optional due date (Unix timestamp).
        tags: Optional list of tags.
        custom_fields: Optional list of custom field dictionaries.

    Returns:
        A dictionary representing the created task.
    """
    api = ClickUpAPI()
    kwargs = {k: v for k, v in locals().items() if k not in ['api', 'list_id', 'name'] and v is not None}
    return api.create_task(list_id=list_id, name=name, **kwargs)

def update_clickup_task(task_id: str, name: Optional[str] = None, description: Optional[str] = None, 
                      assignees: Optional[List[int]] = None, status: Optional[str] = None,
                      priority: Optional[int] = None, due_date: Optional[int] = None,
                      tags: Optional[List[str]] = None, custom_fields: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """
    ADK Tool: Update an existing ClickUp task.

    Args:
        task_id: The ID of the task to update.
        name: Optional new name for the task.
        description: Optional new description.
        assignees: Optional new list of assignees.
        status: Optional new status.
        priority: Optional new priority level.
        due_date: Optional new due date.
        tags: Optional new list of tags.
        custom_fields: Optional new list of custom fields.

    Returns:
        A dictionary representing the updated task.
    """
    api = ClickUpAPI()
    kwargs = {k: v for k, v in locals().items() if k not in ['api', 'task_id'] and v is not None}
    return api.update_task(task_id=task_id, **kwargs)

def delete_clickup_task(task_id: str) -> None:
    """
    ADK Tool: Delete a ClickUp task.

    Args:
        task_id: The ID of the task to delete.
    """
    api = ClickUpAPI()
    api.delete_task(task_id)
    return None

def create_clickup_comment(task_id: str, comment_text: str) -> Dict[str, Any]:
    """
    ADK Tool: Create a comment on a ClickUp task.

    Args:
        task_id: The ID of the task to comment on.
        comment_text: The text content of the comment.

    Returns:
        A dictionary representing the created comment.
    """
    api = ClickUpAPI()
    return api.create_comment(task_id, comment_text)

def update_clickup_comment(comment_id: str, comment_text: str) -> Dict[str, Any]:
    """
    ADK Tool: Update an existing ClickUp comment.

    Args:
        comment_id: The ID of the comment to update.
        comment_text: The new text content for the comment.

    Returns:
        A dictionary representing the updated comment.
    """
    api = ClickUpAPI()
    return api.update_comment(comment_id, comment_text)

def delete_clickup_comment(comment_id: str) -> None:
    """
    ADK Tool: Delete a ClickUp comment.

    Args:
        comment_id: The ID of the comment to delete.
    """
    api = ClickUpAPI()
    api.delete_comment(comment_id)
    return None

def set_clickup_custom_fields(task_id: str, custom_fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    ADK Tool: Update custom fields for a ClickUp task.

    Args:
        task_id: The ID of the task to update.
        custom_fields: A list of custom field dictionaries, e.g., 
                       [{"id": "field_id", "value": "field_value"}, ...].

    Returns:
        A dictionary representing the task after the update.
    """
    api = ClickUpAPI()
    return api.set_custom_fields(task_id, custom_fields)

def get_clickup_list_members(list_id: str) -> List[Dict[str, Any]]:
    """
    ADK Tool: Get members who have access to a specific ClickUp list.

    Args:
        list_id: The ID of the ClickUp list.

    Returns:
        A list of member dictionaries.
    """
    api = ClickUpAPI()
    return api.get_list_members(list_id)

def get_clickup_task_members(task_id: str) -> List[Dict[str, Any]]:
    """
    ADK Tool: Get members who have access to a specific ClickUp task.

    Args:
        task_id: The ID of the ClickUp task.

    Returns:
        A list of member dictionaries.
    """
    api = ClickUpAPI()
    return api.get_task_members(task_id)

def get_clickup_subtasks(task_id: str) -> List[Dict[str, Any]]:
    """
    ADK Tool: Get subtasks of a specific ClickUp task.

    Args:
        task_id: The ID of the parent ClickUp task.

    Returns:
        A list of subtask dictionaries.
    """
    api = ClickUpAPI()
    return api.get_subtasks(task_id)

def create_clickup_subtask(parent_task_id: str, name: str, **kwargs) -> Dict[str, Any]:
    """
    ADK Tool: Create a subtask under a parent ClickUp task.
    Accepts the same optional arguments as create_clickup_task.

    Args:
        parent_task_id: The ID of the parent task.
        name: The name of the new subtask.
        **kwargs: Optional arguments like description, assignees, status, etc.

    Returns:
        A dictionary representing the created subtask.
    """
    api = ClickUpAPI()
    return api.create_subtask(parent_task_id=parent_task_id, name=name, **kwargs)

def get_clickup_teams() -> List[Dict[str, Any]]:
    """
    ADK Tool: Get all ClickUp teams/workspaces the API key has access to.

    Returns:
        A list of team/workspace dictionaries.
    """
    api = ClickUpAPI()
    return api.get_teams()

def get_clickup_team_members(team_id: str) -> List[Dict[str, Any]]:
    """
    ADK Tool: Get all members in a specific ClickUp team/workspace.

    Args:
        team_id: The ID of the ClickUp team/workspace.

    Returns:
        A list of member dictionaries.
    """
    api = ClickUpAPI()
    return api.get_team_members(team_id)

def get_clickup_spaces(team_id: str) -> List[Dict[str, Any]]:
    """
    ADK Tool: Get all spaces within a specific ClickUp team/workspace.

    Args:
        team_id: The ID of the ClickUp team/workspace.

    Returns:
        A list of space dictionaries.
    """
    api = ClickUpAPI()
    return api.get_spaces(team_id)

def get_clickup_folders(space_id: str) -> List[Dict[str, Any]]:
    """
    ADK Tool: Get all folders (projects) within a specific ClickUp space.

    Args:
        space_id: The ID of the ClickUp space.

    Returns:
        A list of folder dictionaries.
    """
    api = ClickUpAPI()
    return api.get_folders(space_id) 