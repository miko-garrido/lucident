from typing import List, Dict, Any, Optional, Union
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
            
        self.base_url = "https://api.clickup.com/api/v2"
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
    Returns a dictionary containing the list of comments or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/task/{task_id}/comment"
    params = {}
    if start is not None:
        params["start"] = start
    if start_id is not None:
        params["start_id"] = start_id
    return api._make_request("GET", endpoint, params=params)

def get_chat_view_comments(view_id: str, start: Optional[int] = None, start_id: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets comments from a Chat view.
    Returns a dictionary containing the list of comments or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/view/{view_id}/comment"
    params = {}
    if start is not None:
        params["start"] = start
    if start_id is not None:
        params["start_id"] = start_id
    return api._make_request("GET", endpoint, params=params)

def get_list_comments(list_id: str, start: Optional[int] = None, start_id: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets comments for a specific list.
    Returns a dictionary containing the list of comments or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/list/{list_id}/comment"
    params = {}
    if start is not None:
        params["start"] = start
    if start_id is not None:
        params["start_id"] = start_id
    return api._make_request("GET", endpoint, params=params)

def get_threaded_comments(comment_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets replies to a specific comment thread.
    Returns a dictionary containing the list of threaded replies or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/comment/{comment_id}/comments"
    return api._make_request("GET", endpoint)

# --- Custom Task Types ---
def get_custom_task_types(team_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the Custom Task Types available in a Workspace.
    Returns a dictionary containing the custom task types or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/custom_item"
    return api._make_request("GET", endpoint)

# --- Custom Fields ---
def get_list_custom_fields(list_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the Custom Fields available for a specific List.
    Returns a dictionary containing the list of custom fields or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/list/{list_id}/field"
    return api._make_request("GET", endpoint)

def get_folder_available_custom_fields(folder_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the available Custom Fields for a Folder.
    Returns a dictionary containing the list of custom fields or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/folder/{folder_id}/field"
    return api._make_request("GET", endpoint)

def get_space_available_custom_fields(space_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the available Custom Fields for a Space.
    Returns a dictionary containing the list of custom fields or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/space/{space_id}/field"
    return api._make_request("GET", endpoint)

def get_team_available_custom_fields(team_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the available Custom Fields for a Workspace (Team).
    Returns a dictionary containing the list of custom fields or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/field"
    return api._make_request("GET", endpoint)

# --- Docs ---
def search_docs(team_id: str, query: str, include_content: Optional[bool] = None,
                 include_locations: Optional[bool] = None, owner_ids: Optional[List[int]] = None,
                 location_ids: Optional[List[int]] = None, location_type: Optional[str] = None,
                 parent_ids: Optional[List[int]] = None, doc_ids: Optional[List[str]] = None,
                 page_ids: Optional[List[str]] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Searches for Docs within a Workspace.
    Returns a dictionary containing the search results or an error dictionary.
    """
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

def get_doc(doc_id: str, include_content: Optional[bool] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets details about a specific Doc.
    Returns a dictionary containing the Doc details or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/doc/{doc_id}"
    params = {}
    if include_content is not None:
        params["include_content"] = str(include_content).lower()
    return api._make_request("GET", endpoint, params=params)

def get_doc_page_listing(doc_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets a listing of pages within a Doc.
    Returns a dictionary containing the page listing or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/doc/{doc_id}/pages/listing"
    return api._make_request("GET", endpoint)

def get_doc_pages(doc_id: str, include_content: Optional[bool] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the pages within a Doc, optionally including their content.
    Returns a dictionary containing the pages or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/doc/{doc_id}/pages"
    params = {}
    if include_content is not None:
        params["include_content"] = str(include_content).lower()
    return api._make_request("GET", endpoint, params=params)

def get_page(page_id: str, include_content: Optional[bool] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets details about a specific page within a Doc.
    Returns a dictionary containing the page details or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/page/{page_id}"
    params = {}
    if include_content is not None:
        params["include_content"] = str(include_content).lower()
    return api._make_request("GET", endpoint, params=params)

# --- Folders ---
def get_folders(space_id: str, archived: Optional[bool] = False) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets Folders within a specific Space.
    Returns a dictionary containing the list of Folders or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/space/{space_id}/folder"
    params = {"archived": str(archived).lower()}
    return api._make_request("GET", endpoint, params=params)

def get_folder(folder_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets details about a specific Folder.
    Returns a dictionary containing the Folder details or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/folder/{folder_id}"
    return api._make_request("GET", endpoint)

# --- Goals ---
def get_goals(team_id: str, include_completed: Optional[bool] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets Goals from a Workspace.
    Returns a dictionary containing the list of Goals or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/goal"
    params = {}
    if include_completed is not None:
        params["include_completed"] = str(include_completed).lower()
    return api._make_request("GET", endpoint, params=params)

def get_goal(goal_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets details about a specific Goal.
    Returns a dictionary containing the Goal details or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/goal/{goal_id}"
    return api._make_request("GET", endpoint)

# --- Guests ---
def get_guest(team_id: str, guest_id: int) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets information about a specific Guest in a Workspace.
    Returns a dictionary containing the Guest details or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/guest/{guest_id}"
    return api._make_request("GET", endpoint)

# --- Lists ---
def get_lists(folder_id: str, archived: Optional[bool] = False) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets Lists within a specific Folder.
    Returns a dictionary containing the list of Lists or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/folder/{folder_id}/list"
    params = {"archived": str(archived).lower()}
    return api._make_request("GET", endpoint, params=params)

def get_folderless_lists(space_id: str, archived: Optional[bool] = False) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets Lists in a Space that are not contained within any Folder.
    Returns a dictionary containing the list of folderless Lists or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/space/{space_id}/list"
    params = {"archived": str(archived).lower()}
    return api._make_request("GET", endpoint, params=params)

def get_list(list_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets details about a specific List.
    Returns a dictionary containing the List details or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/list/{list_id}"
    return api._make_request("GET", endpoint)

# --- Members ---
def get_task_members(task_id: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Gets members (users) assigned to or associated with a task.
    Returns a list of member dictionaries or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/task/{task_id}/member"
    response = api._make_request("GET", endpoint)
    # Check for error dict before accessing 'members'
    if isinstance(response, dict) and "error_code" in response:
        return response
    return response.get("members", []) # Assuming success structure {'members': [...]} or empty dict

def get_list_members(list_id: str) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Gets members (users) who have access to a specific List.
    Returns a list of member dictionaries or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/list/{list_id}/member"
    response = api._make_request("GET", endpoint)
    # Check for error dict before accessing 'members'
    if isinstance(response, dict) and "error_code" in response:
        return response
    return response.get("members", []) # Assuming success structure {'members': [...]} or empty dict

# --- Shared Hierarchy ---
def get_shared_hierarchy(team_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the shared hierarchy for the authorized user in a Workspace.
    Returns a dictionary containing the shared hierarchy details or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/shared"
    return api._make_request("GET", endpoint)

# --- Spaces ---
def get_spaces(team_id: str, archived: Optional[bool] = False) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets Spaces within a specific Workspace.
    Returns a dictionary containing the list of Spaces or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/space"
    params = {"archived": str(archived).lower()}
    return api._make_request("GET", endpoint, params=params)

def get_space(space_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets details about a specific Space.
    Returns a dictionary containing the Space details or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/space/{space_id}"
    return api._make_request("GET", endpoint)

# --- Tags ---
def get_space_tags(space_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets Tags available in a specific Space.
    Returns a dictionary containing the list of tags or an error dictionary.
    """
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
              custom_fields: Optional[str] = None, # JSON string
              custom_items: Optional[List[int]] = None,
              parent: Optional[str] = None, include_subtasks: Optional[bool] = None # Deprecated
              ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets tasks from a specific List, with extensive filtering options.
    Returns a dictionary containing the list of tasks or an error dictionary.
    """
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
             include_markdown_description: Optional[bool] = None, custom_task_ids: Optional[bool] = None, team_id: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets details about a specific task.
    Returns a dictionary containing the task details or an error dictionary.
    """
    api = ClickUpAPI()
    params = {}
    if include_subtasks is not None:
        params["include_subtasks"] = str(include_subtasks).lower()
    if include_markdown_description is not None:
        params["include_markdown_description"] = str(include_markdown_description).lower()

    endpoint = f"/task/{task_id}"

    if custom_task_ids:
        if not team_id:
             # Keep raising config error here as it's invalid input before the API call
             raise ValueError("team_id is required when custom_task_ids is true.")
        params["custom_task_ids"] = "true"
        params["team_id"] = team_id

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
                             ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets tasks for a Workspace (Team), filtered by various criteria.
    Returns a dictionary containing the list of tasks or an error dictionary.
    """
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

def get_task_time_in_status(task_id: str, custom_task_ids: Optional[bool] = None, team_id: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the time spent by a task in each status.
    Returns a dictionary containing the time in status details or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/task/{task_id}/time_in_status"
    params = {}
    if custom_task_ids:
        if not team_id:
            # Keep raising config error here
            raise ValueError("team_id is required when custom_task_ids is true.")
        params["custom_task_ids"] = "true"
        params["team_id"] = team_id

    return api._make_request("GET", endpoint, params=params)

def get_bulk_tasks_time_in_status(task_ids: List[str], custom_task_ids: Optional[bool] = None, team_id: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the time spent in status for multiple tasks.
    Returns a dictionary containing the time in status details or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = "/task/bulk_time_in_status/task_ids"
    params = {"task_ids": task_ids}
    if custom_task_ids:
         if not team_id:
             # Keep raising config error here
             raise ValueError("team_id is required when custom_task_ids is true.")
         params["custom_task_ids"] = "true"
         params["team_id"] = team_id

    return api._make_request("GET", endpoint, params=params)

# --- Templates ---
def get_task_templates(team_id: str, page: int, space_id: Optional[int] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets task templates for a Workspace.
    Returns a dictionary containing the list of task templates or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/template"
    params: Dict[str, Any] = {"page": page}
    if space_id is not None:
        params["space_id"] = space_id
    return api._make_request("GET", endpoint, params=params)

# --- Time Tracking ---
def get_time_entries(team_id: str, start_date: Optional[int] = None,
                     end_date: Optional[int] = None, assignee: Optional[str] = None,
                     include_task_tags: Optional[bool] = None, include_location_names: Optional[bool] = None,
                     space_id: Optional[str] = None, folder_id: Optional[str] = None,
                     list_id: Optional[str] = None, task_id: Optional[str] = None,
                     custom_task_ids: Optional[bool] = None, task_team_id: Optional[str] = None
                     ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets time entries within a date range for a Workspace (Team).
    Returns a dictionary containing the list of time entries or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/time_entries"
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
                # Keep raising config error here
                raise ValueError("task_team_id is required when custom_task_ids is true and task_id is provided.")
            params["custom_task_ids"] = "true"
            params["team_id"] = task_team_id

    return api._make_request("GET", endpoint, params=params)

def get_singular_time_entry(team_id: str, timer_id: str, include_task_tags: Optional[bool] = None,
                            include_location_names: Optional[bool] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets details for a specific time entry.
    Returns a dictionary containing the details or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/time_entries/{timer_id}"
    params = {}
    if include_task_tags is not None:
        params["include_task_tags"] = str(include_task_tags).lower()
    if include_location_names is not None:
        params["include_location_names"] = str(include_location_names).lower()
    return api._make_request("GET", endpoint, params=params)

def get_time_entry_history(team_id: str, timer_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the history of changes for a specific time entry.
    Returns a dictionary containing the history or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/time_entries/{timer_id}/history"
    return api._make_request("GET", endpoint)

def get_running_time_entry(team_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the currently running time entry for the authorized user.
    Returns a dictionary containing the running time entry or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/time_entries/current"
    return api._make_request("GET", endpoint)

def get_all_time_entry_tags(team_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets all tags used in time entries for a Workspace.
    Returns a dictionary containing the list of tags or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/time_entries/tags"
    return api._make_request("GET", endpoint)

# --- Users ---
def get_user(team_id: str, user_id: int) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets information about a specific user in a Workspace.
    Returns a dictionary containing the user details or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/user/{user_id}"
    return api._make_request("GET", endpoint)

# --- Views ---
def get_team_views(team_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets "Everything" level views (Workspace views).
    Returns a dictionary containing the list of Workspace views or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/team/{team_id}/view"
    return api._make_request("GET", endpoint)

def get_space_views(space_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets views available in a specific Space.
    Returns a dictionary containing the list of Space views or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/space/{space_id}/view"
    return api._make_request("GET", endpoint)

def get_folder_views(folder_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets views available in a specific Folder.
    Returns a dictionary containing the list of Folder views or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/folder/{folder_id}/view"
    return api._make_request("GET", endpoint)

def get_list_views(list_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets views available in a specific List.
    Returns a dictionary containing the list of List views or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/list/{list_id}/view"
    return api._make_request("GET", endpoint)

def get_view(view_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets details about a specific view.
    Returns a dictionary containing the view details or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/view/{view_id}"
    return api._make_request("GET", endpoint)

def get_view_tasks(view_id: str, page: Optional[int] = 0, include_closed: Optional[bool] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets tasks that are visible in a specific view.
    Returns a dictionary containing the list of tasks or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/view/{view_id}/task"
    params = {}
    if page is not None: # API default is 0
         params["page"] = page
    if include_closed is not None:
         params["include_closed"] = str(include_closed).lower()
    return api._make_request("GET", endpoint, params=params)

# --- Chat (Experimental) ---
def get_chat_channels(team_id: str, with_members: Optional[bool] = None,
                      with_last_message: Optional[bool] = None, types: Optional[List[str]] = None,
                      filter_unread: Optional[bool] = None, filter_mentions: Optional[bool] = None,
                      continuation: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Retrieves chat channels for a Workspace.
    Returns a dictionary containing the list of chat channels or an error dictionary.
    """
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
                     with_last_message: Optional[bool] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets details for a specific chat channel.
    Returns a dictionary containing the chat channel details or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/channel/{channel_id}"
    params = {}
    if with_members is not None:
        params["with_members"] = str(with_members).lower()
    if with_last_message is not None:
        params["with_last_message"] = str(with_last_message).lower()
    return api._make_request("GET", endpoint, params=params)

def get_chat_channel_followers(channel_id: str, continuation: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the followers of a specific chat channel.
    Returns a dictionary containing the list of channel followers or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/channel/{channel_id}/follower"
    params = {}
    if continuation:
        params["continuation"] = continuation
    return api._make_request("GET", endpoint, params=params)

def get_chat_channel_members(channel_id: str, continuation: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets the members of a specific chat channel.
    Returns a dictionary containing the list of channel members or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/channel/{channel_id}/member"
    params = {}
    if continuation:
        params["continuation"] = continuation
    return api._make_request("GET", endpoint, params=params)

def get_chat_messages(channel_id: str, before_message_id: Optional[str] = None,
                      after_message_id: Optional[str] = None, include_deleted: Optional[bool] = None,
                      include_reactions: Optional[bool] = None, include_replies: Optional[bool] = None,
                      reverse: Optional[bool] = None, limit: Optional[int] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Retrieves messages from a specific chat channel.
    Returns a dictionary containing the list of chat messages or an error dictionary.
    """
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
                          continuation: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets reactions for a specific chat message.
    Returns a dictionary containing the list of reactions or an error dictionary.
    """
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
                        continuation: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Retrieves replies to a specific chat message.
    Returns a dictionary containing the list of replies or an error dictionary.
    """
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

def get_tagged_users_for_message(message_id: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Gets users tagged (mentioned) in a specific chat message.
    Returns a dictionary containing the list of tagged users or an error dictionary.
    """
    api = ClickUpAPI()
    endpoint = f"/message/{message_id}/tagged_user"
    return api._make_request("GET", endpoint)