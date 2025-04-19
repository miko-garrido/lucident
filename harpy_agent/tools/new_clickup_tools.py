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
        except ResourceNotFoundError: # Explicitly catch and re-raise before the generic Exception
             raise
        except Exception as e: # Catch any other unexpected error
             logging.error(f"Unexpected error finding user ID for '{username}': {e}", exc_info=True)
             raise ClickUpError(f"An unexpected error occurred while finding user ID for '{username}'.") from e

# --- Standalone ClickUp API Functions (GET Requests) ---

# --- Authorization ---
def get_authorized_user() -> Dict[str, Any]:
    """
    Gets the details of the user associated with the API token.
    
    Returns:
        Dict[str, Any]: A dictionary containing the authorized user's details.
    """
    # Reference: https://developer.clickup.com/reference/getauthorizeduser
    api = ClickUpAPI()
    endpoint = "/user"
    return api._make_request("GET", endpoint)

def get_authorized_teams() -> Dict[str, Any]:
    """
    Gets the Workspaces (Teams) accessible to the authorized user.
    
    Returns:
        Dict[str, Any]: A dictionary containing the list of authorized teams.
    """
    # Reference: https://developer.clickup.com/reference/getauthorizedteams
    api = ClickUpAPI()
    endpoint = "/team"
    return api._make_request("GET", endpoint)

# --- Comments ---
def get_task_comments(task_id: str, start: Optional[int] = None, start_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Gets comments for a specific task.
    
    Args:
        task_id: The ID of the task to get comments for.
        start: The timestamp (Unix time in ms) to start fetching comments from (optional).
        start_id: The comment ID to fetch comments after (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of comments.
    """
    # Reference: https://developer.clickup.com/reference/gettaskcomments
    api = ClickUpAPI()
    endpoint = f"/task/{task_id}/comment"
    params = {}
    if start is not None:
        params["start"] = start
    if start_id is not None:
        params["start_id"] = start_id
    return api._make_request("GET", endpoint, params=params)

def get_chat_view_comments(view_id: str, start: Optional[int] = None, start_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Gets comments from a Chat view.
    
    Args:
        view_id: The ID of the Chat view.
        start: The timestamp (Unix time in ms) to start fetching comments from (optional).
        start_id: The comment ID to fetch comments after (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of comments for the chat view.
    """
    # Reference: https://developer.clickup.com/reference/getchatviewcomments
    api = ClickUpAPI()
    endpoint = f"/view/{view_id}/comment"
    params = {}
    if start is not None:
        params["start"] = start
    if start_id is not None:
        params["start_id"] = start_id
    return api._make_request("GET", endpoint, params=params)

def get_list_comments(list_id: str, start: Optional[int] = None, start_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Gets comments for a specific list.
    
    Args:
        list_id: The ID of the list.
        start: The timestamp (Unix time in ms) to start fetching comments from (optional).
        start_id: The comment ID to fetch comments after (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of comments for the list.
    """
    # Reference: https://developer.clickup.com/reference/getlistcomments
    api = ClickUpAPI()
    endpoint = f"/list/{list_id}/comment"
    params = {}
    if start is not None:
        params["start"] = start
    if start_id is not None:
        params["start_id"] = start_id
    return api._make_request("GET", endpoint, params=params)

def get_threaded_comments(comment_id: str) -> Dict[str, Any]:
    """
    Gets replies to a specific comment thread. Requires the comment ID of the parent comment.
    
    Args:
        comment_id: The ID of the parent comment.

    Returns:
        Dict[str, Any]: A dictionary containing the list of threaded replies.
    """
    # Reference: https://developer.clickup.com/reference/getthreadedcomments
    api = ClickUpAPI()
    endpoint = f"/comment/{comment_id}/comments"
    return api._make_request("GET", endpoint)

# --- Custom Task Types ---
def get_custom_task_types(team_id: str) -> Dict[str, Any]:
    """
    Gets the Custom Task Types available in a Workspace.
    
    Args:
        team_id: The ID of the Workspace (Team).

    Returns:
        Dict[str, Any]: A dictionary containing the custom task types.
    """
    # Reference: https://developer.clickup.com/reference/getcustomitems
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/custom_item"
    return api._make_request("GET", endpoint)

# --- Custom Fields ---
def get_list_custom_fields(list_id: str) -> Dict[str, Any]:
    """
    Gets the Custom Fields available for a specific List.
    
    Args:
        list_id: The ID of the List.

    Returns:
        Dict[str, Any]: A dictionary containing the list of custom fields for the list.
    """
    # Reference: https://developer.clickup.com/reference/getaccessiblecustomfields
    api = ClickUpAPI()
    endpoint = f"/list/{list_id}/field"
    return api._make_request("GET", endpoint)

def get_folder_available_custom_fields(folder_id: str) -> Dict[str, Any]:
    """
    Gets the available Custom Fields for a Folder.
    
    Args:
        folder_id: The ID of the Folder.

    Returns:
        Dict[str, Any]: A dictionary containing the list of custom fields for the folder.
    """
    # Reference: https://developer.clickup.com/reference/getfolderavailablefields
    api = ClickUpAPI()
    endpoint = f"/folder/{folder_id}/field"
    return api._make_request("GET", endpoint)

def get_space_available_custom_fields(space_id: str) -> Dict[str, Any]:
    """
    Gets the available Custom Fields for a Space.
    
    Args:
        space_id: The ID of the Space.

    Returns:
        Dict[str, Any]: A dictionary containing the list of custom fields for the space.
    """
    # Reference: https://developer.clickup.com/reference/getspaceavailablefields
    api = ClickUpAPI()
    endpoint = f"/space/{space_id}/field"
    return api._make_request("GET", endpoint)

def get_team_available_custom_fields(team_id: str) -> Dict[str, Any]:
    """
    Gets the available Custom Fields for a Workspace (Team).
    
    Args:
        team_id: The ID of the Workspace (Team).

    Returns:
        Dict[str, Any]: A dictionary containing the list of custom fields for the workspace.
    """
    # Reference: https://developer.clickup.com/reference/getteamavailablefields
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/field"
    return api._make_request("GET", endpoint)

# --- Docs ---
def search_docs(team_id: str, query: str, include_content: Optional[bool] = None,
                 include_locations: Optional[bool] = None, owner_ids: Optional[List[int]] = None,
                 location_ids: Optional[List[int]] = None, location_type: Optional[str] = None,
                 parent_ids: Optional[List[int]] = None, doc_ids: Optional[List[str]] = None,
                 page_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Searches for Docs within a Workspace.
    
    Args:
        team_id: The ID of the Workspace (Team).
        query: The search query string.
        include_content: Whether to include the content of the Docs (optional).
        include_locations: Whether to include location information (optional).
        owner_ids: Filter by owner user IDs (optional).
        location_ids: Filter by location IDs (Space, Folder, List) (optional).
        location_type: Filter by location type ('space', 'folder', 'list') (optional).
        parent_ids: Filter by parent Doc IDs (optional).
        doc_ids: Filter by specific Doc IDs (optional).
        page_ids: Filter by specific Page IDs (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the search results for Docs.
    """
    # Reference: https://developer.clickup.com/reference/searchdocs
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/docs"
    params = {"query": query}
    if include_content is not None:
        params["include_content"] = str(include_content).lower()
    if include_locations is not None:
        params["include_locations"] = str(include_locations).lower()
    if owner_ids:
        params["owner_ids[]"] = owner_ids
    if location_ids:
        params["location_ids[]"] = location_ids
    if location_type:
        params["location_type"] = location_type
    if parent_ids:
        params["parent_ids[]"] = parent_ids
    if doc_ids:
        params["doc_ids[]"] = doc_ids
    if page_ids:
        params["page_ids[]"] = page_ids
    return api._make_request("GET", endpoint, params=params)

def get_doc(doc_id: str, include_content: Optional[bool] = None) -> Dict[str, Any]:
    """
    Gets details about a specific Doc.
    
    Args:
        doc_id: The ID of the Doc.
        include_content: Whether to include the content of the Doc (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the Doc details.
    """
    # Reference: https://developer.clickup.com/reference/getdoc
    api = ClickUpAPI()
    endpoint = f"/doc/{doc_id}"
    params = {}
    if include_content is not None:
        params["include_content"] = str(include_content).lower()
    return api._make_request("GET", endpoint, params=params)

def get_doc_page_listing(doc_id: str) -> Dict[str, Any]:
    """
    Gets a listing of pages within a Doc.
    
    Args:
        doc_id: The ID of the Doc.

    Returns:
        Dict[str, Any]: A dictionary containing the page listing for the Doc.
    """
    # Reference: https://developer.clickup.com/reference/getdocpagelisting
    api = ClickUpAPI()
    endpoint = f"/doc/{doc_id}/pages/listing"
    return api._make_request("GET", endpoint)

def get_doc_pages(doc_id: str, include_content: Optional[bool] = None) -> Dict[str, Any]:
    """
    Gets the pages within a Doc, optionally including their content.
    
    Args:
        doc_id: The ID of the Doc.
        include_content: Whether to include the content of the pages (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the pages within the Doc.
    """
    # Reference: https://developer.clickup.com/reference/getdocpages
    api = ClickUpAPI()
    endpoint = f"/doc/{doc_id}/pages"
    params = {}
    if include_content is not None:
        params["include_content"] = str(include_content).lower()
    return api._make_request("GET", endpoint, params=params)

def get_page(page_id: str, include_content: Optional[bool] = None) -> Dict[str, Any]:
    """
    Gets details about a specific page within a Doc.
    
    Args:
        page_id: The ID of the page.
        include_content: Whether to include the content of the page (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the page details.
    """
    # Reference: https://developer.clickup.com/reference/getpage
    api = ClickUpAPI()
    endpoint = f"/page/{page_id}"
    params = {}
    if include_content is not None:
        params["include_content"] = str(include_content).lower()
    return api._make_request("GET", endpoint, params=params)

# --- Folders ---
def get_folders(space_id: str, archived: Optional[bool] = False) -> Dict[str, Any]:
    """
    Gets Folders within a specific Space.
    
    Args:
        space_id: The ID of the Space.
        archived: Whether to include archived Folders (default: False).

    Returns:
        Dict[str, Any]: A dictionary containing the list of Folders.
    """
    # Reference: https://developer.clickup.com/reference/getfolders
    api = ClickUpAPI()
    endpoint = f"/space/{space_id}/folder"
    params = {"archived": str(archived).lower()}
    return api._make_request("GET", endpoint, params=params)

def get_folder(folder_id: str) -> Dict[str, Any]:
    """
    Gets details about a specific Folder.
    
    Args:
        folder_id: The ID of the Folder.

    Returns:
        Dict[str, Any]: A dictionary containing the Folder details.
    """
    # Reference: https://developer.clickup.com/reference/getfolder
    api = ClickUpAPI()
    endpoint = f"/folder/{folder_id}"
    return api._make_request("GET", endpoint)

# --- Goals ---
def get_goals(team_id: str, include_completed: Optional[bool] = None) -> Dict[str, Any]:
    """
    Gets Goals from a Workspace.
    
    Args:
        team_id: The ID of the Workspace (Team).
        include_completed: Whether to include completed Goals (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of Goals.
    """
    # Reference: https://developer.clickup.com/reference/getgoals
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/goal"
    params = {}
    if include_completed is not None:
        params["include_completed"] = str(include_completed).lower()
    return api._make_request("GET", endpoint, params=params)

def get_goal(goal_id: str) -> Dict[str, Any]:
    """
    Gets details about a specific Goal.
    
    Args:
        goal_id: The ID of the Goal.

    Returns:
        Dict[str, Any]: A dictionary containing the Goal details.
    """
    # Reference: https://developer.clickup.com/reference/getgoal
    api = ClickUpAPI()
    endpoint = f"/goal/{goal_id}"
    return api._make_request("GET", endpoint)

# --- Guests ---
def get_guest(team_id: str, guest_id: int) -> Dict[str, Any]:
    """
    Gets information about a specific Guest in a Workspace.
    
    Args:
        team_id: The ID of the Workspace (Team).
        guest_id: The ID of the Guest user.

    Returns:
        Dict[str, Any]: A dictionary containing the Guest details.
    """
    # Reference: https://developer.clickup.com/reference/getguest
    api = ClickUpAPI()
    # Note: API docs path is /team/{team_id}/guest/{guest_id} but reference json links to /guest/{guest_id}
    # Let's follow the docs path as it seems more standard.
    endpoint = f"/team/{team_id}/guest/{guest_id}"
    return api._make_request("GET", endpoint)

# --- Lists ---
def get_lists(folder_id: str, archived: Optional[bool] = False) -> Dict[str, Any]:
    """
    Gets Lists within a specific Folder.
    
    Args:
        folder_id: The ID of the Folder.
        archived: Whether to include archived Lists (default: False).

    Returns:
        Dict[str, Any]: A dictionary containing the list of Lists in the Folder.
    """
    # Reference: https://developer.clickup.com/reference/getlists
    api = ClickUpAPI()
    endpoint = f"/folder/{folder_id}/list"
    params = {"archived": str(archived).lower()}
    return api._make_request("GET", endpoint, params=params)

def get_folderless_lists(space_id: str, archived: Optional[bool] = False) -> Dict[str, Any]:
    """
    Gets Lists in a Space that are not contained within any Folder.
    
    Args:
        space_id: The ID of the Space.
        archived: Whether to include archived Lists (default: False).

    Returns:
        Dict[str, Any]: A dictionary containing the list of folderless Lists in the Space.
    """
    # Reference: https://developer.clickup.com/reference/getfolderlesslists
    api = ClickUpAPI()
    endpoint = f"/space/{space_id}/list"
    params = {"archived": str(archived).lower()}
    return api._make_request("GET", endpoint, params=params)

def get_list(list_id: str) -> Dict[str, Any]:
    """
    Gets details about a specific List.
    
    Args:
        list_id: The ID of the List.

    Returns:
        Dict[str, Any]: A dictionary containing the List details.
    """
    # Reference: https://developer.clickup.com/reference/getlist
    api = ClickUpAPI()
    endpoint = f"/list/{list_id}"
    return api._make_request("GET", endpoint)

# --- Members ---
def get_task_members(task_id: str) -> List[Dict[str, Any]]:
    """
    Gets members (users) assigned to or associated with a task.
    
    Args:
        task_id: The ID of the task.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a member associated with the task.
    """
    # Reference: https://developer.clickup.com/reference/gettaskmembers
    api = ClickUpAPI()
    endpoint = f"/task/{task_id}/member"
    # The API returns a list directly under the 'members' key. Adjusting return type.
    response = api._make_request("GET", endpoint)
    return response.get("members", []) # Assuming response structure {'members': [...]}

def get_list_members(list_id: str) -> List[Dict[str, Any]]:
    """
    Gets members (users) who have access to a specific List.
    
    Args:
        list_id: The ID of the List.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a member with access to the list.
    """
    # Reference: https://developer.clickup.com/reference/getlistmembers
    api = ClickUpAPI()
    endpoint = f"/list/{list_id}/member"
     # The API returns a list directly under the 'members' key. Adjusting return type.
    response = api._make_request("GET", endpoint)
    return response.get("members", []) # Assuming response structure {'members': [...]}

# --- Roles ---
def get_custom_roles(team_id: str) -> Dict[str, Any]:
    """
    Gets the custom roles available in a Workspace.
    
    Args:
        team_id: The ID of the Workspace (Team).

    Returns:
        Dict[str, Any]: A dictionary containing the list of custom roles.
    """
    # Reference: https://developer.clickup.com/reference/getcustomroles
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/customroles"
    return api._make_request("GET", endpoint)

# --- Shared Hierarchy ---
def get_shared_hierarchy(team_id: str) -> Dict[str, Any]:
    """
    Gets the shared hierarchy for the authorized user in a Workspace.
    
    Args:
        team_id: The ID of the Workspace (Team).

    Returns:
        Dict[str, Any]: A dictionary containing the shared hierarchy details.
    """
    # Reference: https://developer.clickup.com/reference/sharedhierarchy
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/shared"
    return api._make_request("GET", endpoint)

# --- Spaces ---
def get_spaces(team_id: str, archived: Optional[bool] = False) -> Dict[str, Any]:
    """
    Gets Spaces within a specific Workspace.
    
    Args:
        team_id: The ID of the Workspace (Team).
        archived: Whether to include archived Spaces (default: False).

    Returns:
        Dict[str, Any]: A dictionary containing the list of Spaces.
    """
    # Reference: https://developer.clickup.com/reference/getspaces
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/space"
    params = {"archived": str(archived).lower()}
    return api._make_request("GET", endpoint, params=params)

def get_space(space_id: str) -> Dict[str, Any]:
    """
    Gets details about a specific Space.
    
    Args:
        space_id: The ID of the Space.

    Returns:
        Dict[str, Any]: A dictionary containing the Space details.
    """
    # Reference: https://developer.clickup.com/reference/getspace
    api = ClickUpAPI()
    endpoint = f"/space/{space_id}"
    return api._make_request("GET", endpoint)

# --- Tags ---
def get_space_tags(space_id: str) -> Dict[str, Any]:
    """
    Gets Tags available in a specific Space.
    
    Args:
        space_id: The ID of the Space.

    Returns:
        Dict[str, Any]: A dictionary containing the list of tags for the Space.
    """
    # Reference: https://developer.clickup.com/reference/getspacetags
    api = ClickUpAPI()
    endpoint = f"/space/{space_id}/tag"
    return api._make_request("GET", endpoint)

# --- Tasks ---
def get_tasks(list_id: str, archived: Optional[bool] = False, 
              include_markdown_description: Optional[bool] = None, page: Optional[int] = None,
              order_by: Optional[str] = None, reverse: Optional[bool] = None, 
              subtasks: Optional[bool] = None, space_ids: Optional[List[str]] = None,
              project_ids: Optional[List[str]] = None, list_ids: Optional[List[str]] = None, 
              statuses: Optional[List[str]] = None, include_closed: Optional[bool] = None, 
              assignees: Optional[List[str]] = None, tags: Optional[List[str]] = None, 
              due_date_gt: Optional[int] = None, due_date_lt: Optional[int] = None, 
              date_created_gt: Optional[int] = None, date_created_lt: Optional[int] = None,
              date_updated_gt: Optional[int] = None, date_updated_lt: Optional[int] = None, 
              date_done_gt: Optional[int] = None, date_done_lt: Optional[int] = None, 
              custom_fields: Optional[str] = None, # JSON string [{ "field_id": "", "operator": "", "value": ""}]
              custom_items: Optional[List[int]] = None, 
              parent: Optional[str] = None, include_subtasks: Optional[bool] = None, # Deprecated: use `subtasks`
              ) -> Dict[str, Any]:
    """
    Gets tasks from a specific List, with extensive filtering options.
    
    Args:
        list_id: The ID of the List to get tasks from.
        archived: Whether to include archived tasks (default: False).
        include_markdown_description: Return description in Markdown format (optional).
        page: Page number for pagination (optional).
        order_by: Field to order tasks by (e.g., 'due_date', 'priority') (optional).
        reverse: Reverse the order of tasks (optional).
        subtasks: Include subtasks (true), exclude subtasks (false), or include both tasks and subtasks ('true_all') (optional).
        space_ids: Filter by Space IDs (optional).
        project_ids: Filter by Folder IDs (previously Projects) (optional).
        list_ids: Filter by List IDs (optional).
        statuses: Filter by task statuses (case-insensitive) (optional).
        include_closed: Include closed tasks (optional).
        assignees: Filter by assignee user IDs (optional).
        tags: Filter by tag names (optional).
        due_date_gt: Filter by due date greater than (Unix time in ms) (optional).
        due_date_lt: Filter by due date less than (Unix time in ms) (optional).
        date_created_gt: Filter by creation date greater than (Unix time in ms) (optional).
        date_created_lt: Filter by creation date less than (Unix time in ms) (optional).
        date_updated_gt: Filter by update date greater than (Unix time in ms) (optional).
        date_updated_lt: Filter by update date less than (Unix time in ms) (optional).
        date_done_gt: Filter by completion date greater than (Unix time in ms) (optional).
        date_done_lt: Filter by completion date less than (Unix time in ms) (optional).
        custom_fields: Filter by custom fields (JSON string) (optional). Example: '[{"field_id":"...", "operator":"=", "value":"..."}]'
        custom_items: Filter by Custom Task Types (provide IDs) (optional).
        parent: Filter by parent task ID (optional).
        include_subtasks: Deprecated alias for `subtasks` (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of tasks matching the criteria.
    """
    # Reference: https://developer.clickup.com/reference/gettasks
    api = ClickUpAPI()
    endpoint = f"/list/{list_id}/task"
    params = {"archived": str(archived).lower()}
    if include_markdown_description is not None:
        params["include_markdown_description"] = str(include_markdown_description).lower()
    if page is not None:
        params["page"] = page
    if order_by:
        params["order_by"] = order_by
    if reverse is not None:
        params["reverse"] = str(reverse).lower()
    if subtasks is not None:
        params["subtasks"] = str(subtasks).lower() # API expects string 'true', 'false', or 'true_all'
    if space_ids:
        params["space_ids[]"] = space_ids
    if project_ids:
        params["project_ids[]"] = project_ids # Note: API calls it project_ids
    if list_ids:
        params["list_ids[]"] = list_ids
    if statuses:
        params["statuses[]"] = statuses
    if include_closed is not None:
        params["include_closed"] = str(include_closed).lower()
    if assignees:
        params["assignees[]"] = assignees
    if tags:
        params["tags[]"] = tags
    if due_date_gt is not None:
        params["due_date_gt"] = due_date_gt
    if due_date_lt is not None:
        params["due_date_lt"] = due_date_lt
    if date_created_gt is not None:
        params["date_created_gt"] = date_created_gt
    if date_created_lt is not None:
        params["date_created_lt"] = date_created_lt
    if date_updated_gt is not None:
        params["date_updated_gt"] = date_updated_gt
    if date_updated_lt is not None:
        params["date_updated_lt"] = date_updated_lt
    if date_done_gt is not None:
        params["date_done_gt"] = date_done_gt
    if date_done_lt is not None:
        params["date_done_lt"] = date_done_lt
    if custom_fields:
         # Pass the raw JSON string as provided by the user
        params["custom_fields"] = custom_fields
    if custom_items:
        params["custom_items[]"] = custom_items
    if parent:
        params["parent"] = parent
    # Handle deprecated include_subtasks if subtasks not set
    if include_subtasks is not None and subtasks is None:
        params["subtasks"] = str(include_subtasks).lower() # Map to subtasks

    return api._make_request("GET", endpoint, params=params)

def get_task(task_id: str, include_subtasks: Optional[bool] = None, 
             include_markdown_description: Optional[bool] = None, custom_task_ids: Optional[bool] = None, team_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Gets details about a specific task.
    
    Args:
        task_id: The ID of the task (can be the canonical ID or custom task ID).
        include_subtasks: Include subtasks in the response (optional).
        include_markdown_description: Return description in Markdown format (optional).
        custom_task_ids: If true, treats task_id as a custom task ID. Requires team_id. (optional)
        team_id: The Workspace (Team) ID, required if custom_task_ids is true. (optional)

    Returns:
        Dict[str, Any]: A dictionary containing the task details.
    """
    # Reference: https://developer.clickup.com/reference/gettask
    api = ClickUpAPI()
    params = {}
    if include_subtasks is not None:
        params["include_subtasks"] = str(include_subtasks).lower()
    if include_markdown_description is not None:
        params["include_markdown_description"] = str(include_markdown_description).lower()
    
    endpoint = f"/task/{task_id}"
    
    if custom_task_ids:
        if not team_id:
             raise InvalidInputError("team_id is required when custom_task_ids is true.")
        params["custom_task_ids"] = "true"
        params["team_id"] = team_id
        # The endpoint for custom task IDs is different according to docs: /team/{team_id}/task/{task_id}
        # However, the primary GET /task/{task_id} endpoint docs mention the custom_task_ids param.
        # Let's stick to the documented parameters for the main endpoint first.
        # If issues arise, consider changing endpoint to f"/team/{team_id}/task/{task_id}" when custom_task_ids=True
        
    return api._make_request("GET", endpoint, params=params)

def get_filtered_team_tasks(team_id: str, page: Optional[int] = None, 
                             order_by: Optional[str] = None, reverse: Optional[bool] = None, 
                             subtasks: Optional[bool] = None, space_ids: Optional[List[str]] = None,
                             project_ids: Optional[List[str]] = None, list_ids: Optional[List[str]] = None, 
                             statuses: Optional[List[str]] = None, include_closed: Optional[bool] = None, 
                             assignees: Optional[List[str]] = None, tags: Optional[List[str]] = None, 
                             due_date_gt: Optional[int] = None, due_date_lt: Optional[int] = None, 
                             date_created_gt: Optional[int] = None, date_created_lt: Optional[int] = None,
                             date_updated_gt: Optional[int] = None, date_updated_lt: Optional[int] = None, 
                             date_done_gt: Optional[int] = None, date_done_lt: Optional[int] = None, 
                             custom_fields: Optional[str] = None, # JSON string
                             custom_items: Optional[List[int]] = None, 
                             parent: Optional[str] = None, include_markdown_description: Optional[bool] = None
                             ) -> Dict[str, Any]:
    """
    Gets tasks for a Workspace (Team), filtered by various criteria. Similar to get_tasks but workspace-wide.
    
    Args:
        team_id: The ID of the Workspace (Team).
        page: Page number for pagination (optional).
        order_by: Field to order tasks by (e.g., 'due_date', 'priority') (optional).
        reverse: Reverse the order of tasks (optional).
        subtasks: Include subtasks (true), exclude subtasks (false), or include both tasks and subtasks ('true_all') (optional).
        space_ids: Filter by Space IDs (optional).
        project_ids: Filter by Folder IDs (previously Projects) (optional).
        list_ids: Filter by List IDs (optional).
        statuses: Filter by task statuses (case-insensitive) (optional).
        include_closed: Include closed tasks (optional).
        assignees: Filter by assignee user IDs (optional).
        tags: Filter by tag names (optional).
        due_date_gt: Filter by due date greater than (Unix time in ms) (optional).
        due_date_lt: Filter by due date less than (Unix time in ms) (optional).
        date_created_gt: Filter by creation date greater than (Unix time in ms) (optional).
        date_created_lt: Filter by creation date less than (Unix time in ms) (optional).
        date_updated_gt: Filter by update date greater than (Unix time in ms) (optional).
        date_updated_lt: Filter by update date less than (Unix time in ms) (optional).
        date_done_gt: Filter by completion date greater than (Unix time in ms) (optional).
        date_done_lt: Filter by completion date less than (Unix time in ms) (optional).
        custom_fields: Filter by custom fields (JSON string) (optional). Example: '[{"field_id":"...", "operator":"=", "value":"..."}]'
        custom_items: Filter by Custom Task Types (provide IDs) (optional).
        parent: Filter by parent task ID (optional).
        include_markdown_description: Return description in Markdown format (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of tasks matching the criteria for the workspace.
    """
    # Reference: https://developer.clickup.com/reference/getfilteredteamtasks
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/task"
    params = {}
    if page is not None:
        params["page"] = page
    if order_by:
        params["order_by"] = order_by
    if reverse is not None:
        params["reverse"] = str(reverse).lower()
    if subtasks is not None:
        params["subtasks"] = str(subtasks).lower()
    if space_ids:
        params["space_ids[]"] = space_ids
    if project_ids:
        params["project_ids[]"] = project_ids
    if list_ids:
        params["list_ids[]"] = list_ids
    if statuses:
        params["statuses[]"] = statuses
    if include_closed is not None:
        params["include_closed"] = str(include_closed).lower()
    if assignees:
        params["assignees[]"] = assignees
    if tags:
        params["tags[]"] = tags
    if due_date_gt is not None:
        params["due_date_gt"] = due_date_gt
    if due_date_lt is not None:
        params["due_date_lt"] = due_date_lt
    if date_created_gt is not None:
        params["date_created_gt"] = date_created_gt
    if date_created_lt is not None:
        params["date_created_lt"] = date_created_lt
    if date_updated_gt is not None:
        params["date_updated_gt"] = date_updated_gt
    if date_updated_lt is not None:
        params["date_updated_lt"] = date_updated_lt
    if date_done_gt is not None:
        params["date_done_gt"] = date_done_gt
    if date_done_lt is not None:
        params["date_done_lt"] = date_done_lt
    if custom_fields:
        params["custom_fields"] = custom_fields
    if custom_items:
        params["custom_items[]"] = custom_items
    if parent:
        params["parent"] = parent
    if include_markdown_description is not None:
        params["include_markdown_description"] = str(include_markdown_description).lower()
        
    return api._make_request("GET", endpoint, params=params)

def get_task_time_in_status(task_id: str, custom_task_ids: Optional[bool] = None, team_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Gets the time spent by a task in each status.
    
    Args:
        task_id: The ID of the task (can be the canonical ID or custom task ID).
        custom_task_ids: If true, treats task_id as a custom task ID. Requires team_id. (optional)
        team_id: The Workspace (Team) ID, required if custom_task_ids is true. (optional)

    Returns:
        Dict[str, Any]: A dictionary containing the time in status details for the task.
    """
    # Reference: https://developer.clickup.com/reference/gettaskstimeinstatus
    api = ClickUpAPI()
    endpoint = f"/task/{task_id}/time_in_status"
    params = {}
    if custom_task_ids:
        if not team_id:
            raise InvalidInputError("team_id is required when custom_task_ids is true.")
        params["custom_task_ids"] = "true"
        params["team_id"] = team_id
        # Docs indicate the endpoint changes for custom IDs, but also list the query param.
        # Let's use the query param approach first.
        # endpoint = f"/team/{team_id}/task/{task_id}/time_in_status"
        
    return api._make_request("GET", endpoint, params=params)

def get_bulk_tasks_time_in_status(task_ids: List[str], custom_task_ids: Optional[bool] = None, team_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Gets the time spent in status for multiple tasks.
    
    Args:
        task_ids: A list of task IDs (canonical or custom).
        custom_task_ids: If true, treats task_ids as custom task IDs. Requires team_id. (optional)
        team_id: The Workspace (Team) ID, required if custom_task_ids is true. (optional)

    Returns:
        Dict[str, Any]: A dictionary containing the time in status details for the specified tasks.
    """
    # Reference: https://developer.clickup.com/reference/getbulktaskstimeinstatus
    api = ClickUpAPI()
    # The documented endpoint is GET /task/bulk_time_in_status/task_ids?task_ids=t1&task_ids=t2...
    # It doesn't use list_id or team_id in the path.
    endpoint = "/task/bulk_time_in_status/task_ids"
    params = {"task_ids": task_ids} # Let requests handle list serialization
    if custom_task_ids:
         if not team_id:
             raise InvalidInputError("team_id is required when custom_task_ids is true.")
         params["custom_task_ids"] = "true"
         params["team_id"] = team_id
         # Docs suggest endpoint changes for custom IDs: /team/{team_id}/task/bulk_time_in_status/task_ids
         # endpoint = f"/team/{team_id}/task/bulk_time_in_status/task_ids"
         
    return api._make_request("GET", endpoint, params=params)

# --- Templates ---
def get_task_templates(team_id: str, page: int, space_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Gets task templates for a Workspace.
    
    Args:
        team_id: The ID of the Workspace (Team).
        page: Page number for pagination (templates are returned 100 at a time).
        space_id: Optional Space ID to filter templates. If provided, only templates available
                  to the specific Space are returned. Otherwise, Workspace-level templates are returned.

    Returns:
        Dict[str, Any]: A dictionary containing the list of task templates.
    """
    # Reference: https://developer.clickup.com/reference/gettasktemplates
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/template"
    params: Dict[str, Any] = {"page": page}
    if space_id is not None:
        params["space_id"] = space_id
    return api._make_request("GET", endpoint, params=params)

# --- Workspaces ---
def get_workspace_seats(team_id: str) -> Dict[str, Any]:
    """
    Gets the number of members and guests in a Workspace.
    
    Args:
        team_id: The ID of the Workspace (Team).

    Returns:
        Dict[str, Any]: A dictionary containing the workspace seat information.
    """
    # Reference: https://developer.clickup.com/reference/getworkspaceseats
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/seats"
    return api._make_request("GET", endpoint)

def get_workspace_plan(team_id: str) -> Dict[str, Any]:
    """
    Gets the subscription plan details for a Workspace.
    
    Args:
        team_id: The ID of the Workspace (Team).

    Returns:
        Dict[str, Any]: A dictionary containing the workspace plan details.
    """
    # Reference: https://developer.clickup.com/reference/getworkspaceplan
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/plan"
    return api._make_request("GET", endpoint)

# --- User Groups (Teams/Permissions) ---
def get_user_groups(team_id: Optional[str] = None, group_ids: Optional[str] = None) -> Dict[str, Any]:
    """
    Gets user groups (Teams for permissions) in the Workspace.
    
    Args:
        team_id: The ID of the Workspace (Team). Docs say optional, but usually needed?
                 Let's make it optional as per docs.
        group_ids: Comma-separated list of group IDs to filter by (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of user groups.
    """
    # Reference: https://developer.clickup.com/reference/getteams1
    api = ClickUpAPI()
    # Docs endpoint is /group, reference JSON has /team/{team_id}/group. Use /group.
    endpoint = "/group"
    params = {}
    if team_id: # Add team_id if provided, though docs don't explicitly list it as param for /group
         params["team_id"] = team_id # This might not be correct based on /group docs, but included for potential need
    if group_ids:
        params["group_ids"] = group_ids
    return api._make_request("GET", endpoint, params=params)

# --- Time Tracking ---
def get_time_entries(team_id: str, start_date: Optional[int] = None, 
                     end_date: Optional[int] = None, assignee: Optional[str] = None,
                     include_task_tags: Optional[bool] = None, include_location_names: Optional[bool] = None,
                     space_id: Optional[str] = None, folder_id: Optional[str] = None,
                     list_id: Optional[str] = None, task_id: Optional[str] = None,
                     custom_task_ids: Optional[bool] = None, task_team_id: Optional[str] = None # team_id for custom task ID
                     ) -> Dict[str, Any]:
    """
    Gets time entries within a date range for a Workspace (Team).
    
    Args:
        team_id: The ID of the Workspace (Team).
        start_date: Start timestamp (Unix time in ms) (optional).
        end_date: End timestamp (Unix time in ms) (optional).
        assignee: Filter by user ID(s) (comma-separated string or list) (optional).
        include_task_tags: Include task tags in the response (optional).
        include_location_names: Include Folder and List names (optional).
        space_id: Filter by Space ID (optional).
        folder_id: Filter by Folder ID (optional).
        list_id: Filter by List ID (optional).
        task_id: Filter by Task ID (canonical or custom) (optional).
        custom_task_ids: If true, treats task_id as a custom task ID. Requires task_team_id. (optional)
        task_team_id: The Workspace (Team) ID for the custom task ID lookup. Required if custom_task_ids is true and task_id is provided. (optional)

    Returns:
        Dict[str, Any]: A dictionary containing the list of time entries matching the criteria.
    """
    # Reference: https://developer.clickup.com/reference/gettimeentrieswithinadaterange
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/time_entries"
    params: Dict[str, Any] = {}
    if start_date is not None:
        params["start_date"] = start_date
    if end_date is not None:
        params["end_date"] = end_date
    if assignee:
         # Docs say comma separated string of user ids
         params["assignee"] = assignee if isinstance(assignee, str) else ",".join(map(str, assignee))
    if include_task_tags is not None:
        params["include_task_tags"] = str(include_task_tags).lower()
    if include_location_names is not None:
        params["include_location_names"] = str(include_location_names).lower()
    if space_id:
        params["space_id"] = space_id
    if folder_id:
        params["folder_id"] = folder_id
    if list_id:
        params["list_id"] = list_id
    if task_id:
        params["task_id"] = task_id
        if custom_task_ids:
            if not task_team_id:
                raise InvalidInputError("task_team_id is required when custom_task_ids is true and task_id is provided.")
            params["custom_task_ids"] = "true"
            params["team_id"] = task_team_id # Pass the correct team_id for the custom task ID lookup
    
    return api._make_request("GET", endpoint, params=params)

def get_singular_time_entry(team_id: str, timer_id: str, include_task_tags: Optional[bool] = None, 
                            include_location_names: Optional[bool] = None) -> Dict[str, Any]:
    """
    Gets details for a specific time entry.
    
    Args:
        team_id: The ID of the Workspace (Team).
        timer_id: The ID of the time entry (timer_id).
        include_task_tags: Include task tags in the response (optional).
        include_location_names: Include Folder and List names (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the details of the specified time entry.
    """
    # Reference: https://developer.clickup.com/reference/getsingulartimeentry
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/time_entries/{timer_id}"
    params = {}
    if include_task_tags is not None:
        params["include_task_tags"] = str(include_task_tags).lower()
    if include_location_names is not None:
        params["include_location_names"] = str(include_location_names).lower()
    return api._make_request("GET", endpoint, params=params)

def get_time_entry_history(team_id: str, timer_id: str) -> Dict[str, Any]:
    """
    Gets the history of changes for a specific time entry.
    
    Args:
        team_id: The ID of the Workspace (Team).
        timer_id: The ID of the time entry.

    Returns:
        Dict[str, Any]: A dictionary containing the history of the specified time entry.
    """
    # Reference: https://developer.clickup.com/reference/gettimeentryhistory
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/time_entries/{timer_id}/history"
    return api._make_request("GET", endpoint)

def get_running_time_entry(team_id: str) -> Dict[str, Any]:
    """
    Gets the currently running time entry for the authorized user in a Workspace.
    
    Args:
        team_id: The ID of the Workspace (Team).

    Returns:
        Dict[str, Any]: A dictionary containing the details of the running time entry, or an empty dict if none.
    """
    # Reference: https://developer.clickup.com/reference/getrunningtimeentry
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/time_entries/current"
    return api._make_request("GET", endpoint)

def get_all_time_entry_tags(team_id: str) -> Dict[str, Any]:
    """
    Gets all tags used in time entries for a Workspace.
    
    Args:
        team_id: The ID of the Workspace (Team).

    Returns:
        Dict[str, Any]: A dictionary containing the list of all time entry tags.
    """
    # Reference: https://developer.clickup.com/reference/getalltagsfromtimeentries
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/time_entries/tags"
    return api._make_request("GET", endpoint)

# --- Time Tracking (Legacy) ---
# Note: Docs suggest these might be deprecated or superseded by newer endpoints.
def get_task_tracked_time_legacy(task_id: str, team_id: Optional[str] = None, custom_task_ids: Optional[bool] = None) -> Dict[str, Any]:
    """
    Legacy endpoint to get tracked time for a specific task.
    
    Args:
        task_id: The ID of the task (canonical or custom).
        team_id: Required if custom_task_ids is true.
        custom_task_ids: Set to true if task_id is a custom task ID.

    Returns:
        Dict[str, Any]: A dictionary containing the tracked time details for the task.
    """
    # Reference: https://developer.clickup.com/reference/gettrackedtime (Task section)
    api = ClickUpAPI()
    endpoint = f"/task/{task_id}/time"
    params = {}
    if custom_task_ids:
         if not team_id:
             raise InvalidInputError("team_id is required when custom_task_ids is true for legacy task time.")
         params["custom_task_ids"] = "true"
         params["team_id"] = team_id
         # Docs suggest endpoint changes for custom IDs: /team/{team_id}/task/{task_id}/time
         # endpoint = f"/team/{team_id}/task/{task_id}/time"
    return api._make_request("GET", endpoint, params=params)

def get_list_tracked_time_legacy(list_id: str) -> Dict[str, Any]:
    """
    Legacy endpoint to get tracked time for all tasks within a list.
    
    Args:
        list_id: The ID of the list.

    Returns:
        Dict[str, Any]: A dictionary containing the tracked time details for the list.
    """
    # Reference: https://developer.clickup.com/reference/gettrackedtime (List section)
    api = ClickUpAPI()
    endpoint = f"/list/{list_id}/time"
    return api._make_request("GET", endpoint)

# --- Users ---
def get_user(team_id: str, user_id: int) -> Dict[str, Any]:
    """
    Gets information about a specific user in a Workspace.
    
    Args:
        team_id: The ID of the Workspace (Team).
        user_id: The ID of the user.

    Returns:
        Dict[str, Any]: A dictionary containing the user details.
    """
    # Reference: https://developer.clickup.com/reference/getuser
    api = ClickUpAPI()
    # API docs path is /team/{team_id}/user/{user_id}
    endpoint = f"/team/{team_id}/user/{user_id}"
    return api._make_request("GET", endpoint)

# --- Views ---
def get_team_views(team_id: str) -> Dict[str, Any]:
    """
    Gets "Everything" level views (Workspace views).
    
    Args:
        team_id: The ID of the Workspace (Team).

    Returns:
        Dict[str, Any]: A dictionary containing the list of Workspace views.
    """
    # Reference: https://developer.clickup.com/reference/getteamviews
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/view"
    return api._make_request("GET", endpoint)

def get_space_views(space_id: str) -> Dict[str, Any]:
    """
    Gets views available in a specific Space.
    
    Args:
        space_id: The ID of the Space.

    Returns:
        Dict[str, Any]: A dictionary containing the list of Space views.
    """
    # Reference: https://developer.clickup.com/reference/getspaceviews
    api = ClickUpAPI()
    endpoint = f"/space/{space_id}/view"
    return api._make_request("GET", endpoint)

def get_folder_views(folder_id: str) -> Dict[str, Any]:
    """
    Gets views available in a specific Folder.
    
    Args:
        folder_id: The ID of the Folder.

    Returns:
        Dict[str, Any]: A dictionary containing the list of Folder views.
    """
    # Reference: https://developer.clickup.com/reference/getfolderviews
    api = ClickUpAPI()
    endpoint = f"/folder/{folder_id}/view"
    return api._make_request("GET", endpoint)

def get_list_views(list_id: str) -> Dict[str, Any]:
    """
    Gets views available in a specific List.
    
    Args:
        list_id: The ID of the List.

    Returns:
        Dict[str, Any]: A dictionary containing the list of List views.
    """
    # Reference: https://developer.clickup.com/reference/getlistviews
    api = ClickUpAPI()
    endpoint = f"/list/{list_id}/view"
    return api._make_request("GET", endpoint)

def get_view(view_id: str) -> Dict[str, Any]:
    """
    Gets details about a specific view.
    
    Args:
        view_id: The ID of the view.

    Returns:
        Dict[str, Any]: A dictionary containing the view details.
    """
    # Reference: https://developer.clickup.com/reference/getview
    api = ClickUpAPI()
    endpoint = f"/view/{view_id}"
    return api._make_request("GET", endpoint)

def get_view_tasks(view_id: str, page: Optional[int] = 0, include_closed: Optional[bool] = None) -> Dict[str, Any]:
    """
    Gets tasks that are visible in a specific view.
    
    Args:
        view_id: The ID of the view.
        page: Page number for pagination (starts at 0) (optional).
        include_closed: Include closed tasks filter override (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of tasks in the view.
    """
    # Reference: https://developer.clickup.com/reference/getviewtasks
    api = ClickUpAPI()
    endpoint = f"/view/{view_id}/task"
    params = {}
    if page is not None: # API default is 0, so only include if specified
         params["page"] = page
    if include_closed is not None: # Override view's setting if provided
         params["include_closed"] = str(include_closed).lower()
    return api._make_request("GET", endpoint, params=params)

# --- Webhooks ---
def get_webhooks(team_id: str) -> Dict[str, Any]:
    """
    Gets webhooks registered for a Workspace.
    
    Args:
        team_id: The ID of the Workspace (Team).

    Returns:
        Dict[str, Any]: A dictionary containing the list of webhooks.
    """
    # Reference: https://developer.clickup.com/reference/getwebhooks
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/webhook"
    return api._make_request("GET", endpoint)

# --- Chat (Experimental) ---
def get_chat_channels(team_id: str, with_members: Optional[bool] = None, 
                      with_last_message: Optional[bool] = None, types: Optional[List[str]] = None,
                      filter_unread: Optional[bool] = None, filter_mentions: Optional[bool] = None,
                      continuation: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves chat channels for a Workspace.
    
    Args:
        team_id: The ID of the Workspace (Team).
        with_members: Include channel member list (optional).
        with_last_message: Include the last message sent (optional).
        types: Filter by channel types ('location', 'direct', 'group') (optional).
        filter_unread: Only return channels with unread messages (optional).
        filter_mentions: Only return channels with mentions (optional).
        continuation: Pagination token from previous response (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of chat channels.
    """
    # Reference: https://developer.clickup.com/reference/getchatchannels
    api = ClickUpAPI()
    endpoint = "/channel"
    params = {"team_id": team_id}
    if with_members is not None:
        params["with_members"] = str(with_members).lower()
    if with_last_message is not None:
        params["with_last_message"] = str(with_last_message).lower()
    if types:
        params["types[]"] = types
    if filter_unread is not None:
        params["filter_unread"] = str(filter_unread).lower()
    if filter_mentions is not None:
        params["filter_mentions"] = str(filter_mentions).lower()
    if continuation:
        params["continuation"] = continuation
    return api._make_request("GET", endpoint, params=params)

def get_chat_channel(channel_id: str, with_members: Optional[bool] = None, 
                     with_last_message: Optional[bool] = None) -> Dict[str, Any]:
    """
    Gets details for a specific chat channel.
    
    Args:
        channel_id: The ID of the chat channel.
        with_members: Include channel member list (optional).
        with_last_message: Include the last message sent (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the chat channel details.
    """
    # Reference: https://developer.clickup.com/reference/getchatchannel
    api = ClickUpAPI()
    endpoint = f"/channel/{channel_id}"
    params = {}
    if with_members is not None:
        params["with_members"] = str(with_members).lower()
    if with_last_message is not None:
        params["with_last_message"] = str(with_last_message).lower()
    return api._make_request("GET", endpoint, params=params)

def get_chat_channel_followers(channel_id: str, continuation: Optional[str] = None) -> Dict[str, Any]:
    """
    Gets the followers of a specific chat channel.
    
    Args:
        channel_id: The ID of the chat channel.
        continuation: Pagination token from previous response (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of channel followers.
    """
    # Reference: https://developer.clickup.com/reference/getchatchannelfollowers
    api = ClickUpAPI()
    endpoint = f"/channel/{channel_id}/follower"
    params = {}
    if continuation:
        params["continuation"] = continuation
    return api._make_request("GET", endpoint, params=params)

def get_chat_channel_members(channel_id: str, continuation: Optional[str] = None) -> Dict[str, Any]:
    """
    Gets the members of a specific chat channel.
    
    Args:
        channel_id: The ID of the chat channel.
        continuation: Pagination token from previous response (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of channel members.
    """
    # Reference: https://developer.clickup.com/reference/getchatchannelmembers
    api = ClickUpAPI()
    endpoint = f"/channel/{channel_id}/member"
    params = {}
    if continuation:
        params["continuation"] = continuation
    return api._make_request("GET", endpoint, params=params)

def get_chat_messages(channel_id: str, before_message_id: Optional[str] = None,
                      after_message_id: Optional[str] = None, include_deleted: Optional[bool] = None,
                      include_reactions: Optional[bool] = None, include_replies: Optional[bool] = None,
                      reverse: Optional[bool] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Retrieves messages from a specific chat channel.
    
    Args:
        channel_id: The ID of the chat channel.
        before_message_id: Get messages before this ID (optional).
        after_message_id: Get messages after this ID (optional).
        include_deleted: Include deleted messages (optional).
        include_reactions: Include reactions for each message (optional).
        include_replies: Include reply details for each message (optional).
        reverse: Retrieve messages in reverse chronological order (optional).
        limit: Number of messages to retrieve (max 100) (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of chat messages.
    """
    # Reference: https://developer.clickup.com/reference/getchatmessages
    api = ClickUpAPI()
    endpoint = f"/channel/{channel_id}/message"
    params: Dict[str, Any] = {}
    if before_message_id:
        params["before_message_id"] = before_message_id
    if after_message_id:
        params["after_message_id"] = after_message_id
    if include_deleted is not None:
        params["include_deleted"] = str(include_deleted).lower()
    if include_reactions is not None:
        params["include_reactions"] = str(include_reactions).lower()
    if include_replies is not None:
        params["include_replies"] = str(include_replies).lower()
    if reverse is not None:
        params["reverse"] = str(reverse).lower()
    if limit is not None:
         params["limit"] = limit
    return api._make_request("GET", endpoint, params=params)

def get_message_reactions(message_id: str, user_id: Optional[int] = None, 
                          continuation: Optional[str] = None) -> Dict[str, Any]:
    """
    Gets reactions for a specific chat message.
    
    Args:
        message_id: The ID of the chat message.
        user_id: Filter reactions by a specific user ID (optional).
        continuation: Pagination token from previous response (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of reactions for the message.
    """
    # Reference: https://developer.clickup.com/reference/getchatmessagereactions
    api = ClickUpAPI()
    endpoint = f"/message/{message_id}/reaction"
    params = {}
    if user_id is not None:
        params["user_id"] = user_id
    if continuation:
        params["continuation"] = continuation
    return api._make_request("GET", endpoint, params=params)

def get_message_replies(message_id: str, include_deleted: Optional[bool] = None,
                        include_reactions: Optional[bool] = None, include_replies: Optional[bool] = None,
                        reverse: Optional[bool] = None, limit: Optional[int] = None,
                        continuation: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves replies to a specific chat message.
    
    Args:
        message_id: The ID of the parent chat message.
        include_deleted: Include deleted replies (optional).
        include_reactions: Include reactions for each reply (optional).
        include_replies: Include nested reply details (optional).
        reverse: Retrieve replies in reverse chronological order (optional).
        limit: Number of replies to retrieve (max 100) (optional).
        continuation: Pagination token from previous response (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of replies for the message.
    """
    # Reference: https://developer.clickup.com/reference/getchatmessagereplies
    api = ClickUpAPI()
    endpoint = f"/message/{message_id}/reply"
    params: Dict[str, Any] = {}
    if include_deleted is not None:
        params["include_deleted"] = str(include_deleted).lower()
    if include_reactions is not None:
        params["include_reactions"] = str(include_reactions).lower()
    if include_replies is not None:
        params["include_replies"] = str(include_replies).lower()
    if reverse is not None:
        params["reverse"] = str(reverse).lower()
    if limit is not None:
        params["limit"] = limit
    if continuation:
         params["continuation"] = continuation
    return api._make_request("GET", endpoint, params=params)

def get_tagged_users_for_message(message_id: str) -> Dict[str, Any]:
    """
    Gets users tagged (mentioned) in a specific chat message.
    
    Args:
        message_id: The ID of the chat message.

    Returns:
        Dict[str, Any]: A dictionary containing the list of tagged users.
    """
    # Reference: https://developer.clickup.com/reference/getchatmessagetaggedusers
    api = ClickUpAPI()
    endpoint = f"/message/{message_id}/tagged_user"
    return api._make_request("GET", endpoint)

# --- Add more functions for POST, PUT, DELETE etc. below as needed ---


