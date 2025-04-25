from typing import List, Dict, Any, Optional, Union
import requests
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import json
import logging
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Load ClickUp Team ID from config
CLICKUP_TEAM_ID = Config.CLICKUP_TEAM_ID

# --- ClickUpAPI Class ---
class ClickUpAPI:
    def __init__(self):
        self.api_key = os.getenv("CLICKUP_API_KEY")
        if not self.api_key:
            # Raise ValueError instead of ClickUpConfigError
            raise ValueError("CLICKUP_API_KEY not found in environment variables") 
        
        self.workspace_id = os.getenv("CLICKUP_WORKSPACE_ID", "3723297") # Load from env or use default
        if not self.workspace_id:
            # Raise ValueError instead of ClickUpConfigError
             raise ValueError("CLICKUP_WORKSPACE_ID not found in environment variables and no default provided")
            
        # Set base URL without version
        self.base_url = "https://api.clickup.com/api" 
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Any:
        """
        Makes an HTTP request to the ClickUp API.
        Returns the JSON response on success, or an error dictionary on failure.
        Error dictionary format: {"error_code": int, "error_message": str}
        """
        url = f"{self.base_url}{endpoint}"
        response = None # Initialize response to None
        try:
            response = requests.request(
                method, url, headers=self.headers, params=params, json=data, timeout=30 # Added timeout
            )
            
            # Check for HTTP errors (4xx or 5xx)
            if not response.ok:
                error_message = f"HTTP error {response.status_code} for {url}."
                try:
                    # Try to get more specific error from ClickUp response
                    error_details = response.json()
                    err = error_details.get("err")
                    ecode = error_details.get("ECODE")
                    if err:
                        error_message += f" ClickUp Error: {err}"
                    if ecode:
                        error_message += f" (ECODE: {ecode})"
                except json.JSONDecodeError:
                     # If response is not JSON, use the raw text
                     error_message += f" Response: {response.text}"
                except Exception as e:
                     # Catch potential errors during error detail extraction
                     logging.warning(f"Could not parse error response body for {url}: {e}. Response text: {response.text}")
                     error_message += f" Response: {response.text}"
                     
                return {"error_code": response.status_code, "error_message": error_message}

            # Attempt to parse successful response as JSON
            return response.json()

        except requests.exceptions.ConnectionError as conn_err:
            logging.error(f"Connection error accessing {url}: {conn_err}", exc_info=True)
            return {"error_code": 503, "error_message": f"Connection error: {conn_err}"} # 503 Service Unavailable
        except requests.exceptions.Timeout as timeout_err:
            logging.error(f"Request timed out for {url}: {timeout_err}", exc_info=True)
            return {"error_code": 504, "error_message": f"Request timed out: {timeout_err}"} # 504 Gateway Timeout
        except requests.exceptions.RequestException as req_err:
            logging.error(f"An error occurred during the API request to {url}: {req_err}", exc_info=True)
            # Attempt to get status code from response if available
            status_code = response.status_code if response is not None else 500
            return {"error_code": status_code, "error_message": f"Request error: {req_err}"}
        except json.JSONDecodeError as json_err:
            # Handle errors in parsing the JSON response even for potentially "ok" status codes
            logging.error(f"Failed to decode JSON response from {url}. Error: {json_err}. Response text: {response.text if response else 'No response'}", exc_info=True)
            return {"error_code": 500, "error_message": f"Failed to decode JSON response. Error: {json_err}. Response text: {response.text if response else 'No response object'}"}
        except Exception as e: # Catch any other unexpected error during the request process
            logging.error(f"Unexpected error during request to {url}: {e}", exc_info=True)
            status_code = response.status_code if response is not None else 500
            return {"error_code": status_code, "error_message": f"An unexpected error occurred: {e}"}


    def _get_user_id(self, username: str) -> Union[str, Dict[str, Any]]:
        """
        Helper method to get user ID from username or email.
        Returns the user ID (str) on success, or an error dictionary on failure.
        """
        endpoint = "/team"
        teams_data = self._make_request("GET", endpoint)

        # Check if _make_request returned an error
        if isinstance(teams_data, dict) and "error_code" in teams_data:
            teams_data["error_message"] = f"Failed to fetch teams to find user ID for '{username}': {teams_data.get('error_message', 'Unknown API error')}"
            return teams_data # Propagate the error dictionary

        try:
            teams = teams_data.get("teams", [])
            
            for team in teams:
                members = team.get("members", [])
                for member in members:
                    user = member.get("user", {})
                    api_username = user.get("username")
                    api_email = user.get("email")
                    
                    # Check if the input username matches either the API username or email (case-insensitive)
                    if (api_username and api_username.lower() == username.lower()) or \
                       (api_email and api_email.lower() == username.lower()):
                        user_id = user.get("id")
                        if user_id:
                            return str(user_id) # Ensure it returns string ID
                        else:
                            # This case should ideally not happen if username matches
                            logging.warning(f"Found user '{username}' but ID is missing in API response.")
                            # Return an error dict instead of raising ClickUpError
                            return {"error_code": 500, "error_message": f"Found user '{username}' but ID is missing in API response."}
            
            # If loop completes without returning, user was not found
            # Return an error dict instead of raising ResourceNotFoundError
            return {"error_code": 404, "error_message": f"User with username or email '{username}' not found in any accessible team."}

        except Exception as e: # Catch any other unexpected error during processing
             logging.error(f"Unexpected error finding user ID for '{username}' after fetching teams: {e}", exc_info=True)
             # Return an error dict instead of raising ClickUpError
             return {"error_code": 500, "error_message": f"An unexpected error occurred while processing team data for user '{username}': {e}"}

# --- Standalone ClickUp API Functions (GET Requests) ---

# --- Comments ---
def get_task_comments(task_id: str, start: Optional[int] = None, start_id: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets comments for a specific task.
    
    Args:
        task_id (str): The ID of the task to get comments for.
        start (Optional[int]): The timestamp (Unix time in ms) to start fetching comments from (optional).
        start_id (Optional[str]): The comment ID to fetch comments after (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of comments.
    """
    # Reference: https://developer.clickup.com/reference/gettaskcomments
    api = ClickUpAPI()
    endpoint = f"/v2/task/{task_id}/comment"
    params = {}
    if start is not None:
        params["start"] = start
    if start_id is not None:
        params["start_id"] = start_id
    return api._make_request("GET", endpoint, params=params)

def get_chat_view_comments(view_id: str, start: Optional[int] = None, start_id: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets comments from a Chat view.
    
    Args:
        view_id (str): The ID of the Chat view.
        start (Optional[int]): The timestamp (Unix time in ms) to start fetching comments from (optional).
        start_id (Optional[str]): The comment ID to fetch comments after (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of comments for the chat view.
    """
    # Reference: https://developer.clickup.com/reference/getchatviewcomments
    api = ClickUpAPI()
    endpoint = f"/v2/view/{view_id}/comment"
    params = {}
    if start is not None:
        params["start"] = start
    if start_id is not None:
        params["start_id"] = start_id
    return api._make_request("GET", endpoint, params=params)

def get_list_comments(list_id: str, start: Optional[int] = None, start_id: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets comments for a specific list.
    
    Args:
        list_id (str): The ID of the list.
        start (Optional[int]): The timestamp (Unix time in ms) to start fetching comments from (optional).
        start_id (Optional[str]): The comment ID to fetch comments after (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of comments for the list.
    """
    # Reference: https://developer.clickup.com/reference/getlistcomments
    api = ClickUpAPI()
    endpoint = f"/v2/list/{list_id}/comment"
    params = {}
    if start is not None:
        params["start"] = start
    if start_id is not None:
        params["start_id"] = start_id
    return api._make_request("GET", endpoint, params=params)

def get_threaded_comments(comment_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets replies to a specific comment thread. Requires the comment ID of the parent comment.
    
    Args:
        comment_id (str): The ID of the parent comment.

    Returns:
        Dict[str, Any]: A dictionary containing the list of threaded replies.
    """
    # Reference: https://developer.clickup.com/reference/getthreadedcomments
    api = ClickUpAPI()
    endpoint = f"/v2/comment/{comment_id}/reply" # Changed from /comments to /reply
    return api._make_request("GET", endpoint)

# --- Custom Task Types ---
def get_custom_task_types(team_id: str = CLICKUP_TEAM_ID) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the Custom Task Types available in a Workspace.
    
    Args:
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..

    Returns:
        Dict[str, Any]: A dictionary containing the list of custom task types under the 'data' key.
    """
    # Reference: https://developer.clickup.com/reference/getcustomitems
    api = ClickUpAPI()
    endpoint = f"/v2/team/{team_id}/custom_item"
    return api._make_request("GET", endpoint)

# --- Custom Fields ---
def get_list_custom_fields(list_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the Custom Fields available for a specific List.
    
    Args:
        list_id (str): The ID of the List.

    Returns:
        Dict[str, Any]: A dictionary containing the list of custom fields for the list.
    """
    # Reference: https://developer.clickup.com/reference/getaccessiblecustomfields
    api = ClickUpAPI()
    endpoint = f"/v2/list/{list_id}/field"
    return api._make_request("GET", endpoint)

def get_folder_available_custom_fields(folder_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the available Custom Fields for a Folder.
    
    Args:
        folder_id (str): The ID of the Folder.

    Returns:
        Dict[str, Any]: A dictionary containing the list of custom fields for the folder.
    """
    # Reference: https://developer.clickup.com/reference/getfolderavailablefields
    api = ClickUpAPI()
    endpoint = f"/v2/folder/{folder_id}/field"
    return api._make_request("GET", endpoint)

def get_space_available_custom_fields(space_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the available Custom Fields for a Space.
    
    Args:
        space_id (str): The ID of the Space.

    Returns:
        Dict[str, Any]: A dictionary containing the list of custom fields for the space.
    """
    # Reference: https://developer.clickup.com/reference/getspaceavailablefields
    api = ClickUpAPI()
    endpoint = f"/v2/space/{space_id}/field"
    return api._make_request("GET", endpoint)

def get_team_available_custom_fields(team_id: str = CLICKUP_TEAM_ID) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the available Custom Fields for a Workspace (Team).
    
    Args:
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..

    Returns:
        Dict[str, Any]: A dictionary containing the list of custom fields for the workspace.
    """
    # Reference: https://developer.clickup.com/reference/getteamavailablefields
    api = ClickUpAPI()
    endpoint = f"/v2/team/{team_id}/field"
    return api._make_request("GET", endpoint)

# --- Docs ---
def search_docs(query: str, team_id: str = CLICKUP_TEAM_ID, include_content: Optional[bool] = None,
                 include_locations: Optional[bool] = None, owner_ids: Optional[List[int]] = None,
                 location_ids: Optional[List[int]] = None, location_type: Optional[str] = None,
                 parent_ids: Optional[List[int]] = None, doc_ids: Optional[List[str]] = None,
                 page_ids: Optional[List[str]] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Searches for Docs within a Workspace.
    
    Args:
        query (str): The search query string.
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..
        include_content (Optional[bool]): Whether to include the content of the Docs (optional).
        include_locations (Optional[bool]): Whether to include location information (optional).
        owner_ids (Optional[List[int]]): Filter by owner user IDs (optional).
        location_ids (Optional[List[int]]): Filter by location IDs (Space, Folder, List) (optional).
        location_type (Optional[str]): Filter by location type ('space', 'folder', 'list') (optional).
        parent_ids (Optional[List[int]]): Filter by parent Doc IDs (optional).
        doc_ids (Optional[List[str]]): Filter by specific Doc IDs (optional).
        page_ids (Optional[List[str]]): Filter by specific Page IDs (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the search results for Docs under the 'data' or 'docs' key, or an error dictionary.
    """
    # Reference: https://developer.clickup.com/reference/searchdocs 
    api = ClickUpAPI()
    endpoint = f"/v3/workspaces/{team_id}/docs"
    params = {}
    if query:
        params["search"] = query # Changed from "query": query
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

def get_doc(doc_id: str, workspace_id: str = CLICKUP_TEAM_ID, include_content: Optional[bool] = None) -> Dict[str, Any]:
    """
    Gets details about a specific Doc.
    
    Args:
        doc_id (str): The ID of the Doc.
        workspace_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..
        include_content (Optional[bool]): Whether to include the content of the Doc (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the Doc details, or an error dictionary.
    """
    # Reference: https://developer.clickup.com/reference/getdoc
    api = ClickUpAPI()
    endpoint = f"/v3/workspaces/{workspace_id}/docs/{doc_id}"
    params = {}
    if include_content is not None:
        params["include_content"] = str(include_content).lower()
    return api._make_request("GET", endpoint, params=params)

def get_doc_page_listing(doc_id: str, workspace_id: str = CLICKUP_TEAM_ID) -> List[Dict[str, Any]]:
    """
    Gets a listing of pages within a Doc.
    
    Args:
        doc_id (str): The ID of the Doc.
        workspace_id (str): The ID of the Workspace (Team). Defaults to Dorxata team.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each containing page listing details.
    """
    # Reference: https://developer.clickup.com/reference/getdocpagelisting
    api = ClickUpAPI()
    endpoint = f"/v3/workspaces/{workspace_id}/docs/{doc_id}/pages"
    return api._make_request("GET", endpoint)

def get_doc_pages(doc_id: str, workspace_id: str = CLICKUP_TEAM_ID, include_content: Optional[bool] = None) -> List[Dict[str, Any]]:
    """
    Gets the pages within a Doc, optionally including their content.
    
    Args:
        doc_id (str): The ID of the Doc.
        workspace_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..
        include_content (Optional[bool]): Whether to include the content of the pages (optional).

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a page.
    """
    # Reference: https://developer.clickup.com/reference/getdocpages
    api = ClickUpAPI()
    endpoint = f"/v3/workspaces/{workspace_id}/docs/{doc_id}/pages"
    params = {}
    if include_content is not None:
        params["include_content"] = str(include_content).lower()
    return api._make_request("GET", endpoint, params=params)

def get_page(doc_id: str, page_id: str, workspace_id: str = CLICKUP_TEAM_ID, content_format: Optional[str] = None) -> Dict[str, Any]:
    """
    Gets details about a specific page within a Doc.
    
    Args:
        doc_id (str): The ID of the parent Doc.
        page_id (str): The ID of the page.
        workspace_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..
        content_format (Optional[str]): The desired content format (e.g., 'text/html', 'text/md'). Optional.

    Returns:
        Dict[str, Any]: A dictionary containing the page details, or an error dictionary.
    """
    # Reference: https://developer.clickup.com/reference/getpage
    api = ClickUpAPI()
    endpoint = f"/v3/workspaces/{workspace_id}/docs/{doc_id}/pages/{page_id}"
    params = {}
    if content_format is not None:
        params["content_format"] = content_format
    return api._make_request("GET", endpoint, params=params)

# --- Folders ---
def get_folders(space_id: str, archived: Optional[bool] = False) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets Folders within a specific Space.
    
    Args:
        space_id (str): The ID of the Space.
        archived (Optional[bool]): Whether to include archived Folders (default: False).

    Returns:
        Dict[str, Any]: A dictionary containing the list of Folders.
    """
    # Reference: https://developer.clickup.com/reference/getfolders
    api = ClickUpAPI()
    endpoint = f"/v2/space/{space_id}/folder"
    params = {"archived": str(archived).lower()}
    return api._make_request("GET", endpoint, params=params)

def get_folder(folder_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets details about a specific Folder.
    
    Args:
        folder_id (str): The ID of the Folder.

    Returns:
        Dict[str, Any]: A dictionary containing the Folder details.
    """
    # Reference: https://developer.clickup.com/reference/getfolder
    api = ClickUpAPI()
    endpoint = f"/v2/folder/{folder_id}"
    return api._make_request("GET", endpoint)

# --- Goals ---
def get_goals(team_id: str = CLICKUP_TEAM_ID, include_completed: Optional[bool] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets Goals from a Workspace.
    
    Args:
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..
        include_completed (Optional[bool]): Whether to include completed Goals (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of Goals.
    """
    # Reference: https://developer.clickup.com/reference/getgoals
    api = ClickUpAPI()
    endpoint = f"/v2/team/{team_id}/goal"
    params = {}
    if include_completed is not None:
        params["include_completed"] = str(include_completed).lower()
    return api._make_request("GET", endpoint, params=params)

def get_goal(goal_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets details about a specific Goal.
    
    Args:
        goal_id (str): The ID of the Goal.

    Returns:
        Dict[str, Any]: A dictionary containing the Goal details.
    """
    # Reference: https://developer.clickup.com/reference/getgoal
    api = ClickUpAPI()
    endpoint = f"/v2/goal/{goal_id}"
    return api._make_request("GET", endpoint)

# --- Guests ---
def get_guest(guest_id: int, team_id: str = CLICKUP_TEAM_ID) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets information about a specific Guest in a Workspace.
    
    Args:
        guest_id (int): The ID of the Guest user.
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..

    Returns:
        Dict[str, Any]: A dictionary containing the Guest details.
    """
    # Reference: https://developer.clickup.com/reference/getguest
    api = ClickUpAPI()
    endpoint = f"/v2/team/{team_id}/guest/{guest_id}"
    return api._make_request("GET", endpoint)

# --- Lists ---
def get_lists(folder_id: str, archived: Optional[bool] = False) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets Lists within a specific Folder.
    
    Args:
        folder_id (str): The ID of the Folder.
        archived (Optional[bool]): Whether to include archived Lists (default: False).

    Returns:
        Dict[str, Any]: A dictionary containing the list of Lists in the Folder.
    """
    # Reference: https://developer.clickup.com/reference/getlists
    api = ClickUpAPI()
    endpoint = f"/v2/folder/{folder_id}/list"
    params = {"archived": str(archived).lower()}
    return api._make_request("GET", endpoint, params=params)

def get_folderless_lists(space_id: str, archived: Optional[bool] = False) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets Lists in a Space that are not contained within any Folder.
    
    Args:
        space_id (str): The ID of the Space.
        archived (Optional[bool]): Whether to include archived Lists (default: False).

    Returns:
        Dict[str, Any]: A dictionary containing the list of folderless Lists in the Space.
    """
    # Reference: https://developer.clickup.com/reference/getfolderlesslists
    api = ClickUpAPI()
    endpoint = f"/v2/space/{space_id}/list"
    params = {"archived": str(archived).lower()}
    return api._make_request("GET", endpoint, params=params)

def get_list(list_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets details about a specific List.
    
    Args:
        list_id (str): The ID of the List.

    Returns:
        Dict[str, Any]: A dictionary containing the List details.
    """
    # Reference: https://developer.clickup.com/reference/getlist
    api = ClickUpAPI()
    endpoint = f"/v2/list/{list_id}"
    return api._make_request("GET", endpoint)

# --- Members ---
def get_task_members(task_id: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Gets members (users) assigned to or associated with a task.
    
    Args:
        task_id (str): The ID of the task.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a member associated with the task.
    """
    # Reference: https://developer.clickup.com/reference/gettaskmembers
    api = ClickUpAPI()
    endpoint = f"/v2/task/{task_id}/member"
    response = api._make_request("GET", endpoint)
    # Check for error dict before accessing 'members'
    if isinstance(response, dict) and "error_code" in response:
        return response
    return response.get("members", []) # Assuming success structure {'members': [...]} or empty dict

def get_list_members(list_id: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Gets members (users) who have access to a specific List.
    
    Args:
        list_id (str): The ID of the List.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each representing a member with access to the list.
    """
    # Reference: https://developer.clickup.com/reference/getlistmembers
    api = ClickUpAPI()
    endpoint = f"/v2/list/{list_id}/member"
    response = api._make_request("GET", endpoint)
    # Check for error dict before accessing 'members'
    if isinstance(response, dict) and "error_code" in response:
        return response
    return response.get("members", []) # Assuming success structure {'members': [...]} or empty dict

# --- Shared Hierarchy ---
def get_shared_hierarchy(team_id: str = CLICKUP_TEAM_ID) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the shared hierarchy for the authorized user in a Workspace.
    
    Args:
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..

    Returns:
        Dict[str, Any]: A dictionary containing the shared hierarchy details.
    """
    # Reference: https://developer.clickup.com/reference/sharedhierarchy
    api = ClickUpAPI()
    endpoint = f"/v2/team/{team_id}/shared"
    return api._make_request("GET", endpoint)

# --- Spaces ---
def get_spaces(team_id: str = CLICKUP_TEAM_ID, archived: Optional[bool] = False) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets Spaces within a specific Workspace.
    
    Args:
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..
        archived (Optional[bool]): Whether to include archived Spaces (default: False).

    Returns:
        Dict[str, Any]: A dictionary containing the list of Spaces.
    """
    # Reference: https://developer.clickup.com/reference/getspaces
    api = ClickUpAPI()
    endpoint = f"/v2/team/{team_id}/space"
    params = {"archived": str(archived).lower()}
    return api._make_request("GET", endpoint, params=params)

def get_space(space_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets details about a specific Space.
    
    Args:
        space_id (str): The ID of the Space.

    Returns:
        Dict[str, Any]: A dictionary containing the Space details.
    """
    # Reference: https://developer.clickup.com/reference/getspace
    api = ClickUpAPI()
    endpoint = f"/v2/space/{space_id}"
    return api._make_request("GET", endpoint)

# --- Tags ---
def get_space_tags(space_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets Tags available in a specific Space.
    
    Args:
        space_id (str): The ID of the Space.

    Returns:
        Dict[str, Any]: A dictionary containing the list of tags for the Space.
    """
    # Reference: https://developer.clickup.com/reference/getspacetags
    api = ClickUpAPI()
    endpoint = f"/v2/space/{space_id}/tag"
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
              custom_fields: Optional[str] = None,
              custom_items: Optional[List[int]] = None,
              parent: Optional[str] = None, include_subtasks: Optional[bool] = None # Deprecated
              ) -> Dict[str, Any]:
    """
    Gets tasks from a specific List, with extensive filtering options.
    
    Args:
        list_id (str): The ID of the List to get tasks from.
        archived (Optional[bool]): Whether to include archived tasks (default: False).
        include_markdown_description (Optional[bool]): Return description in Markdown format (optional).
        page (Optional[int]): Page number for pagination (optional).
        order_by (Optional[str]): Field to order tasks by (e.g., 'due_date', 'priority') (optional).
        reverse (Optional[bool]): Reverse the order of tasks (optional).
        subtasks (Optional[bool]): Include subtasks (true), exclude subtasks (false), or include both tasks and subtasks ('true_all') (optional).
        space_ids (Optional[List[str]]): Filter by Space IDs (optional).
        project_ids (Optional[List[str]]): Filter by Folder IDs (previously Projects) (optional).
        list_ids (Optional[List[str]]): Filter by List IDs (optional).
        statuses (Optional[List[str]]): Filter by task statuses (case-insensitive) (optional).
        include_closed (Optional[bool]): Include closed tasks (optional).
        assignees (Optional[List[str]]): Filter by assignee user IDs (optional).
        tags (Optional[List[str]]): Filter by tag names (optional).
        due_date_gt (Optional[int]): Filter by due date greater than (Unix time in ms) (optional).
        due_date_lt (Optional[int]): Filter by due date less than (Unix time in ms) (optional).
        date_created_gt (Optional[int]): Filter by creation date greater than (Unix time in ms) (optional).
        date_created_lt (Optional[int]): Filter by creation date less than (Unix time in ms) (optional).
        date_updated_gt (Optional[int]): Filter by update date greater than (Unix time in ms) (optional).
        date_updated_lt (Optional[int]): Filter by update date less than (Unix time in ms) (optional).
        date_done_gt (Optional[int]): Filter by completion date greater than (Unix time in ms) (optional).
        date_done_lt (Optional[int]): Filter by completion date less than (Unix time in ms) (optional).
        custom_fields (Optional[str]): Filter by custom fields (JSON string) (optional). Example: '[{"field_id":"...", "operator":"=", "value":"..."}]'
        custom_items (Optional[List[int]]): Filter by Custom Task Types. Including 0 returns tasks. Including 1 returns milestones. Including other numbers returns custom task types (provide IDs) (optional).
        parent (Optional[str]): Filter by parent task ID (optional).
        include_subtasks (Optional[bool]): Deprecated alias for `subtasks` (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of tasks under the 'tasks' key matching the criteria,
                        or an error dictionary if the request fails.
    """
    # Reference: https://developer.clickup.com/reference/gettasks
    api = ClickUpAPI()
    endpoint = f"/v2/list/{list_id}/task"
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
             include_markdown_description: Optional[bool] = None, custom_task_ids: Optional[bool] = None, team_id: Optional[str] = CLICKUP_TEAM_ID) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets details about a specific task.
    
    Args:
        task_id (str): The ID of the task (can be the canonical ID or custom task ID).
        include_subtasks (Optional[bool]): Include subtasks in the response (optional).
        include_markdown_description (Optional[bool]): Return description in Markdown format (optional).
        custom_task_ids (Optional[bool]): If true, treats task_id as a custom task ID. Requires team_id. (optional)
        team_id (Optional[str]): The Workspace (Team) ID, required if custom_task_ids is true. Defaults to Dorxata team..

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

    endpoint = f"/v2/task/{task_id}"

    if custom_task_ids:
        if not team_id:
             # Keep raising config error here as it's invalid input before the API call
             raise ValueError("team_id is required when custom_task_ids is true.")
        params["custom_task_ids"] = "true"
        params["team_id"] = team_id

    return api._make_request("GET", endpoint, params=params)

def get_filtered_team_tasks(team_id: str = CLICKUP_TEAM_ID, page: Optional[int] = None,
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
                             ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets tasks for a Workspace (Team), filtered by various criteria. Similar to get_tasks but workspace-wide.
    
    Args:
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..
        page (Optional[int]): Page number for pagination (optional).
        order_by (Optional[str]): Field to order tasks by (e.g., 'due_date', 'priority') (optional).
        reverse (Optional[bool]): Reverse the order of tasks (optional).
        subtasks (Optional[bool]): Include subtasks (true), exclude subtasks (false), or include both tasks and subtasks ('true_all') (optional).
        space_ids (Optional[List[str]]): Filter by Space IDs (optional).
        project_ids (Optional[List[str]]): Filter by Folder IDs (previously Projects) (optional).
        list_ids (Optional[List[str]]): Filter by List IDs (optional).
        statuses (Optional[List[str]]): Filter by task statuses (case-insensitive) (optional).
        include_closed (Optional[bool]): Include closed tasks (optional).
        assignees (Optional[List[str]]): Filter by assignee user IDs (optional).
        tags (Optional[List[str]]): Filter by tag names (optional).
        due_date_gt (Optional[int]): Filter by due date greater than (Unix time in ms) (optional).
        due_date_lt (Optional[int]): Filter by due date less than (Unix time in ms) (optional).
        date_created_gt (Optional[int]): Filter by creation date greater than (Unix time in ms) (optional).
        date_created_lt (Optional[int]): Filter by creation date less than (Unix time in ms) (optional).
        date_updated_gt (Optional[int]): Filter by update date greater than (Unix time in ms) (optional).
        date_updated_lt (Optional[int]): Filter by update date less than (Unix time in ms) (optional).
        date_done_gt (Optional[int]): Filter by completion date greater than (Unix time in ms) (optional).
        date_done_lt (Optional[int]): Filter by completion date less than (Unix time in ms) (optional).
        custom_fields (Optional[str]): Filter by custom fields (JSON string) (optional). Example: '[{"field_id":"...", "operator":"=", "value":"..."}]'
        custom_items (Optional[List[int]]): Filter by Custom Task Types (provide IDs) (optional).
        parent (Optional[str]): Filter by parent task ID (optional).
        include_markdown_description (Optional[bool]): Return description in Markdown format (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of tasks matching the criteria for the workspace.
    """
    # Reference: https://developer.clickup.com/reference/getfilteredteamtasks
    api = ClickUpAPI()
    endpoint = f"/v2/team/{team_id}/task"
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

def get_task_time_in_status(task_id: str, custom_task_ids: Optional[bool] = None, team_id: Optional[str] = CLICKUP_TEAM_ID) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the time spent by a task in each status.
    
    Args:
        task_id (str): The ID of the task (can be the canonical ID or custom task ID).
        custom_task_ids (Optional[bool]): If true, treats task_id as a custom task ID. Requires team_id. (optional)
        team_id (Optional[str]): The Workspace (Team) ID, required if custom_task_ids is true. Defaults to Dorxata team..

    Returns:
        Dict[str, Any]: A dictionary containing the time in status details for the task.
    """
    # Reference: https://developer.clickup.com/reference/gettaskstimeinstatus
    api = ClickUpAPI()
    endpoint = f"/v2/task/{task_id}/time_in_status"
    params = {}
    if custom_task_ids:
        if not team_id:
            # Keep raising config error here if CLICKUP_TEAM_ID is not set
            raise ValueError("team_id is required when custom_task_ids is true, and CLICKUP_TEAM_ID seems not configured.")
        params["custom_task_ids"] = "true"
        params["team_id"] = team_id

    return api._make_request("GET", endpoint, params=params)

def get_bulk_tasks_time_in_status(task_ids: List[str], custom_task_ids: Optional[bool] = None, team_id: Optional[str] = CLICKUP_TEAM_ID) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the time spent in status for multiple tasks.
    
    Args:
        task_ids (List[str]): A list of task IDs (canonical or custom).
        custom_task_ids (Optional[bool]): If true, treats task_ids as custom task IDs. Requires team_id. (optional)
        team_id (Optional[str]): The Workspace (Team) ID, required if custom_task_ids is true. Defaults to Dorxata team..

    Returns:
        Dict[str, Any]: A dictionary containing the time in status details for the specified tasks.
    """
    # Reference: https://developer.clickup.com/reference/getbulktaskstimeinstatus
    api = ClickUpAPI()
    endpoint = "/v2/task/bulk_time_in_status/task_ids"
    params = {"task_ids": task_ids}
    if custom_task_ids:
         if not team_id:
             # Keep raising config error here if CLICKUP_TEAM_ID is not set
             raise ValueError("team_id is required when custom_task_ids is true, and CLICKUP_TEAM_ID seems not configured.")
         params["custom_task_ids"] = "true"
         params["team_id"] = team_id

    return api._make_request("GET", endpoint, params=params)

# --- Templates ---
def get_task_templates(page: int, team_id: str = CLICKUP_TEAM_ID, space_id: Optional[int] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets task templates for a Workspace.
    
    Args:
        page (int): Page number for pagination (templates are returned 100 at a time).
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..
        space_id (Optional[int]): Optional Space ID to filter templates. If provided, only templates available
                  to the specific Space are returned. Otherwise, Workspace-level templates are returned.

    Returns:
        Dict[str, Any]: A dictionary containing the list of task templates.
    """
    # Reference: https://developer.clickup.com/reference/gettasktemplates
    api = ClickUpAPI()
    endpoint = f"/v2/team/{team_id}/taskTemplate"
    params: Dict[str, Any] = {"page": page}
    if space_id is not None:
        params["space_id"] = space_id
    return api._make_request("GET", endpoint, params=params)

# --- Time Tracking ---
def get_time_entries(team_id: str = CLICKUP_TEAM_ID, start_date: Optional[int] = None,
                     end_date: Optional[int] = None, assignee: Optional[str] = None,
                     include_task_tags: Optional[bool] = None, include_location_names: Optional[bool] = None,
                     space_id: Optional[str] = None, folder_id: Optional[str] = None,
                     list_id: Optional[str] = None, task_id: Optional[str] = None,
                     custom_task_ids: Optional[bool] = None, task_team_id: Optional[str] = CLICKUP_TEAM_ID
                     ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets time entries within a date range for a Workspace (Team).
    
    Args:
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..
        start_date (Optional[int]): Start timestamp (Unix time in ms) (optional).
        end_date (Optional[int]): End timestamp (Unix time in ms) (optional).
        assignee (Optional[str]): Filter by user ID(s) (comma-separated string or list) (optional).
        include_task_tags (Optional[bool]): Include task tags in the response (optional).
        include_location_names (Optional[bool]): Include Folder and List names (optional).
        space_id (Optional[str]): Filter by Space ID (optional).
        folder_id (Optional[str]): Filter by Folder ID (optional).
        list_id (Optional[str]): Filter by List ID (optional).
        task_id (Optional[str]): Filter by Task ID (canonical or custom) (optional).
        custom_task_ids (Optional[bool]): If true, treats task_id as a custom task ID. Requires task_team_id. (optional)
        task_team_id (Optional[str]): The Workspace (Team) ID for the custom task ID lookup. Required if custom_task_ids is true and task_id is provided. Defaults to Dorxata team..

    Returns:
        Dict[str, Any]: A dictionary containing the list of time entries matching the criteria.
    """
    # Reference: https://developer.clickup.com/reference/gettimeentrieswithinadaterange
    api = ClickUpAPI()
    endpoint = f"/v2/team/{team_id}/time_entries"
    params: Dict[str, Any] = {}
    if start_date is not None:
        params["start_date"] = start_date
    if end_date is not None:
        params["end_date"] = end_date
    if assignee:
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
                # Keep raising config error here if CLICKUP_TEAM_ID is not set
                raise ValueError("task_team_id is required when custom_task_ids is true and task_id is provided, and CLICKUP_TEAM_ID seems not configured.")
            params["custom_task_ids"] = "true"
            # Use the provided or defaulted task_team_id. API param is 'team_id' in this context.
            params["team_id"] = task_team_id

    return api._make_request("GET", endpoint, params=params)

def get_singular_time_entry(timer_id: str, team_id: str = CLICKUP_TEAM_ID, include_task_tags: Optional[bool] = None,
                            include_location_names: Optional[bool] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets details for a specific time entry.
    
    Args:
        timer_id (str): The ID of the time entry (timer_id).
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..
        include_task_tags (Optional[bool]): Include task tags in the response (optional).
        include_location_names (Optional[bool]): Include Folder and List names (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the details of the specified time entry.
    """
    # Reference: https://developer.clickup.com/reference/getsingulartimeentry
    api = ClickUpAPI()
    endpoint = f"/v2/team/{team_id}/time_entries/{timer_id}"
    params = {}
    if include_task_tags is not None:
        params["include_task_tags"] = str(include_task_tags).lower()
    if include_location_names is not None:
        params["include_location_names"] = str(include_location_names).lower()
    return api._make_request("GET", endpoint, params=params)

def get_time_entry_history(timer_id: str, team_id: str = CLICKUP_TEAM_ID) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the history of changes for a specific time entry.
    
    Args:
        timer_id (str): The ID of the time entry.
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..

    Returns:
        Dict[str, Any]: A dictionary containing the history of the specified time entry.
    """
    # Reference: https://developer.clickup.com/reference/gettimeentryhistory
    api = ClickUpAPI()
    endpoint = f"/v2/team/{team_id}/time_entries/{timer_id}/history"
    return api._make_request("GET", endpoint)

def get_running_time_entry(team_id: str = CLICKUP_TEAM_ID) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the currently running time entry for the authorized user in a Workspace.
    
    Args:
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..

    Returns:
        Dict[str, Any]: A dictionary containing the details of the running time entry, or an empty dict if none.
    """
    # Reference: https://developer.clickup.com/reference/getrunningtimeentry
    api = ClickUpAPI()
    endpoint = f"/v2/team/{team_id}/time_entries/current"
    return api._make_request("GET", endpoint)

def get_all_time_entry_tags(team_id: str = CLICKUP_TEAM_ID) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets all tags used in time entries for a Workspace.
    
    Args:
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..

    Returns:
        Dict[str, Any]: A dictionary containing the list of all time entry tags.
    """
    # Reference: https://developer.clickup.com/reference/getalltagsfromtimeentries
    api = ClickUpAPI()
    endpoint = f"/v2/team/{team_id}/time_entries/tags"
    return api._make_request("GET", endpoint)

# --- Users ---
def get_user(user_id: int, team_id: str = CLICKUP_TEAM_ID) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets information about a specific user in a Workspace.
    
    Args:
        user_id (int): The ID of the user.
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..

    Returns:
        Dict[str, Any]: A dictionary containing the user details.
    """
    # Reference: https://developer.clickup.com/reference/getuser
    api = ClickUpAPI()
    endpoint = f"/v2/team/{team_id}/user/{user_id}"
    return api._make_request("GET", endpoint)

# --- Views ---
def get_team_views(team_id: str = CLICKUP_TEAM_ID) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets "Everything" level views (Workspace views).
    
    Args:
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..

    Returns:
        Dict[str, Any]: A dictionary containing the list of Workspace views.
    """
    # Reference: https://developer.clickup.com/reference/getteamviews
    api = ClickUpAPI()
    endpoint = f"/v2/team/{team_id}/view"
    return api._make_request("GET", endpoint)

def get_space_views(space_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets views available in a specific Space.
    
    Args:
        space_id (str): The ID of the Space.

    Returns:
        Dict[str, Any]: A dictionary containing the list of Space views.
    """
    # Reference: https://developer.clickup.com/reference/getspaceviews
    api = ClickUpAPI()
    endpoint = f"/v2/space/{space_id}/view"
    return api._make_request("GET", endpoint)

def get_folder_views(folder_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets views available in a specific Folder.
    
    Args:
        folder_id (str): The ID of the Folder.

    Returns:
        Dict[str, Any]: A dictionary containing the list of Folder views.
    """
    # Reference: https://developer.clickup.com/reference/getfolderviews
    api = ClickUpAPI()
    endpoint = f"/v2/folder/{folder_id}/view"
    return api._make_request("GET", endpoint)

def get_list_views(list_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets views available in a specific List.
    
    Args:
        list_id (str): The ID of the List.

    Returns:
        Dict[str, Any]: A dictionary containing the list of List views.
    """
    # Reference: https://developer.clickup.com/reference/getlistviews
    api = ClickUpAPI()
    endpoint = f"/v2/list/{list_id}/view"
    return api._make_request("GET", endpoint)

def get_view(view_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets details about a specific view.
    
    Args:
        view_id (str): The ID of the view.

    Returns:
        Dict[str, Any]: A dictionary containing the view details, often nested under a 'view' key, or an error dictionary.
    """
    # Reference: https://developer.clickup.com/reference/getview
    api = ClickUpAPI()
    endpoint = f"/v2/view/{view_id}"
    return api._make_request("GET", endpoint)

def get_view_tasks(view_id: str, page: Optional[int] = 0, include_closed: Optional[bool] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets tasks that are visible in a specific view.
    
    Args:
        view_id (str): The ID of the view.
        page (Optional[int]): Page number for pagination (starts at 0) (optional).
        include_closed (Optional[bool]): Include closed tasks filter override (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of tasks in the view.
    """
    # Reference: https://developer.clickup.com/reference/getviewtasks
    api = ClickUpAPI()
    endpoint = f"/v2/view/{view_id}/task"
    params = {}
    if page is not None: # API default is 0
         params["page"] = page
    if include_closed is not None:
         params["include_closed"] = str(include_closed).lower()
    return api._make_request("GET", endpoint, params=params)

# --- Chat (Experimental) ---
def get_chat_channels(team_id: str = CLICKUP_TEAM_ID, with_members: Optional[bool] = None,
                      with_last_message: Optional[bool] = None, types: Optional[List[str]] = None,
                      filter_unread: Optional[bool] = None, filter_mentions: Optional[bool] = None,
                      continuation: Optional[str] = None) -> Union[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    """
    Retrieves chat channels for a Workspace.
    
    Args:
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..
        with_members (Optional[bool]): Include channel member list (optional).
        with_last_message (Optional[bool]): Include the last message sent (optional).
        types (Optional[List[str]]): Filter by channel types ('location', 'direct', 'group') (optional).
        filter_unread (Optional[bool]): Only return channels with unread messages (optional).
        filter_mentions (Optional[bool]): Only return channels with mentions (optional).
        continuation (Optional[str]): Pagination token from previous response (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of chat channels under the 'data' key.
    """
    # Reference: https://developer.clickup.com/reference/getchatchannels
    api = ClickUpAPI()
    endpoint = f"/v3/workspaces/{team_id}/chat/channels"
    params = {}
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

def get_chat_channel(channel_id: str, team_id: str = CLICKUP_TEAM_ID, with_members: Optional[bool] = None,
                     with_last_message: Optional[bool] = None) -> Union[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """
    Gets details for a specific chat channel.
    
    Args:
        channel_id (str): The ID of the chat channel.
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..
        with_members (Optional[bool]): Include channel member list (optional).
        with_last_message (Optional[bool]): Include the last message sent (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the chat channel details under the 'data' key.
    """
    # Reference: https://developer.clickup.com/reference/getchatchannel
    api = ClickUpAPI()
    endpoint = f"/v3/workspaces/{team_id}/chat/channels/{channel_id}"
    params = {}
    if with_members is not None:
        params["with_members"] = str(with_members).lower()
    if with_last_message is not None:
        params["with_last_message"] = str(with_last_message).lower()
    return api._make_request("GET", endpoint, params=params)

def get_chat_channel_followers(channel_id: str, team_id: str = CLICKUP_TEAM_ID, continuation: Optional[str] = None) -> Union[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    """
    Gets the followers of a specific chat channel.
    
    Args:
        channel_id (str): The ID of the chat channel.
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..
        continuation (Optional[str]): Pagination token from previous response (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of channel followers under the 'data' key.
    """
    # Reference: https://developer.clickup.com/reference/getchatchannelfollowers
    api = ClickUpAPI()
    endpoint = f"/v3/workspaces/{team_id}/chat/channels/{channel_id}/followers"
    params = {}
    if continuation:
        params["continuation"] = continuation
    return api._make_request("GET", endpoint, params=params)

def get_chat_channel_members(channel_id: str, team_id: str = CLICKUP_TEAM_ID, continuation: Optional[str] = None) -> Union[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    """
    Gets the members of a specific chat channel.
    
    Args:
        channel_id (str): The ID of the chat channel.
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..
        continuation (Optional[str]): Pagination token from previous response (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of channel members under the 'data' key.
    """
    # Reference: https://developer.clickup.com/reference/getchatchannelmembers
    api = ClickUpAPI()
    endpoint = f"/v3/workspaces/{team_id}/chat/channels/{channel_id}/members"
    params = {}
    if continuation:
        params["continuation"] = continuation
    return api._make_request("GET", endpoint, params=params)

def get_chat_messages(channel_id: str, team_id: str = CLICKUP_TEAM_ID, before_message_id: Optional[str] = None,
                      after_message_id: Optional[str] = None, include_deleted: Optional[bool] = None,
                      include_reactions: Optional[bool] = None, include_replies: Optional[bool] = None,
                      reverse: Optional[bool] = None, limit: Optional[int] = None) -> Union[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    """
    Retrieves messages from a specific chat channel.
    
    Args:
        channel_id (str): The ID of the chat channel.
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..
        before_message_id (Optional[str]): Get messages before this ID (optional).
        after_message_id (Optional[str]): Get messages after this ID (optional).
        include_deleted (Optional[bool]): Include deleted messages (optional).
        include_reactions (Optional[bool]): Include reactions for each message (optional).
        include_replies (Optional[bool]): Include reply details for each message (optional).
        reverse (Optional[bool]): Retrieve messages in reverse chronological order (optional).
        limit (Optional[int]): Number of messages to retrieve (max 100) (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of chat messages under the 'data' key. Each message object uses 'content' for the message text.
    """
    # Reference: https://developer.clickup.com/reference/getchatmessages
    api = ClickUpAPI()
    endpoint = f"/v3/workspaces/{team_id}/chat/channels/{channel_id}/messages"
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

def get_message_reactions(message_id: str, team_id: str = CLICKUP_TEAM_ID, user_id: Optional[int] = None,
                          continuation: Optional[str] = None) -> Union[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    """
    Gets reactions for a specific chat message.
    
    Args:
        message_id (str): The ID of the chat message.
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..
        user_id (Optional[int]): Filter reactions by a specific user ID (optional).
        continuation (Optional[str]): Pagination token from previous response (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of reactions for the message under the 'data' key.
    """
    # Reference: https://developer.clickup.com/reference/getchatmessagereactions
    api = ClickUpAPI()
    endpoint = f"/v3/workspaces/{team_id}/chat/messages/{message_id}/reactions"
    params = {}
    if user_id is not None:
        params["user_id"] = user_id
    if continuation:
        params["continuation"] = continuation
    return api._make_request("GET", endpoint, params=params)

def get_message_replies(message_id: str, team_id: str = CLICKUP_TEAM_ID, include_deleted: Optional[bool] = None,
                        include_reactions: Optional[bool] = None, include_replies: Optional[bool] = None,
                        reverse: Optional[bool] = None, limit: Optional[int] = None,
                        continuation: Optional[str] = None) -> Union[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    """
    Retrieves replies to a specific chat message.
    
    Args:
        message_id (str): The ID of the parent chat message.
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..
        include_deleted (Optional[bool]): Include deleted replies (optional).
        include_reactions (Optional[bool]): Include reactions for each reply (optional).
        include_replies (Optional[bool]): Include nested reply details (optional).
        reverse (Optional[bool]): Retrieve replies in reverse chronological order (optional).
        limit (Optional[int]): Number of replies to retrieve (max 100) (optional).
        continuation (Optional[str]): Pagination token from previous response (optional).

    Returns:
        Dict[str, Any]: A dictionary containing the list of replies for the message under the 'data' key.
    """
    # Reference: https://developer.clickup.com/reference/getchatmessagereplies
    api = ClickUpAPI()
    endpoint = f"/v3/workspaces/{team_id}/chat/messages/{message_id}/replies"
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

def get_tagged_users_for_message(message_id: str, team_id: str = CLICKUP_TEAM_ID) -> Union[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    """
    Gets users tagged (mentioned) in a specific chat message.
    
    Args:
        message_id (str): The ID of the chat message.
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team..

    Returns:
        Dict[str, Any]: A dictionary containing the list of tagged users under the 'data' key.
    """
    # Reference: https://developer.clickup.com/reference/getchatmessagetaggedusers
    api = ClickUpAPI()
    endpoint = f"/v3/workspaces/{team_id}/chat/messages/{message_id}/tagged_users"
    return api._make_request("GET", endpoint)

# --- Custom Tools ---

def get_workspace_structure(team_id: str = CLICKUP_TEAM_ID) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Retrieves the structure of spaces, folders, lists, and folderless lists ina specific workspace.
    
    Args:
        team_id (str): The ID of the Workspace (Team). Defaults to Dorxata team.
    
    Returns:
        Dict[str, Any]: A dictionary containing the spaces, folders, lists, and folderless lists of the workspace under the 'data' key.
    
    Example:
        {
            "data": {
                "spaces": [
                    {
                        "id": "1234567890",
                        "name": "Space 1",
                        "folderless_lists": [
                            {
                                "id": "1234567890",
                                "name": "Folderless List 1"
                            }
                        ],
                        "folders": [
                            {
                                "id": "1234567890",
                                "name": "Folder 1",
                                "lists": [
                                    {
                                        "id": "1234567890",
                                        "name": "List 1"
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "id": "1234567890",
                        "name": "Space 2",
                        "folderless_lists": [
                            {
                                "id": "1234567890",
                                "name": "Folderless List 2"
                            }
                        ],
                        "folders": [
                            {
                                "id": "1234567890",
                                "name": "Folder 2",
                                "lists": [
                                    {
                                        "id": "1234567890",
                                        "name": "List 2"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }
    """
    api = ClickUpAPI()
    
    # 1. Get Spaces
    spaces_response = get_spaces(team_id)
    if isinstance(spaces_response, dict) and "error_code" in spaces_response:
        return spaces_response # Propagate error
    
    spaces_data = spaces_response.get("spaces", [])
    workspace_structure = {"spaces": []}

    # 2. Iterate through Spaces
    for space in spaces_data:
        space_id = space.get("id")
        space_name = space.get("name")
        if not space_id or not space_name:
            logging.warning(f"Skipping space with missing id or name in team {team_id}: {space}")
            continue

        space_details = {
            "id": space_id,
            "name": space_name,
            "folderless_lists": [],
            "folders": []
        }

        # 3. Get Folderless Lists for the Space
        folderless_lists_response = get_folderless_lists(space_id)
        if isinstance(folderless_lists_response, dict) and "error_code" in folderless_lists_response:
            logging.warning(f"Failed to get folderless lists for space {space_id}: {folderless_lists_response}")
            # Continue building structure, but note the failure
        else:
            folderless_lists_data = folderless_lists_response.get("lists", [])
            space_details["folderless_lists"] = [
                {"id": lst.get("id"), "name": lst.get("name")}
                for lst in folderless_lists_data if lst.get("id") and lst.get("name")
            ]

        # 4. Get Folders for the Space
        folders_response = get_folders(space_id)
        if isinstance(folders_response, dict) and "error_code" in folders_response:
            logging.warning(f"Failed to get folders for space {space_id}: {folders_response}")
            # Continue building structure, but note the failure
        else:
            folders_data = folders_response.get("folders", [])
            
            # 5. Iterate through Folders
            for folder in folders_data:
                folder_id = folder.get("id")
                folder_name = folder.get("name")
                if not folder_id or not folder_name:
                    logging.warning(f"Skipping folder with missing id or name in space {space_id}: {folder}")
                    continue

                folder_details = {
                    "id": folder_id,
                    "name": folder_name,
                    "lists": []
                }

                # 6. Get Lists for the Folder
                lists_response = get_lists(folder_id)
                if isinstance(lists_response, dict) and "error_code" in lists_response:
                    logging.warning(f"Failed to get lists for folder {folder_id}: {lists_response}")
                    # Continue building structure, but note the failure
                else:
                    lists_data = lists_response.get("lists", [])
                    folder_details["lists"] = [
                        {"id": lst.get("id"), "name": lst.get("name")}
                        for lst in lists_data if lst.get("id") and lst.get("name")
                    ]
                
                space_details["folders"].append(folder_details)

        workspace_structure["spaces"].append(space_details)

    return {"data": workspace_structure}