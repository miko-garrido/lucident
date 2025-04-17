from typing import List, Dict, Any, Optional
import requests
from datetime import datetime, timedelta, timezone
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
        try:
            response = requests.get(
                f"{self.base_url}/team",
                headers=self.headers
            )
            response.raise_for_status() # Check for HTTP errors
            teams_data = response.json()
            teams = teams_data.get("teams", [])
            
            for team in teams:
                members = team.get("members", [])
                for member in members:
                    user = member.get("user", {})
                    # Ensure username exists and perform case-insensitive comparison
                    api_username = user.get("username")
                    if api_username and api_username.lower() == username.lower():
                        return user.get("id") # Return the user ID
            return None # Username not found in any team
        except requests.exceptions.RequestException as e:
            print(f"Error fetching teams to find user ID for '{username}': {e}")
            return None
        except json.JSONDecodeError:
            print(f"Error decoding JSON response when fetching teams for user '{username}'.")
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
    # Use timezone-aware UTC time
    date_limit = datetime.now(timezone.utc) - timedelta(days=days) 
    # ClickUp API expects milliseconds timestamp
    date_updated_gt = int(date_limit.timestamp() * 1000) 
    
    params = {
        "archived": "false",
        "date_updated_gt": date_updated_gt,
         # Consider adding pagination params if lists can be very large
        "subtasks": "true", 
        "include_closed": "true" 
    }

    try:
        response = requests.get(
            f"{api.base_url}/list/{list_id}/task", 
            headers=api.headers,
            params=params
        )
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json().get("tasks", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching tasks for list {list_id}: {e}")
        return [] # Return empty list on error
    except json.JSONDecodeError:
        print(f"Error decoding JSON response for list {list_id}.")
        return []

def get_clickup_task_details(task_id: str) -> Dict[str, Any]:
    """
    Retrieves detailed information about a specific ClickUp task.

    Args:
        task_id (str): The ID of the ClickUp task.

    Returns:
        Dict[str, Any]: A dictionary containing the details of the task (e.g., name, description, status, assignees). Returns an empty dictionary or raises an error if the task is not found.
    """
    api = ClickUpAPI()
    params = {
        "include_subtasks": "true" 
    }
    try:
        response = requests.get(
            f"{api.base_url}/task/{task_id}", 
            headers=api.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching details for task {task_id}: {e}")
        # Decide error handling: return empty dict or raise? Returning {} for now.
        return {} 
    except json.JSONDecodeError:
        print(f"Error decoding JSON response for task {task_id}.")
        return {}

def get_clickup_comments(task_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves all comments associated with a specific ClickUp task.

    Args:
        task_id (str): The ID of the ClickUp task.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary represents a comment. Returns an empty list if the task has no comments or an error occurs.
    """
    api = ClickUpAPI()
    # ClickUp API for comments is often associated with list or view, 
    # but task comments endpoint exists too.
    # Ensure correct endpoint: GET /task/{task_id}/comment
    try:
        response = requests.get(
            f"{api.base_url}/task/{task_id}/comment", 
            headers=api.headers
            # Add params like start_date, start_id if needed for pagination
        )
        response.raise_for_status()
        return response.json().get("comments", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching comments for task {task_id}: {e}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON response for task comments {task_id}.")
        return []

def get_clickup_user_tasks(username: str, days: int = 7) -> List[Dict[str, Any]]:
    """
    Retrieves tasks assigned to a specific ClickUp user across all their teams, updated within the last N days.

    Args:
        username (str): The username of the ClickUp user.
        days (int): The number of past days to look back for task updates. Defaults to 7.

    Returns:
        List[Dict[str, Any]]: A list of task dictionaries assigned to the specified user. Returns an empty list if no tasks are found or the user doesn't exist.
    """
    api = ClickUpAPI()
    user_id = api._get_user_id(username) # Use the helper method
    
    if not user_id:
        print(f"Could not find user ID for username: {username}")
        return []

    all_tasks = []
    
    # Need team ID(s) to query tasks by assignee
    # Re-fetch teams or reuse logic from _get_user_id if possible (to avoid extra API call)
    # For simplicity, let's fetch teams again here.
    try:
        team_response = requests.get(f"{api.base_url}/team", headers=api.headers)
        team_response.raise_for_status()
        teams = team_response.json().get("teams", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching teams to get user tasks for '{username}': {e}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON response when fetching teams for user tasks '{username}'.")
        return []
        
    if not teams:
        print("No teams found for the user via API key.")
        return []

    # Use timezone-aware UTC time here as well
    date_limit = datetime.now(timezone.utc) - timedelta(days=days) 
    date_updated_gt = int(date_limit.timestamp() * 1000)

    for team in teams:
        team_id = team.get("id")
        if not team_id:
            continue # Skip if team has no ID

        print(f"Fetching tasks for user ID {user_id} in team {team_id} updated after {date_limit.isoformat()}...")

        params = {
            "assignees[]": [user_id], # Filter by assignee ID
            "subtasks": "true",
            "include_closed": "true",
            "date_updated_gt": date_updated_gt
        }
        
        # Basic pagination handling
        page = 0
        while True:
            params["page"] = page
            try:
                tasks_response = requests.get(
                    f"{api.base_url}/team/{team_id}/task",
                    headers=api.headers,
                    params=params
                )
                tasks_response.raise_for_status()
                tasks_data = tasks_response.json()
                current_page_tasks = tasks_data.get("tasks", [])
                
                if not current_page_tasks:
                    break # No more tasks on this page (or subsequent pages)
                    
                all_tasks.extend(current_page_tasks)
                
                # Basic check: if fewer tasks than a potential limit (e.g., 100) are returned, assume last page
                # ClickUp V2 doesn't give 'last_page' easily here.
                if len(current_page_tasks) < 100: 
                    break 
                
                page += 1
                
            except requests.exceptions.RequestException as e:
                print(f"Error fetching page {page} of tasks for team {team_id} / user {user_id}: {e}")
                # Decide whether to break or continue with next team
                break # Break inner loop on error for this team
            except json.JSONDecodeError:
                 print(f"Error decoding JSON for page {page} of tasks team {team_id} / user {user_id}.")
                 break # Break inner loop

    print(f"Found {len(all_tasks)} tasks total for user {username} (ID: {user_id}) updated in the last {days} days.")
    return all_tasks

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
    params = {}
    if task_id: params["task_id"] = task_id # Note: API docs suggest task_id isn't a direct filter here? Verify endpoint.
                                           # /team/{team_id}/time_entries seems the main one. Let's filter client-side if needed.
    if user_id: params["assignee"] = user_id # API uses 'assignee' param for user filtering
    if start_date: params["start_date"] = start_date # Timestamps in ms
    if end_date: params["end_date"] = end_date
    
    # Add include_task_tags, include_location_names etc. if needed
    # params["include_task_tags"] = "true" 
    
    try:
        response = requests.get(
            f"{api.base_url}/team/{team_id}/time_entries", 
            headers=api.headers,
            params=params
        )
        response.raise_for_status()
        # Potentially filter further by task_id client-side if API doesn't support it directly
        entries = response.json().get("data", []) 
        if task_id:
             entries = [entry for entry in entries if entry.get('task', {}).get('id') == task_id]
        return entries
    except requests.exceptions.RequestException as e:
        print(f"Error fetching time entries for team {team_id}: {e}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON response for time entries team {team_id}.")
        return []

# def create_clickup_task(list_id: str, name: str, description: Optional[str] = None,
#                       assignees: Optional[List[int]] = None, status: Optional[str] = None,
#                       priority: Optional[int] = None, due_date: Optional[int] = None,
#                       tags: Optional[List[str]] = None, custom_fields_json: Optional[List[str]] = None) -> Dict[str, Any]:
#     """
#     Creates a new task in a specified ClickUp list.

#     Args:
#         list_id (str): The ID of the ClickUp list where the task will be created.
#         name (str): The name of the new task.
#         description (Optional[str]): The description for the task.
#         assignees (Optional[List[int]]): A list of user IDs to assign to the task.
#         status (Optional[str]): The status to set for the task (e.g., "To Do", "In Progress").
#         priority (Optional[int]): The priority level (1=Urgent, 2=High, 3=Normal, 4=Low).
#         due_date (Optional[int]): The due date for the task as a Unix timestamp.
#         tags (Optional[List[str]]): A list of tag names to apply to the task.
#         custom_fields_json (Optional[List[str]]): A list of custom field values as JSON strings. Each string must be a valid JSON object, e.g., '{"id": "field_id", "value": "field_value"}'.

#     Returns:
#         Dict[str, Any]: A dictionary representing the newly created task. Raises an error if creation fails.
#     """
#     api = ClickUpAPI()
    
#     payload = {"name": name}
#     if description is not None: payload["description"] = description
#     if assignees is not None: payload["assignees"] = assignees
#     if status is not None: payload["status"] = status
#     if priority is not None: payload["priority"] = priority
#     if due_date is not None: payload["due_date"] = due_date # Unix ms timestamp
#     if tags is not None: payload["tags"] = tags
    
#     # Handle custom fields
#     if custom_fields_json:
#         parsed_custom_fields = []
#         try:
#             for cf_str in custom_fields_json:
#                  field_data = json.loads(cf_str)
#                  # Basic validation
#                  if "id" not in field_data or "value" not in field_data:
#                       raise ValueError(f"Custom field JSON missing 'id' or 'value': {cf_str}")
#                  parsed_custom_fields.append(field_data)
#             payload["custom_fields"] = parsed_custom_fields
#         except json.JSONDecodeError as e:
#             raise ValueError(f"Invalid JSON format in custom_fields_json: {e}")
#         except ValueError as e: # Catch validation error
#              raise e

#     try:
#         response = requests.post(
#             f"{api.base_url}/list/{list_id}/task", 
#             headers=api.headers, 
#             json=payload # Send data as JSON body
#         )
#         response.raise_for_status()
#         return response.json()
#     except requests.exceptions.RequestException as e:
#         print(f"Error creating task in list {list_id}: {e} - Response: {e.response.text if e.response else 'No response'}")
#         # Re-raise or return error indicator? Raising for now.
#         raise e 
#     except json.JSONDecodeError:
#         # This might happen if the response isn't JSON on success (unlikely for create)
#          print(f"Error decoding JSON response after creating task in list {list_id}.")
#          raise # Re-raise, as a successful creation should return JSON

# def update_clickup_task(task_id: str, name: Optional[str] = None, description: Optional[str] = None,
#                       assignees: Optional[List[int]] = None, status: Optional[str] = None,
#                       priority: Optional[int] = None, due_date: Optional[int] = None,
#                       tags: Optional[List[str]] = None) -> Dict[str, Any]:
#     """
#     Updates an existing ClickUp task. Does NOT update custom fields (use set_clickup_custom_fields).

#     Args:
#         task_id (str): The ID of the task to update.
#         name (Optional[str]): The new name for the task.
#         description (Optional[str]): The new description for the task.
#         assignees (Optional[List[int]]): The new list of assignee user IDs.
#         status (Optional[str]): The new status for the task.
#         priority (Optional[int]): The new priority level.
#         due_date (Optional[int]): The new due date (Unix timestamp).
#         tags (Optional[List[str]]): The new list of tags.

#     Returns:
#         Dict[str, Any]: A dictionary representing the updated task. Raises an error if the update fails or the task is not found.
#     """
#     api = ClickUpAPI()
#     payload = {}
#     if name is not None: payload["name"] = name
#     if description is not None: payload["description"] = description
#     # Handling assignees might need PUT for replacement or special handling
#     # Check ClickUp API: PUT /task/{task_id} usually replaces fields provided.
#     if assignees is not None: payload["assignees"] = assignees # This might overwrite existing unless handled carefully by API
#     if status is not None: payload["status"] = status
#     if priority is not None: payload["priority"] = priority
#     if due_date is not None: payload["due_date"] = due_date
#     if tags is not None: payload["tags"] = tags # Check API for how tags are updated (append vs replace)

#     if not payload:
#         print("No update parameters provided for update_clickup_task.")
#         # Maybe return current task details or raise error? Returning {}
#         return get_clickup_task_details(task_id) # Return current details if no changes

#     try:
#         response = requests.put( # Use PUT for updates typically
#             f"{api.base_url}/task/{task_id}", 
#             headers=api.headers, 
#             json=payload
#         )
#         response.raise_for_status()
#         return response.json()
#     except requests.exceptions.RequestException as e:
#         print(f"Error updating task {task_id}: {e} - Response: {e.response.text if e.response else 'No response'}")
#         raise e
#     except json.JSONDecodeError:
#         print(f"Error decoding JSON response after updating task {task_id}.")
#         raise

# def delete_clickup_task(task_id: str) -> Dict[str, Any]:
#     """
#     Deletes a specific ClickUp task.

#     Args:
#         task_id (str): The ID of the task to delete.

#     Returns:
#         Dict[str, Any]: An empty dictionary ({}) upon successful deletion. Raises an error if deletion fails or the task is not found.
#     """
#     api = ClickUpAPI()
#     try:
#         response = requests.delete(
#             f"{api.base_url}/task/{task_id}", 
#             headers=api.headers
#         )
#         # Successful deletion often returns 204 No Content
#         if response.status_code == 204:
#             return {} # Return empty dict on success (204)
#         response.raise_for_status() # Raise for other errors (4xx, 5xx)
#         # If it returns content on success (e.g., 200 OK with data), handle it:
#         # return response.json() 
#         return {} # Assuming 204 is the primary success case
#     except requests.exceptions.RequestException as e:
#         print(f"Error deleting task {task_id}: {e}")
#         raise e

# def create_clickup_comment(task_id: str, comment_text: str, assignees: Optional[List[int]] = None, notify_all: bool = False) -> Dict[str, Any]:
#     """
#     Adds a comment to a specific ClickUp task. Can assign and notify.

#     Args:
#         task_id (str): The ID of the task to add the comment to.
#         comment_text (str): The text content of the comment.
#         assignees (Optional[List[int]]): A list of user IDs to assign to the comment.
#         notify_all (bool): Whether to notify all members of the task.

#     Returns:
#         Dict[str, Any]: A dictionary representing the newly created comment. Raises an error if creation fails.
#     """
#     api = ClickUpAPI()
#     payload = {
#         "comment_text": comment_text,
#         "notify_all": notify_all
#     }
#     if assignees:
#         payload["assignee"] = assignees[0] # API seems to take one assignee for comment creation? Verify.
#         # If multiple assignees needed, maybe @mention in text?
        
#     # Endpoint: POST /task/{task_id}/comment
#     try:
#         response = requests.post(
#             f"{api.base_url}/task/{task_id}/comment", 
#             headers=api.headers,
#             json=payload
#         )
#         response.raise_for_status()
#         return response.json() # Returns details of the created comment
#     except requests.exceptions.RequestException as e:
#         print(f"Error creating comment on task {task_id}: {e} - Response: {e.response.text if e.response else 'No response'}")
#         raise e
#     except json.JSONDecodeError:
#          print(f"Error decoding JSON response after creating comment on task {task_id}.")
#          raise

# def update_clickup_comment(comment_id: str, comment_text: str) -> Dict[str, Any]:
#     """
#     Updates the text of an existing ClickUp comment.

#     Args:
#         comment_id (str): The ID of the comment to update.
#         comment_text (str): The new text content for the comment.

#     Returns:
#         Dict[str, Any]: A dictionary representing the updated comment status (often just a success indicator from the API). Raises an error if update fails.
#     """
#     api = ClickUpAPI()
#     payload = {"comment_text": comment_text}
    
#     # Endpoint: PUT /comment/{comment_id}
#     try:
#         response = requests.put(
#             f"{api.base_url}/comment/{comment_id}", 
#             headers=api.headers,
#             json=payload
#         )
#         response.raise_for_status()
#         # Update often returns 200 OK with empty body or success status
#         # Check API docs for expected successful response
#         # If it returns JSON: return response.json()
#         return {"status": "success", "comment_id": comment_id} # Placeholder success
#     except requests.exceptions.RequestException as e:
#         print(f"Error updating comment {comment_id}: {e} - Response: {e.response.text if e.response else 'No response'}")
#         raise e

# def delete_clickup_comment(comment_id: str) -> Dict[str, Any]:
#     """
#     Deletes a specific ClickUp comment.

#     Args:
#         comment_id (str): The ID of the comment to delete.

#     Returns:
#         Dict[str, Any]: An empty dictionary ({}) upon successful deletion. Raises an error if deletion fails.
#     """
#     api = ClickUpAPI()
#     # Endpoint: DELETE /comment/{comment_id}
#     try:
#         response = requests.delete(
#             f"{api.base_url}/comment/{comment_id}", 
#             headers=api.headers
#         )
#         if response.status_code == 204:
#             return {} # Success
#         response.raise_for_status()
#         return {} # Assuming 204 success
#     except requests.exceptions.RequestException as e:
#         print(f"Error deleting comment {comment_id}: {e}")
#         raise e

# def set_clickup_custom_fields(task_id: str, custom_fields_json: List[str]) -> Dict[str, Any]:
#     """
#     Sets or updates the values of custom fields for a specific ClickUp task using JSON strings.

#     Args:
#         task_id (str): The ID of the task to update custom fields for.
#         custom_fields_json (List[str]): A list of custom field dictionaries as JSON strings to set. Each string must be a valid JSON object with "id" and "value". Example: ['{"id": "abc-123", "value": "New Value"}'].

#     Returns:
#         Dict[str, Any]: A dictionary representing the task after the custom fields have been updated. Raises an error if the update fails.
#     """
#     api = ClickUpAPI()
    
#     # Parse and validate JSON strings first
#     parsed_custom_fields = []
#     try:
#         for cf_str in custom_fields_json:
#             field_data = json.loads(cf_str)
#             if "id" not in field_data or "value" not in field_data:
#                  raise ValueError(f"Custom field JSON missing 'id' or 'value': {cf_str}")
#             parsed_custom_fields.append(field_data)
#     except json.JSONDecodeError as e:
#         raise ValueError(f"Invalid JSON format in custom_fields_json: {e}")
#     except ValueError as e: # Catch validation error
#          raise e

#     if not parsed_custom_fields:
#         raise ValueError("No valid custom field data provided.")

#     # ClickUp API uses POST /task/{task_id}/field/{field_id}
#     # We need to make one request per custom field to update
    
#     # Note: This approach might be inefficient for many fields. 
#     # Check if task update (PUT /task/{task_id}) supports updating custom fields directly in its payload.
#     # If PUT /task/{task_id} supports 'custom_fields': [{ "id": "...", "value": ...}] then update_clickup_task could handle this.
#     # Assuming we MUST use the specific endpoint for now:
    
#     results = []
#     errors = []
#     for field in parsed_custom_fields:
#         field_id = field["id"]
#         field_value = {"value": field["value"]} # Payload requires {"value": ...}
#         try:
#             response = requests.post( # POST to set/update custom field value
#                 f"{api.base_url}/task/{task_id}/field/{field_id}", 
#                 headers=api.headers,
#                 json=field_value
#             )
#             response.raise_for_status()
#             # Success usually 200 OK, maybe with the updated task?
#             # For simplicity, let's just note success or capture response if needed.
#             results.append({"field_id": field_id, "status": "success"}) 
#         except requests.exceptions.RequestException as e:
#             print(f"Error setting custom field {field_id} on task {task_id}: {e}")
#             errors.append({"field_id": field_id, "error": str(e)})
#             # Decide: continue or stop on first error? Continuing for now.
    
#     if errors:
#         # Raise an error summarizing failures or return partial success?
#         raise Exception(f"Failed to set some custom fields: {errors}")
        
#     # After setting all fields, maybe fetch the updated task?
#     return get_clickup_task_details(task_id) 

def get_clickup_list_members(list_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves members who have access to a specific ClickUp list.

    Args:
        list_id (str): The ID of the ClickUp list.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a member with access to the list. Returns an empty list if no members are found or an error occurs.
    """
    api = ClickUpAPI()
    # Endpoint: GET /list/{list_id}/member
    try:
        response = requests.get(
            f"{api.base_url}/list/{list_id}/member", 
            headers=api.headers
        )
        response.raise_for_status()
        return response.json().get("members", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching members for list {list_id}: {e}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON response for list members {list_id}.")
        return []

def get_clickup_task_members(task_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves members associated with (e.g., assigned to) a specific ClickUp task.
    This might just be the 'assignees' field from get_task_details.
    Let's fetch task details and extract assignees.
    """
    try:
        task_details = get_clickup_task_details(task_id)
        return task_details.get("assignees", [])
    except Exception as e: # Catch potential errors from get_clickup_task_details
        print(f"Error getting task details to find members for task {task_id}: {e}")
        return []

def get_clickup_subtasks(task_id: str, archived: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieves all subtasks associated with a specific ClickUp parent task.

    Args:
        task_id (str): The ID of the parent ClickUp task.
        archived (bool): Whether to include archived subtasks.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a subtask. Returns an empty list if the task has no subtasks or an error occurs.
    """
    api = ClickUpAPI()
    # Subtasks are often included in the parent task details or fetched via filtering tasks
    # Let's use the `get_clickup_tasks` approach but filter by parent ID
    # Need parent task's list_id first.
    
    # Alternative: Task details often include subtask IDs. Let's try that first.
    try:
        parent_task = get_clickup_task_details(task_id)
        if not parent_task: return []
        
        # Check if subtasks are directly included
        if "subtasks" in parent_task and isinstance(parent_task["subtasks"], list):
             # If full subtask objects are embedded:
             # return parent_task["subtasks"] 
             pass # Assume they are not fully embedded by default

        # If only IDs or partial info, fetch them fully?
        # More robust: Query tasks with parent filter
        list_id = parent_task.get("list", {}).get("id")
        if not list_id:
             print(f"Could not determine list_id for parent task {task_id} to fetch subtasks.")
             return []

        params = {
            "archived": str(archived).lower(),
            "parent": task_id, # Filter by parent task ID
            "subtasks": "true" # Include subtasks of subtasks? Usually not needed here.
        }
        
        response = requests.get(
            f"{api.base_url}/list/{list_id}/task", 
            headers=api.headers,
            params=params
        )
        response.raise_for_status()
        return response.json().get("tasks", [])
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching subtasks for parent task {task_id}: {e}")
        return []
    except Exception as e: # Catch errors from get_clickup_task_details
         print(f"Error getting parent task details for {task_id}: {e}")
         return []

# def create_clickup_subtask(parent_task_id: str, name: str, **kwargs) -> Dict[str, Any]:
#     """
#     Creates a new subtask under a specified parent task in ClickUp.
#     Accepts same optional args as create_clickup_task.

#     Args:
#         parent_task_id (str): The ID of the parent task under which the subtask will be created.
#         name (str): The name of the new subtask.
#         **kwargs: Additional optional arguments like description, assignees, status, priority, due_date, tags, custom_fields.

#     Returns:
#         Dict[str, Any]: A dictionary representing the newly created subtask. Raises an error if creation fails.
#     """
#     api = ClickUpAPI()
    
#     # Need the list_id of the parent task
#     try:
#         parent_task = get_clickup_task_details(parent_task_id)
#         list_id = parent_task.get("list", {}).get("id")
#         if not list_id:
#             raise ValueError(f"Could not find list_id for parent task {parent_task_id}")
#     except Exception as e:
#          raise ValueError(f"Failed to get parent task details to create subtask: {e}")

#     payload = {"name": name, "parent": parent_task_id} # Set parent field
    
#     # Add other optional args from kwargs if present
#     # (description, assignees, status, priority, due_date, tags, custom_fields_json)
#     if kwargs.get("description"): payload["description"] = kwargs["description"]
#     if kwargs.get("assignees"): payload["assignees"] = kwargs["assignees"]
#     if kwargs.get("status"): payload["status"] = kwargs["status"]
#     if kwargs.get("priority"): payload["priority"] = kwargs["priority"]
#     if kwargs.get("due_date"): payload["due_date"] = kwargs["due_date"]
#     if kwargs.get("tags"): payload["tags"] = kwargs["tags"]
    
#     # Handle custom fields similarly to create_clickup_task
#     if "custom_fields_json" in kwargs:
#         parsed_custom_fields = []
#         try:
#             for cf_str in kwargs["custom_fields_json"]:
#                  field_data = json.loads(cf_str)
#                  if "id" not in field_data or "value" not in field_data:
#                       raise ValueError(f"Subtask Custom field JSON missing 'id' or 'value': {cf_str}")
#                  parsed_custom_fields.append(field_data)
#             payload["custom_fields"] = parsed_custom_fields
#         except json.JSONDecodeError as e:
#             raise ValueError(f"Invalid JSON format in subtask custom_fields_json: {e}")
#         except ValueError as e:
#              raise e
             
#     try:
#         # Use the same endpoint as create_task, just include "parent" in payload
#         response = requests.post(
#             f"{api.base_url}/list/{list_id}/task", 
#             headers=api.headers, 
#             json=payload
#         )
#         response.raise_for_status()
#         return response.json()
#     except requests.exceptions.RequestException as e:
#         print(f"Error creating subtask under {parent_task_id} in list {list_id}: {e} - Response: {e.response.text if e.response else 'No response'}")
#         raise e
#     except json.JSONDecodeError:
#          print(f"Error decoding JSON response after creating subtask for {parent_task_id}.")
#          raise

def get_clickup_teams() -> List[Dict[str, Any]]:
    """
    Retrieves all teams (workspaces) accessible by the authenticated user.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a team/workspace.
    """
    api = ClickUpAPI()
    # Endpoint: GET /team
    try:
        response = requests.get(f"{api.base_url}/team", headers=api.headers)
        response.raise_for_status()
        return response.json().get("teams", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching teams: {e}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON response when fetching teams.")
        return []

def get_clickup_team_members(team_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves members of a specific ClickUp team (workspace).
    Note: The /team endpoint already returns members. This might be redundant
    unless a specific team's member list is needed without fetching all teams.
    Let's use the /team endpoint and filter.

    Args:
        team_id (str): The ID of the ClickUp team/workspace.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a member of the team. Returns an empty list if the team is not found or an error occurs.
    """
    try:
        all_teams = get_clickup_teams()
        for team in all_teams:
            if team.get("id") == team_id:
                return team.get("members", [])
        print(f"Team with ID {team_id} not found among accessible teams.")
        return []
    except Exception as e: # Catch errors from get_clickup_teams
        print(f"Error retrieving teams to find members for team {team_id}: {e}")
        return []

def get_clickup_spaces(team_id: str, archived: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieves all spaces within a specific ClickUp team (workspace).

    Args:
        team_id (str): The ID of the ClickUp team/workspace.
        archived (bool): Whether to include archived spaces.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a space within the team. Returns an empty list if the team is not found or an error occurs.
    """
    api = ClickUpAPI()
    params = {"archived": str(archived).lower()}
    # Endpoint: GET /team/{team_id}/space
    try:
        response = requests.get(
            f"{api.base_url}/team/{team_id}/space", 
            headers=api.headers,
            params=params
        )
        response.raise_for_status()
        return response.json().get("spaces", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching spaces for team {team_id}: {e}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON response for spaces in team {team_id}.")
        return []

def get_clickup_folders(space_id: str, archived: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieves all folders within a specific ClickUp space.

    Args:
        space_id (str): The ID of the ClickUp space.
        archived (bool): Whether to include archived folders.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a folder within the space. Returns an empty list if the space is not found or an error occurs.
    """
    api = ClickUpAPI()
    params = {"archived": str(archived).lower()}
    # Endpoint: GET /space/{space_id}/folder
    try:
        response = requests.get(
            f"{api.base_url}/space/{space_id}/folder", 
            headers=api.headers,
            params=params
        )
        response.raise_for_status()
        return response.json().get("folders", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching folders for space {space_id}: {e}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON response for folders in space {space_id}.")
        return []

def get_clickup_lists(folder_id: str, archived: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieves all lists within a specific ClickUp folder.

    Args:
        folder_id (str): The ID of the ClickUp folder.
        archived (bool): Whether to include archived lists.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a list within the folder. Returns an empty list if the folder is not found or an error occurs.
    """
    api = ClickUpAPI()
    params = {"archived": str(archived).lower()}
    # Endpoint: GET /folder/{folder_id}/list
    try:
        response = requests.get(
            f"{api.base_url}/folder/{folder_id}/list", 
            headers=api.headers,
            params=params
        )
        response.raise_for_status()
        return response.json().get("lists", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching lists for folder {folder_id}: {e}")
        return []
    except json.JSONDecodeError:
        print(f"Error decoding JSON response for lists in folder {folder_id}.")
        return []
