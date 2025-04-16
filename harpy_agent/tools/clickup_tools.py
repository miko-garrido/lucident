from typing import List, Dict, Any, Optional
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json

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
    Retrieves tasks from a specific ClickUp list that have been updated within the last N days.

    Args:
        list_id (str): The ID of the ClickUp list to fetch tasks from.
        days (int): The number of past days to look back for task updates. Defaults to 7.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary represents a task and its properties. Returns an empty list if no tasks are found or an error occurs.
    """
    api = ClickUpAPI()
    return api.get_tasks(list_id, days)

def get_clickup_task_details(task_id: str) -> Dict[str, Any]:
    """
    Retrieves detailed information about a specific ClickUp task.

    Args:
        task_id (str): The ID of the ClickUp task.

    Returns:
        Dict[str, Any]: A dictionary containing the details of the task (e.g., name, description, status, assignees). Returns an empty dictionary or raises an error if the task is not found.
    """
    api = ClickUpAPI()
    return api.get_task_details(task_id)

def get_clickup_comments(task_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all comments associated with a specific ClickUp task.

    Args:
        task_id (str): The ID of the ClickUp task.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary represents a comment. Returns an empty list if the task has no comments or an error occurs.
    """
    api = ClickUpAPI()
    return api.get_comments(task_id)

def get_clickup_user_tasks(username: str, days: int = 7) -> List[Dict[str, Any]]:
    """
    Retrieves tasks assigned to a specific ClickUp user that have been updated within the last N days.

    Args:
        username (str): The username of the ClickUp user.
        days (int): The number of past days to look back for task updates. Defaults to 7.

    Returns:
        List[Dict[str, Any]]: A list of task dictionaries assigned to the specified user. Returns an empty list if no tasks are found or the user doesn't exist.
    """
    api = ClickUpAPI()
    return api.get_user_tasks(username, days)

def get_clickup_time_entries(team_id: str, task_id: Optional[str] = None, user_id: Optional[str] = None,
                           start_date: Optional[int] = None, end_date: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Retrieves ClickUp time entries, with options to filter by task, user, and date range.

    Args:
        team_id (str): The ID of the ClickUp team/workspace (required).
        task_id (Optional[str]): Filter time entries for this specific task ID.
        user_id (Optional[str]): Filter time entries for this specific user ID.
        start_date (Optional[int]): Filter entries starting from this Unix timestamp.
        end_date (Optional[int]): Filter entries ending at this Unix timestamp.

    Returns:
        List[Dict[str, Any]]: A list of time entry dictionaries matching the filters. Returns an empty list if no entries are found or an error occurs.
    """
    api = ClickUpAPI()
    # Note: team_id is required by the underlying API method call structure here
    return api.get_time_entries(task_id=task_id, user_id=user_id, team_id=team_id, 
                                start_date=start_date, end_date=end_date)

def create_clickup_task(list_id: str, name: str, description: Optional[str] = None,
                      assignees: Optional[List[int]] = None, status: Optional[str] = None,
                      priority: Optional[int] = None, due_date: Optional[int] = None,
                      tags: Optional[List[str]] = None, custom_fields_json: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Creates a new task in a specified ClickUp list.

    Args:
        list_id (str): The ID of the ClickUp list where the task will be created.
        name (str): The name of the new task.
        description (Optional[str]): The description for the task.
        assignees (Optional[List[int]]): A list of user IDs to assign to the task.
        status (Optional[str]): The status to set for the task (e.g., "To Do", "In Progress").
        priority (Optional[int]): The priority level (1=Urgent, 2=High, 3=Normal, 4=Low).
        due_date (Optional[int]): The due date for the task as a Unix timestamp.
        tags (Optional[List[str]]): A list of tag names to apply to the task.
        custom_fields_json (Optional[List[str]]): A list of custom field values as JSON strings. Each string must be a valid JSON object, e.g., '{"id": "field_id", "value": "field_value"}'.

    Returns:
        Dict[str, Any]: A dictionary representing the newly created task. Raises an error if creation fails.
    """
    api = ClickUpAPI()
    # Parse custom_fields_json if provided
    parsed_custom_fields = None
    if custom_fields_json:
        try:
            parsed_custom_fields = [json.loads(cf_str) for cf_str in custom_fields_json]
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in custom_fields_json: {e}")

    # Prepare kwargs, using parsed_custom_fields
    kwargs = {k: v for k, v in locals().items() if k not in ['api', 'list_id', 'name', 'custom_fields_json', 'parsed_custom_fields'] and v is not None}
    if parsed_custom_fields is not None:
        kwargs['custom_fields'] = parsed_custom_fields # Pass the parsed list of dicts

    return api.create_task(list_id=list_id, name=name, **kwargs)

def update_clickup_task(task_id: str, name: Optional[str] = None, description: Optional[str] = None,
                      assignees: Optional[List[int]] = None, status: Optional[str] = None,
                      priority: Optional[int] = None, due_date: Optional[int] = None,
                      tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Updates an existing ClickUp task with new values. Does NOT update custom fields (use set_clickup_custom_fields for that).

    Args:
        task_id (str): The ID of the task to update.
        name (Optional[str]): The new name for the task.
        description (Optional[str]): The new description for the task.
        assignees (Optional[List[int]]): The new list of assignee user IDs.
        status (Optional[str]): The new status for the task.
        priority (Optional[int]): The new priority level.
        due_date (Optional[int]): The new due date (Unix timestamp).
        tags (Optional[List[str]]): The new list of tags.

    Returns:
        Dict[str, Any]: A dictionary representing the updated task. Raises an error if the update fails or the task is not found.
    """
    api = ClickUpAPI()

    # Prepare kwargs
    kwargs = {k: v for k, v in locals().items() if k not in ['api', 'task_id'] and v is not None}

    return api.update_task(task_id=task_id, **kwargs)

def delete_clickup_task(task_id: str) -> Dict[str, Any]:
    """
    Deletes a specific ClickUp task.

    Args:
        task_id (str): The ID of the task to delete.

    Returns:
        Dict[str, Any]: An empty dictionary ({}) upon successful deletion. Raises an error if deletion fails or the task is not found.
    """
    api = ClickUpAPI()
    api.delete_task(task_id)
    # Return empty dict to signify success, as API returns 204 No Content
    return {}

def create_clickup_comment(task_id: str, comment_text: str) -> Dict[str, Any]:
    """
    Adds a comment to a specific ClickUp task.

    Args:
        task_id (str): The ID of the task to add the comment to.
        comment_text (str): The text content of the comment.

    Returns:
        Dict[str, Any]: A dictionary representing the newly created comment. Raises an error if creation fails.
    """
    api = ClickUpAPI()
    return api.create_comment(task_id, comment_text)

def update_clickup_comment(comment_id: str, comment_text: str) -> Dict[str, Any]:
    """
    Updates the text of an existing ClickUp comment.

    Args:
        comment_id (str): The ID of the comment to update.
        comment_text (str): The new text content for the comment.

    Returns:
        Dict[str, Any]: A dictionary representing the updated comment status (often just a success indicator from the API). Raises an error if update fails.
    """
    api = ClickUpAPI()
    return api.update_comment(comment_id, comment_text)

def delete_clickup_comment(comment_id: str) -> Dict[str, Any]:
    """
    Deletes a specific ClickUp comment.

    Args:
        comment_id (str): The ID of the comment to delete.

    Returns:
        Dict[str, Any]: An empty dictionary ({}) upon successful deletion. Raises an error if deletion fails.
    """
    api = ClickUpAPI()
    api.delete_comment(comment_id)
     # Return empty dict to signify success, as API returns 204 No Content
    return {}

def set_clickup_custom_fields(task_id: str, custom_fields_json: List[str]) -> Dict[str, Any]:
    """
    Sets or updates the values of custom fields for a specific ClickUp task.

    Args:
        task_id (str): The ID of the task to update custom fields for.
        custom_fields_json (List[str]): A list of custom field dictionaries as JSON strings to set. Each string must be a valid JSON object with "id" and "value". Example: ['{"id": "abc-123", "value": "New Value"}'].

    Returns:
        Dict[str, Any]: A dictionary representing the task after the custom fields have been updated. Raises an error if the update fails.
    """
    api = ClickUpAPI()
    # Parse custom_fields_json
    parsed_custom_fields = []
    try:
        parsed_custom_fields = [json.loads(cf_str) for cf_str in custom_fields_json]
        # Basic validation (ensure id and value are present)
        for cf in parsed_custom_fields:
            if "id" not in cf or "value" not in cf:
                raise ValueError(f"Custom field JSON string missing 'id' or 'value': {cf}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format in custom_fields_json: {e}")
    except ValueError as e: # Catch the explicit ValueError raised above
        raise e

    return api.set_custom_fields(task_id, parsed_custom_fields)

def get_clickup_list_members(list_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves members who have access to a specific ClickUp list.

    Args:
        list_id (str): The ID of the ClickUp list.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a member with access to the list. Returns an empty list if no members are found or an error occurs.
    """
    api = ClickUpAPI()
    return api.get_list_members(list_id)

def get_clickup_task_members(task_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves members who have access to a specific ClickUp task.

    Args:
        task_id (str): The ID of the ClickUp task.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a member with access to the task. Returns an empty list if no members are found or an error occurs.
    """
    api = ClickUpAPI()
    return api.get_task_members(task_id)

def get_clickup_subtasks(task_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all subtasks associated with a specific ClickUp parent task.

    Args:
        task_id (str): The ID of the parent ClickUp task.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a subtask. Returns an empty list if the task has no subtasks or an error occurs.
    """
    api = ClickUpAPI()
    return api.get_subtasks(task_id)

def create_clickup_subtask(parent_task_id: str, name: str, **kwargs) -> Dict[str, Any]:
    """
    Creates a new subtask under a specified parent task in ClickUp.

    Accepts the same optional arguments as `create_clickup_task` (description, assignees, status, etc.).

    Args:
        parent_task_id (str): The ID of the parent task under which the subtask will be created.
        name (str): The name of the new subtask.
        **kwargs: Additional optional arguments like description, assignees, status, priority, due_date, tags, custom_fields.

    Returns:
        Dict[str, Any]: A dictionary representing the newly created subtask. Raises an error if creation fails.
    """
    api = ClickUpAPI()
    return api.create_subtask(parent_task_id=parent_task_id, name=name, **kwargs)

def get_clickup_teams() -> List[Dict[str, Any]]:
    """
    Retrieves all teams (workspaces) accessible by the authenticated user.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a team/workspace.
    """
    api = ClickUpAPI()
    return api.get_teams()

def get_clickup_team_members(team_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all members belonging to a specific ClickUp team (workspace).

    Args:
        team_id (str): The ID of the ClickUp team/workspace.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a member of the team. Returns an empty list if the team is not found or an error occurs.
    """
    api = ClickUpAPI()
    return api.get_team_members(team_id)

def get_clickup_spaces(team_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all spaces within a specific ClickUp team (workspace).

    Args:
        team_id (str): The ID of the ClickUp team/workspace.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a space within the team. Returns an empty list if the team is not found or an error occurs.
    """
    api = ClickUpAPI()
    return api.get_spaces(team_id)

def get_clickup_folders(space_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all folders within a specific ClickUp space.

    Args:
        space_id (str): The ID of the ClickUp space.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a folder within the space. Returns an empty list if the space is not found or an error occurs.
    """
    api = ClickUpAPI()
    return api.get_folders(space_id)

def get_clickup_lists(folder_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all lists within a specific ClickUp folder.

    Args:
        folder_id (str): The ID of the ClickUp folder.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a list within the folder. Returns an empty list if the folder is not found or an error occurs.
    """
    api = ClickUpAPI()
    return api.get_lists(folder_id) 