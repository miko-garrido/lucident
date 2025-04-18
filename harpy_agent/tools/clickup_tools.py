from typing import List, Dict, Any, Optional
import requests
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# --- Custom Exceptions ---
class ClickUpError(Exception):
    """Base exception for ClickUp API errors."""
    pass

class ClickUpAPIError(ClickUpError):
    """Exception raised for errors in the ClickUp API request itself."""
    def __init__(self, message, status_code=None, response_text=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
    
    def __str__(self):
        return f"{super().__str__()} (Status Code: {self.status_code}, Response: {self.response_text})"

class ResourceNotFoundError(ClickUpError):
    """Exception raised when a ClickUp resource (task, list, user, etc.) is not found."""
    pass

class InvalidInputError(ClickUpError):
    """Exception raised for invalid input provided to a function."""
    pass

class ClickUpConfigError(ClickUpError):
    """Exception raised for configuration issues (e.g., missing API key)."""
    pass

# --- ClickUpAPI Class ---
class ClickUpAPI:
    def __init__(self):
        self.api_key = os.getenv("CLICKUP_API_KEY")
        if not self.api_key:
            raise ClickUpConfigError("CLICKUP_API_KEY not found in environment variables")
        
        self.workspace_id = os.getenv("CLICKUP_WORKSPACE_ID", "3723297") # Load from env or use default
        if not self.workspace_id:
             raise ClickUpConfigError("CLICKUP_WORKSPACE_ID not found in environment variables and no default provided")
            
        self.base_url = "https://api.clickup.com/api/v2"
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Any:
        """Makes an HTTP request to the ClickUp API and handles common errors."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(
                method, url, headers=self.headers, params=params, json=data
            )
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            # Handle specific HTTP errors like 404 Not Found
            if http_err.response.status_code == 404:
                raise ResourceNotFoundError(f"Resource not found at {url}. {http_err}")
            elif http_err.response.status_code == 401:
                 raise ClickUpAPIError(f"Authentication error (401). Check API key. {http_err}", status_code=401, response_text=http_err.response.text)
            else:
                raise ClickUpAPIError(
                    f"HTTP error occurred: {http_err}", 
                    status_code=http_err.response.status_code, 
                    response_text=http_err.response.text
                )
        except requests.exceptions.ConnectionError as conn_err:
            raise ClickUpAPIError(f"Connection error: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            raise ClickUpAPIError(f"Request timed out: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            # Catch other request-related errors
            raise ClickUpAPIError(f"An error occurred during the API request: {req_err}")
        except json.JSONDecodeError as json_err:
            # Handle errors in parsing the JSON response
            raise ClickUpAPIError(f"Failed to decode JSON response from {url}. Error: {json_err}. Response text: {response.text}", response_text=response.text if 'response' in locals() else 'No response object')


    def _get_user_id(self, username: str) -> str:
        """
        Helper method to get user ID from username.
        Raises ResourceNotFoundError if the user is not found.
        """
        endpoint = "/team"
        try:
            teams_data = self._make_request("GET", endpoint)
            teams = teams_data.get("teams", [])
            
            for team in teams:
                members = team.get("members", [])
                for member in members:
                    user = member.get("user", {})
                    api_username = user.get("username")
                    api_email = user.get("email") # Get email field
                    # Check if the input username matches either the API username or email (case-insensitive)
                    if (api_username and api_username.lower() == username.lower()) or \
                       (api_email and api_email.lower() == username.lower()):
                        user_id = user.get("id")
                        if user_id:
                            return str(user_id) # Ensure it returns string ID
                        else:
                            # This case should ideally not happen if username matches, but good to handle
                            raise ClickUpError(f"Found user '{username}' but ID is missing in API response.")
            
            # If loop completes without returning, user was not found
            raise ResourceNotFoundError(f"User with username or email '{username}' not found in any accessible team.")

        except ClickUpAPIError as e:
             # Re-raise API errors with more context
             raise ClickUpAPIError(f"Failed to fetch teams to find user ID for '{username}': {e}", status_code=e.status_code, response_text=e.response_text) from e
        except Exception as e: # Catch any other unexpected error
             logging.error(f"Unexpected error finding user ID for '{username}': {e}", exc_info=True)
             raise ClickUpError(f"An unexpected error occurred while finding user ID for '{username}'.") from e


# --- Standalone Function Tools ---

def get_clickup_tasks(list_id: str, days: int = 7) -> List[Dict[str, Any]]:
    """
    Retrieves tasks from a specific ClickUp list updated within the last N days.

    Args:
        list_id (str): The ID of the ClickUp list.
        days (int): The number of past days for task updates. Defaults to 7.

    Returns:
        List[Dict[str, Any]]: A list of task dictionaries.

    Raises:
        ClickUpAPIError: If the API request fails.
        ResourceNotFoundError: If the list_id is invalid or not found.
        InvalidInputError: If days is negative.
        ClickUpError: For other ClickUp related errors.
    """
    if days < 0:
        raise InvalidInputError("Number of days must be non-negative.")
        
    api = ClickUpAPI()
    date_limit = datetime.now(timezone.utc) - timedelta(days=days) 
    date_updated_gt = int(date_limit.timestamp() * 1000) 
    
    params = {
        "archived": "false",
        "date_updated_gt": date_updated_gt,
        "subtasks": "true", 
        "include_closed": "true" 
    }
    endpoint = f"/list/{list_id}/task"
    
    try:
        response_data = api._make_request("GET", endpoint, params=params)
        return response_data.get("tasks", [])
    except (ClickUpAPIError, ResourceNotFoundError) as e:
         logging.error(f"Failed to get tasks for list {list_id}: {e}")
         raise # Re-raise the specific error
    except Exception as e: # Catch unexpected errors
        logging.error(f"Unexpected error getting tasks for list {list_id}: {e}", exc_info=True)
        raise ClickUpError(f"An unexpected error occurred fetching tasks for list {list_id}.") from e


def get_clickup_task_details(task_id: str) -> Dict[str, Any]:
    """
    Retrieves detailed information about a specific ClickUp task.

    Args:
        task_id (str): The ID of the ClickUp task.

    Returns:
        Dict[str, Any]: A dictionary containing the task details.

    Raises:
        ClickUpAPIError: If the API request fails.
        ResourceNotFoundError: If the task_id is invalid or not found.
        ClickUpError: For other ClickUp related errors.
    """
    api = ClickUpAPI()
    params = {"include_subtasks": "true"}
    endpoint = f"/task/{task_id}"
    
    try:
        return api._make_request("GET", endpoint, params=params)
    except (ClickUpAPIError, ResourceNotFoundError) as e:
        logging.error(f"Failed to get details for task {task_id}: {e}")
        raise # Re-raise the specific error
    except Exception as e: # Catch unexpected errors
        logging.error(f"Unexpected error getting details for task {task_id}: {e}", exc_info=True)
        raise ClickUpError(f"An unexpected error occurred fetching details for task {task_id}.") from e


def get_clickup_comments(task_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves comments for a specific ClickUp task.

    Args:
        task_id (str): The ID of the ClickUp task.

    Returns:
        List[Dict[str, Any]]: A list of comment dictionaries.

    Raises:
        ClickUpAPIError: If the API request fails.
        ResourceNotFoundError: If the task_id is invalid or not found.
        ClickUpError: For other ClickUp related errors.
    """
    api = ClickUpAPI()
    endpoint = f"/task/{task_id}/comment"
    
    try:
        response_data = api._make_request("GET", endpoint)
        return response_data.get("comments", [])
    except (ClickUpAPIError, ResourceNotFoundError) as e:
        logging.error(f"Failed to get comments for task {task_id}: {e}")
        raise # Re-raise the specific error
    except Exception as e: # Catch unexpected errors
        logging.error(f"Unexpected error getting comments for task {task_id}: {e}", exc_info=True)
        raise ClickUpError(f"An unexpected error occurred fetching comments for task {task_id}.") from e


def get_clickup_user_tasks(username: str, days: int = 7) -> List[Dict[str, Any]]:
    """
    Retrieves tasks assigned to a specific ClickUp user, updated within N days.

    Args:
        username (str): The username of the ClickUp user.
        days (int): The number of past days for task updates. Defaults to 7.

    Returns:
        List[Dict[str, Any]]: A list of task dictionaries assigned to the user.

    Raises:
        ClickUpAPIError: If API requests fail.
        ResourceNotFoundError: If the user or required teams are not found.
        InvalidInputError: If days is negative.
        ClickUpError: For other ClickUp related errors.
    """
    if days < 0:
         raise InvalidInputError("Number of days must be non-negative.")
         
    api = ClickUpAPI()
    
    try:
        user_id = api._get_user_id(username) # Can raise ResourceNotFoundError or ClickUpAPIError
    except ResourceNotFoundError as e:
        logging.error(f"Failed to find user '{username}': {e}")
        # Return empty list if user not found, as no tasks can be fetched.
        return [] 
    except ClickUpAPIError as e:
         logging.error(f"API error getting user ID for '{username}': {e}")
         raise # Propagate API errors
    except Exception as e: # Catch other unexpected errors from _get_user_id
        logging.error(f"Unexpected error getting user ID for '{username}': {e}", exc_info=True)
        raise ClickUpError(f"An unexpected error occurred getting user ID for {username}.") from e

    all_tasks = []
    teams = []
    
    # Fetch teams once
    try:
        teams_data = api._make_request("GET", "/team")
        teams = teams_data.get("teams", [])
        if not teams:
             # It's possible the user exists but has no accessible teams via this API key
             logging.warning(f"No teams found via API key, cannot fetch tasks for user '{username}'.")
             return [] # Return empty list if no teams are accessible
    except (ClickUpAPIError, ResourceNotFoundError) as e:
        logging.error(f"Failed to fetch teams to get tasks for user '{username}': {e}")
        raise ClickUpAPIError(f"Could not fetch teams for user '{username}'.") from e
    except Exception as e:
        logging.error(f"Unexpected error fetching teams for user '{username}': {e}", exc_info=True)
        raise ClickUpError(f"An unexpected error occurred fetching teams for user {username}.") from e

    date_limit = datetime.now(timezone.utc) - timedelta(days=days) 
    date_updated_gt = int(date_limit.timestamp() * 1000)

    for team in teams:
        team_id = team.get("id")
        if not team_id:
            logging.warning(f"Skipping team without ID: {team.get('name', 'N/A')}")
            continue 

        logging.info(f"Fetching tasks for user ID {user_id} in team {team_id} updated after {date_limit.isoformat()}...")

        base_params = {
            "assignees[]": [user_id], # API expects list format even for one ID
            "subtasks": "true",
            "include_closed": "true",
            "date_updated_gt": date_updated_gt
        }
        
        page = 0
        while True:
            params = base_params.copy()
            params["page"] = page
            endpoint = f"/team/{team_id}/task"
            
            try:
                tasks_data = api._make_request("GET", endpoint, params=params)
                current_page_tasks = tasks_data.get("tasks", [])
                
                if not current_page_tasks:
                    break # No more tasks on this page
                    
                all_tasks.extend(current_page_tasks)
                
                # Assume last page if fewer than 100 tasks returned (ClickUp's typical page limit)
                if len(current_page_tasks) < 100: 
                    break 
                
                page += 1
                
            except (ClickUpAPIError, ResourceNotFoundError) as e:
                # Log error for this specific page/team but continue to next team
                logging.error(f"Error fetching page {page} of tasks for team {team_id} / user {user_id}: {e}")
                break # Stop fetching for this team on error
            except Exception as e:
                 logging.error(f"Unexpected error fetching page {page} for team {team_id} / user {user_id}: {e}", exc_info=True)
                 break # Stop fetching for this team on unexpected error

    logging.info(f"Found {len(all_tasks)} tasks total for user {username} (ID: {user_id}) updated in the last {days} days.")
    return all_tasks


def get_clickup_time_entries(task_id: Optional[str] = None, user_id: Optional[str] = None,
                           start_date: Optional[int] = None, end_date: Optional[int] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Retrieves ClickUp time entries, optionally filtered.

    Args:
        task_id (Optional[str]): Filter by task ID.
        user_id (Optional[str]): Filter by user ID.
        start_date (Optional[int]): Start Unix timestamp (ms).
        end_date (Optional[int]): End Unix timestamp (ms).

    Returns:
        Dict[str, List[Dict[str, Any]]]: A dictionary with 'entries' key containing a list of time entry dictionaries.

    Raises:
        ClickUpAPIError: If the API request fails.
        ResourceNotFoundError: If the underlying team/workspace is not found.
        ClickUpError: For other ClickUp related errors.
    """
    api = ClickUpAPI()
    team_id = api.workspace_id # Use the workspace ID
    params = {}
    # API uses 'assignee' param for user filtering
    if user_id: params["assignee"] = user_id 
    if start_date: params["start_date"] = start_date
    if end_date: params["end_date"] = end_date
    # Add other potential params if needed:
    # params["include_task_tags"] = "true" 
    # params["include_location_names"] = "true"
    
    endpoint = f"/team/{team_id}/time_entries"
    
    try:
        response_data = api._make_request("GET", endpoint, params=params)
        entries = response_data.get("data", []) 
        
        # Client-side filtering for task_id if provided, as API might not support it directly
        if task_id:
             entries = [entry for entry in entries if entry.get('task', {}).get('id') == task_id]
             
        # Return a dictionary structure instead of a plain list
        return {"entries": entries}
    except (ClickUpAPIError, ResourceNotFoundError) as e:
        logging.error(f"Failed to get time entries for team {team_id}: {e}")
        
        # If an error occurs, potentially return an empty structure or re-raise
        # For consistency, let's return an empty list within the dict structure on handled errors too,
        # although re-raising might be preferred depending on desired error handling.
        # Re-raising as it was originally. Consider returning {'entries': []} here if needed.
        raise # Re-raise the specific error
    except Exception as e: # Catch unexpected errors
        logging.error(f"Unexpected error getting time entries for team {team_id}: {e}", exc_info=True)
        # Similarly, consider returning {'entries': []} here too if exceptions should yield empty results.
        # Re-raising as it was originally.
        raise ClickUpError(f"An unexpected error occurred fetching time entries for team {team_id}.") from e


def get_clickup_list_members(list_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves members with access to a specific ClickUp list.

    Args:
        list_id (str): The ID of the ClickUp list.

    Returns:
        List[Dict[str, Any]]: A list of member dictionaries.

    Raises:
        ClickUpAPIError: If the API request fails.
        ResourceNotFoundError: If the list_id is invalid or not found.
        ClickUpError: For other ClickUp related errors.
    """
    api = ClickUpAPI()
    endpoint = f"/list/{list_id}/member"
    
    try:
        response_data = api._make_request("GET", endpoint)
        return response_data.get("members", [])
    except (ClickUpAPIError, ResourceNotFoundError) as e:
        logging.error(f"Failed to get members for list {list_id}: {e}")
        raise # Re-raise the specific error
    except Exception as e: # Catch unexpected errors
        logging.error(f"Unexpected error getting members for list {list_id}: {e}", exc_info=True)
        raise ClickUpError(f"An unexpected error occurred fetching members for list {list_id}.") from e


def get_clickup_task_members(task_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves members assigned to a specific ClickUp task.

    Args:
        task_id (str): The ID of the ClickUp task.

    Returns:
        List[Dict[str, Any]]: A list of assignee dictionaries.

    Raises:
        ClickUpAPIError: If the API request for task details fails.
        ResourceNotFoundError: If the task_id is invalid or not found.
        ClickUpError: For other ClickUp related errors.
    """
    try:
        # Reuses get_clickup_task_details, which already handles errors
        task_details = get_clickup_task_details(task_id) 
        return task_details.get("assignees", [])
    except (ClickUpAPIError, ResourceNotFoundError) as e:
        # Log and re-raise errors from get_clickup_task_details
        logging.error(f"Failed to get task details to find members for task {task_id}: {e}")
        raise
    except Exception as e: # Catch unexpected errors
        logging.error(f"Unexpected error finding members for task {task_id}: {e}", exc_info=True)
        raise ClickUpError(f"An unexpected error occurred finding members for task {task_id}.") from e


def get_clickup_subtasks(task_id: str, archived: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieves subtasks for a specific ClickUp parent task.

    Args:
        task_id (str): The ID of the parent task.
        archived (bool): Whether to include archived subtasks.

    Returns:
        List[Dict[str, Any]]: A list of subtask dictionaries.

    Raises:
        ClickUpAPIError: If API requests fail.
        ResourceNotFoundError: If the parent task or its list is not found.
        ClickUpError: If the parent task's list ID cannot be determined or other errors occur.
    """
    api = ClickUpAPI()
    parent_task = {}
    
    try:
        # Get parent task details first to find its list ID
        parent_task = get_clickup_task_details(task_id) # Handles its own errors
    except (ClickUpAPIError, ResourceNotFoundError) as e:
         logging.error(f"Failed to get parent task details ({task_id}) to fetch subtasks: {e}")
         raise # Re-raise error from getting parent task
    except Exception as e:
        logging.error(f"Unexpected error getting parent task {task_id}: {e}", exc_info=True)
        raise ClickUpError(f"An unexpected error occurred getting parent task {task_id}.") from e

    # Check if subtasks might be embedded (though unlikely to be full details)
    # if "subtasks" in parent_task and isinstance(parent_task["subtasks"], list):
    #      logging.warning(f"Parent task {task_id} response contains a 'subtasks' key. Assuming it's incomplete and fetching via list endpoint.")
         
    list_id = parent_task.get("list", {}).get("id")
    if not list_id:
        # This is a critical error for this approach
        raise ClickUpError(f"Could not determine list_id for parent task {task_id} from its details.")

    params = {
        "archived": str(archived).lower(),
        "parent": task_id,
        "subtasks": "true" # Usually okay, check if API allows filtering only direct subtasks if needed
    }
    endpoint = f"/list/{list_id}/task"
    
    try:
        response_data = api._make_request("GET", endpoint, params=params)
        return response_data.get("tasks", [])
    except (ClickUpAPIError, ResourceNotFoundError) as e:
        # Error fetching the subtasks themselves
        logging.error(f"Failed to fetch subtasks for parent task {task_id} in list {list_id}: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error fetching subtasks for parent {task_id}: {e}", exc_info=True)
        raise ClickUpError(f"An unexpected error occurred fetching subtasks for parent {task_id}.") from e


def get_clickup_teams() -> List[Dict[str, Any]]:
    """
    Retrieves all teams (workspaces) accessible by the authenticated user.

    Returns:
        List[Dict[str, Any]]: A list of team/workspace dictionaries.

    Raises:
        ClickUpAPIError: If the API request fails.
        ClickUpError: For other ClickUp related errors.
    """
    api = ClickUpAPI()
    endpoint = "/team"
    try:
        response_data = api._make_request("GET", endpoint)
        return response_data.get("teams", [])
    except ClickUpAPIError as e: # ResourceNotFoundError unlikely for /team endpoint
        logging.error(f"Failed to fetch teams: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error fetching teams: {e}", exc_info=True)
        raise ClickUpError("An unexpected error occurred fetching teams.") from e


def get_clickup_team_members() -> List[Dict[str, Any]]:
    """
    Retrieves members of the default ClickUp team (workspace) set in ClickUpAPI.

    Returns:
        List[Dict[str, Any]]: A list of member dictionaries for the default team.

    Raises:
        ClickUpAPIError: If fetching teams fails.
        ResourceNotFoundError: If the default workspace ID is not found among accessible teams.
        ClickUpError: For other ClickUp related errors.
    """
    api = ClickUpAPI()
    team_id = api.workspace_id 
    try:
        all_teams = get_clickup_teams() # Handles its own errors
        for team in all_teams:
            if team.get("id") == team_id:
                return team.get("members", [])
        
        # If loop finishes, the default team wasn't found
        raise ResourceNotFoundError(f"Default team/workspace with ID {team_id} not found among accessible teams.")
        
    except (ClickUpAPIError, ResourceNotFoundError) as e:
        logging.error(f"Error getting members for default team {team_id}: {e}")
        raise
    except Exception as e: # Catch unexpected errors during processing
        logging.error(f"Unexpected error getting members for default team {team_id}: {e}", exc_info=True)
        raise ClickUpError(f"An unexpected error occurred getting members for default team {team_id}.") from e


def get_clickup_spaces(archived: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieves spaces within the default ClickUp team (workspace).

    Args:
        archived (bool): Whether to include archived spaces.

    Returns:
        List[Dict[str, Any]]: A list of space dictionaries.

    Raises:
        ClickUpAPIError: If the API request fails.
        ResourceNotFoundError: If the default workspace ID is invalid.
        ClickUpError: For other ClickUp related errors.
    """
    api = ClickUpAPI()
    team_id = api.workspace_id 
    params = {"archived": str(archived).lower()}
    endpoint = f"/team/{team_id}/space"
    
    try:
        response_data = api._make_request("GET", endpoint, params=params)
        return response_data.get("spaces", [])
    except (ClickUpAPIError, ResourceNotFoundError) as e:
        logging.error(f"Failed to get spaces for team {team_id}: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error getting spaces for team {team_id}: {e}", exc_info=True)
        raise ClickUpError(f"An unexpected error occurred fetching spaces for team {team_id}.") from e


def get_clickup_folders(space_id: str, archived: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieves folders within a specific ClickUp space.

    Args:
        space_id (str): The ID of the ClickUp space.
        archived (bool): Whether to include archived folders.

    Returns:
        List[Dict[str, Any]]: A list of folder dictionaries.

    Raises:
        ClickUpAPIError: If the API request fails.
        ResourceNotFoundError: If the space_id is invalid or not found.
        ClickUpError: For other ClickUp related errors.
    """
    api = ClickUpAPI()
    params = {"archived": str(archived).lower()}
    endpoint = f"/space/{space_id}/folder"
    
    try:
        response_data = api._make_request("GET", endpoint, params=params)
        return response_data.get("folders", [])
    except (ClickUpAPIError, ResourceNotFoundError) as e:
        logging.error(f"Failed to get folders for space {space_id}: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error getting folders for space {space_id}: {e}", exc_info=True)
        raise ClickUpError(f"An unexpected error occurred fetching folders for space {space_id}.") from e


def get_clickup_lists(folder_id: str, archived: bool = False) -> List[Dict[str, Any]]:
    """
    Retrieves lists within a specific ClickUp folder.

    Args:
        folder_id (str): The ID of the ClickUp folder.
        archived (bool): Whether to include archived lists.

    Returns:
        List[Dict[str, Any]]: A list of list dictionaries.

    Raises:
        ClickUpAPIError: If the API request fails.
        ResourceNotFoundError: If the folder_id is invalid or not found.
        ClickUpError: For other ClickUp related errors.
    """
    api = ClickUpAPI()
    params = {"archived": str(archived).lower()}
    endpoint = f"/folder/{folder_id}/list"
    
    try:
        response_data = api._make_request("GET", endpoint, params=params)
        return response_data.get("lists", [])
    except (ClickUpAPIError, ResourceNotFoundError) as e:
        logging.error(f"Failed to get lists for folder {folder_id}: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error getting lists for folder {folder_id}: {e}", exc_info=True)
        raise ClickUpError(f"An unexpected error occurred fetching lists for folder {folder_id}.") from e


def find_clickup_users(search_string: str) -> List[Dict[str, Any]]:
    """
    Useful when you don't have all the information about the user. Finds ClickUp users whose username or email contains the search string.

    Args:
        search_string (str): The string to search for within usernames or emails.

    Returns:
        List[Dict[str, Any]]: A list of matching user dictionaries, each containing 
                               'id', 'username', and 'email'. Returns an empty list 
                               if no matches are found or no teams are accessible.

    Raises:
        ClickUpAPIError: If fetching teams fails.
        ClickUpError: For other unexpected ClickUp related errors.
    """
    if not search_string:
        logging.warning("find_clickup_users called with empty search string.")
        return []

    api = ClickUpAPI()
    matching_users = []
    processed_user_ids = set()
    search_lower = search_string.lower()

    try:
        teams_data = api._make_request("GET", "/team")
        teams = teams_data.get("teams", [])

        if not teams:
            logging.warning("No teams found via API key, cannot search for users.")
            return []

        for team in teams:
            members = team.get("members", [])
            for member in members:
                user = member.get("user", {})
                user_id = user.get("id")
                api_username = user.get("username", "") # Use empty string if missing
                api_email = user.get("email", "")      # Use empty string if missing
                
                # Skip if user ID is missing or already processed
                if not user_id or user_id in processed_user_ids:
                    continue

                # Check for partial match in username or email (case-insensitive)
                # Ensure username/email are treated as empty strings if None before lower()
                username_lower = api_username.lower() if api_username else ""
                email_lower = api_email.lower() if api_email else ""
                if (search_lower in username_lower) or \
                   (search_lower in email_lower):
                    matching_users.append({
                        "id": str(user_id),
                        "username": api_username,
                        "email": api_email
                    })
                    processed_user_ids.add(user_id) # Add to set to avoid duplicates

        logging.info(f"Found {len(matching_users)} users matching '{search_string}'.")
        return matching_users

    except ClickUpAPIError as e:
        logging.error(f"Failed to fetch teams while searching for users matching '{search_string}': {e}")
        raise # Re-raise API errors
    except Exception as e:
        logging.error(f"Unexpected error searching for users matching '{search_string}': {e}", exc_info=True)
        raise ClickUpError(f"An unexpected error occurred while searching for users matching '{search_string}'.") from e
