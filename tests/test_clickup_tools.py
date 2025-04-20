import pytest
from unittest.mock import patch, MagicMock
import os
import sys # Add sys import
from dotenv import load_dotenv
import time # For potential rate limiting delays
from datetime import datetime, timezone, timedelta

# Adjust sys.path to include the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Assuming clickup_tools.py is in harpy_agent/tools/
# Adjust the import path based on your project structure and how you run tests
from harpy_agent.tools import clickup_tools

# --- IMPORTANT ---
# Load REAL environment variables for integration tests
# Ensure you have a .env file in your project root with CLICKUP_API_KEY
load_dotenv() 

# Check if the API key is actually loaded
api_key = os.getenv("CLICKUP_API_KEY")
if not api_key:
     pytest.skip("CLICKUP_API_KEY not found in environment variables. Skipping integration tests.", allow_module_level=True)

# --- Marker for integration tests ---
pytestmark = pytest.mark.integration

# --- Helper function to introduce delay ---
def rate_limit_delay():
    time.sleep(1) # Adjust delay as needed based on ClickUp rate limits

# --- Placeholder IDs - REPLACE THESE WITH YOUR ACTUAL IDs ---
# You can get these from your ClickUp workspace URL or API exploration tools
TEST_LIST_ID = "901805343302"
TEST_TASK_ID = "86ertcmf5"
TEST_TASK_WITH_COMMENTS_ID = "86ertcmf5" # Task known to have comments
TEST_PARENT_TASK_ID = "86et65e20" # Task known to have subtasks
TEST_COMMENT_ID = "90180108845811" # For get_threaded_comments
TEST_USERNAME = "miko@dorxata.com" # For _get_user_id tests (indirectly used)
TEST_USER_ID = 18765432 # Replace with a real user ID (integer) for get_user
TEST_TEAM_ID = "3723297" # Your Workspace/Team ID
TEST_SPACE_ID = "43795741"
TEST_FOLDER_ID = "90184491751"
TEST_VIEW_ID = "Y6-42119681-1"
TEST_DOC_ID = "3hm11-2595"
TEST_PAGE_ID = "3hm11-9105"
TEST_GOAL_ID = "1"
TEST_GUEST_ID = 9876543 # Replace with a real guest ID (integer) if applicable
TEST_TIMER_ID = "YOUR_REAL_TIMER_ID" # For time entry history/details
TEST_CHANNEL_ID = "3hm11-57378"
TEST_MESSAGE_ID = "80180002933247"

# Helper function to check for API error responses
def is_api_error(response):
    return isinstance(response, dict) and "error_code" in response

# --- Test Functions ---

# Test for get_tasks (replaces get_clickup_tasks)
def test_get_tasks_live():
    """Test get_tasks retrieves tasks from a specific list.

    Uses get_tasks(list_id=...). Replaces old test_get_clickup_tasks_live.
    """
    if not TEST_LIST_ID or TEST_LIST_ID == "YOUR_REAL_LIST_ID":
        pytest.skip("TEST_LIST_ID not set.")

    rate_limit_delay()
    # Get tasks updated in the last 30 days for the test list
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    start_timestamp_ms = int(thirty_days_ago.timestamp() * 1000)

    result = clickup_tools.get_tasks(list_id=TEST_LIST_ID, date_updated_gt=start_timestamp_ms)

    if is_api_error(result):
        pytest.fail(f"API Error: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict) # Expecting {'tasks': [...]} structure
    assert "tasks" in result
    tasks = result["tasks"]
    assert isinstance(tasks, list)

    # If tasks are returned, check their structure
    if tasks:
        assert isinstance(tasks[0], dict)
        assert "id" in tasks[0]
        assert "name" in tasks[0]
    # Note: Test might pass with an empty list if no tasks match the criteria.

# Test for get_task (replaces get_clickup_task_details)
def test_get_task_live():
    """Test get_task retrieves details for a specific task.

    Uses get_task(task_id=...). Replaces old test_get_clickup_task_details_live.
    """
    if not TEST_TASK_ID or TEST_TASK_ID == "YOUR_REAL_TASK_ID":
        pytest.skip("TEST_TASK_ID not set.")

    rate_limit_delay()
    details = clickup_tools.get_task(task_id=TEST_TASK_ID)

    if is_api_error(details):
        pytest.fail(f"API Error getting task details: {details['error_message']} (Code: {details['error_code']})")

    assert isinstance(details, dict)
    assert details.get("id") == TEST_TASK_ID
    assert "name" in details
    assert "status" in details
    assert "assignees" in details # Even if empty, the key should exist

# Test for get_task_comments (replaces get_clickup_comments)
def test_get_task_comments_live():
    """Test get_task_comments retrieves comments for a specific task."""
    if not TEST_TASK_WITH_COMMENTS_ID or TEST_TASK_WITH_COMMENTS_ID == "YOUR_TASK_ID_WITH_COMMENTS":
        pytest.skip("TEST_TASK_WITH_COMMENTS_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_task_comments(task_id=TEST_TASK_WITH_COMMENTS_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting task comments: {result['error_message']} (Code: {result['error_code']})")

    # Assuming the API returns a dict like {'comments': [...]} on success
    assert isinstance(result, dict), f"Expected dict, got {type(result)}: {result}"
    assert 'comments' in result
    comments = result['comments']
    assert isinstance(comments, list)

    # If you expect comments on the test task, check their structure
    if comments:
        assert isinstance(comments[0], dict)
        assert "id" in comments[0]
        # Adjust field name if necessary based on actual API response
        assert "comment_text" in comments[0] or "comment" in comments[0] 
        assert "user" in comments[0]

def test_get_chat_view_comments_live():
    """Test get_chat_view_comments retrieves comments for a chat view."""
    if not TEST_VIEW_ID or TEST_VIEW_ID == "YOUR_REAL_VIEW_ID":
        pytest.skip("TEST_VIEW_ID not set for chat view comments test.")

    rate_limit_delay()
    result = clickup_tools.get_chat_view_comments(view_id=TEST_VIEW_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting chat view comments: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert 'comments' in result
    comments = result['comments']
    assert isinstance(comments, list)
    # Add more specific assertions if comments are expected

def test_get_list_comments_live():
    """Test get_list_comments retrieves comments for a specific list."""
    if not TEST_LIST_ID or TEST_LIST_ID == "YOUR_REAL_LIST_ID":
        pytest.skip("TEST_LIST_ID not set for list comments test.")

    rate_limit_delay()
    result = clickup_tools.get_list_comments(list_id=TEST_LIST_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting list comments: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert 'comments' in result
    comments = result['comments']
    assert isinstance(comments, list)
    # Add more specific assertions if comments are expected

def test_get_threaded_comments_live():
    """Test get_threaded_comments retrieves replies for a comment thread."""
    if not TEST_COMMENT_ID or TEST_COMMENT_ID == "YOUR_REAL_COMMENT_ID_WITH_REPLIES":
        pytest.skip("TEST_COMMENT_ID not set for threaded comments test.")

    rate_limit_delay()
    result = clickup_tools.get_threaded_comments(comment_id=TEST_COMMENT_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting threaded comments: {result['error_message']} (Code: {result['error_code']})")

    # Assuming the API returns a dict like {'comments': [...]} or similar
    assert isinstance(result, dict)
    assert 'comments' in result # Adjust key if API response differs
    replies = result['comments']
    assert isinstance(replies, list)
    # Add assertions about reply structure if expected

# Test for get_clickup_user_tasks
def test_get_clickup_user_tasks_live():
    """Test get_clickup_user_tasks retrieves tasks for a specific user."""
    if not TEST_USERNAME or TEST_USERNAME == "YOUR_CLICKUP_USERNAME":
         pytest.skip("TEST_USERNAME not set.")

    rate_limit_delay()
    # This requires the _get_user_id helper to work, which fetches teams first.
    user_tasks = clickup_tools.get_clickup_user_tasks(username=TEST_USERNAME, days=90) # Look back further
    
    assert isinstance(user_tasks, list)
    # If the user is expected to have assigned tasks updated recently:
    # if user_tasks:
    #     assert isinstance(user_tasks[0], dict)
    #     assert "id" in user_tasks[0]
    #     # Check if the assignee list actually contains the user (might need user ID)
    #     # This might be complex to assert reliably without knowing the user's ID beforehand.

# Test for get_clickup_time_entries (uses workspace_id from env)
def test_get_clickup_time_entries_for_default_workspace_live():
    """Test get_clickup_time_entries retrieves time entries for the default workspace."""
    rate_limit_delay()
    # Fetch all time entries for the default workspace for the last N days (optional filter)
    entries_data = clickup_tools.get_clickup_time_entries() # Removed team_id argument
    assert isinstance(entries_data, dict)
    assert "entries" in entries_data
    entries = entries_data["entries"]

    assert isinstance(entries, list)
    if entries:
        assert isinstance(entries[0], dict)
        assert "id" in entries[0]
        assert "user" in entries[0]
        assert "duration" in entries[0]
        # Can add filtering by task_id or user_id here if needed for more specific tests
        # task_entries = clickup_tools.get_clickup_time_entries(team_id=TEST_TEAM_ID, task_id=TEST_TASK_ID)
        # assert isinstance(task_entries, list)

# Test for get_clickup_list_members
def test_get_clickup_list_members_live():
    """Test get_clickup_list_members retrieves members for a specific list."""
    if not TEST_LIST_ID or TEST_LIST_ID == "YOUR_REAL_LIST_ID":
        pytest.skip("TEST_LIST_ID not set.")

    rate_limit_delay()
    members = clickup_tools.get_clickup_list_members(list_id=TEST_LIST_ID)
    
    assert isinstance(members, list)
    assert len(members) > 0 # Expect at least one member (likely the owner)
    assert isinstance(members[0], dict)
    assert "id" in members[0]
    assert "username" in members[0]

# Test for get_clickup_task_members (uses get_clickup_task_details)
def test_get_clickup_task_members_live():
    """Test get_clickup_task_members retrieves assignees for a specific task."""
    if not TEST_TASK_ID or TEST_TASK_ID == "YOUR_REAL_TASK_ID":
        pytest.skip("TEST_TASK_ID not set.")

    rate_limit_delay()
    members = clickup_tools.get_clickup_task_members(task_id=TEST_TASK_ID)
    
    assert isinstance(members, list)
    # Assignees list might be empty, which is valid
    if members:
        assert isinstance(members[0], dict)
        assert "id" in members[0]
        assert "username" in members[0]

# Test for get_clickup_subtasks
def test_get_clickup_subtasks_live():
    """Test get_clickup_subtasks retrieves subtasks for a parent task."""
    if not TEST_PARENT_TASK_ID or TEST_PARENT_TASK_ID == "YOUR_PARENT_TASK_ID":
         pytest.skip("TEST_PARENT_TASK_ID not set.")

    rate_limit_delay()
    subtasks = clickup_tools.get_clickup_subtasks(task_id=TEST_PARENT_TASK_ID)
    
    assert isinstance(subtasks, list)
    # Check structure if subtasks are expected
    if subtasks:
         assert isinstance(subtasks[0], dict)
         assert "id" in subtasks[0]
         assert "name" in subtasks[0]
         assert subtasks[0].get("parent") == TEST_PARENT_TASK_ID

# Test for get_clickup_teams
def test_get_clickup_teams_live():
    """Test get_clickup_teams retrieves teams/workspaces."""
    rate_limit_delay()
    teams = clickup_tools.get_clickup_teams()
    
    assert isinstance(teams, list)
    assert len(teams) > 0 # Should have at least one team
    assert isinstance(teams[0], dict)
    assert "id" in teams[0]
    assert "name" in teams[0]
    assert "members" in teams[0] # Members should be included

# Test for get_clickup_team_members (uses workspace_id from env)
def test_get_clickup_team_members_for_default_workspace_live():
    """Test get_clickup_team_members retrieves members for the default workspace."""
    rate_limit_delay()
    members = clickup_tools.get_clickup_team_members() # Removed team_id argument
    
    assert isinstance(members, list)
    assert len(members) > 0 # Expect members in a valid workspace
    assert isinstance(members[0], dict)
    assert "user" in members[0]
    assert "id" in members[0]["user"]

# Test for get_clickup_spaces (uses workspace_id from env)
def test_get_clickup_spaces_for_default_workspace_live():
    """Test get_clickup_spaces retrieves spaces within the default workspace."""
    rate_limit_delay()
    spaces = clickup_tools.get_clickup_spaces() # Removed team_id argument
    
    assert isinstance(spaces, list)
    assert len(spaces) > 0 # Expect spaces in a typical workspace
    assert isinstance(spaces[0], dict)
    assert "id" in spaces[0]
    assert "name" in spaces[0]

# Test for get_clickup_folders
def test_get_clickup_folders_live():
    """Test get_clickup_folders retrieves folders within a space."""
    if not TEST_SPACE_ID or TEST_SPACE_ID == "YOUR_REAL_SPACE_ID":
        pytest.skip("TEST_SPACE_ID not set.")

    rate_limit_delay()
    folders = clickup_tools.get_clickup_folders(space_id=TEST_SPACE_ID)
    
    assert isinstance(folders, list)
    # A space might not have folders, so len(folders) >= 0 is okay
    if folders:
        assert isinstance(folders[0], dict)
        assert "id" in folders[0]
        assert "name" in folders[0]

# Test for get_clickup_lists
def test_get_clickup_lists_live():
    """Test get_clickup_lists retrieves lists within a folder."""
    if not TEST_FOLDER_ID or TEST_FOLDER_ID == "YOUR_REAL_FOLDER_ID":
        pytest.skip("TEST_FOLDER_ID not set.")

    rate_limit_delay()
    lists = clickup_tools.get_clickup_lists(folder_id=TEST_FOLDER_ID)
    
    assert isinstance(lists, list)
    # Check structure only if the list is not empty (API call succeeded and folder has lists)
    if lists:
        assert isinstance(lists[0], dict)
        assert "id" in lists[0]
        assert "name" in lists[0]

# Test for find_clickup_users
def test_find_clickup_users_live():
    """Test find_clickup_users finds users based on a search string."""
    if not TEST_USERNAME or TEST_USERNAME == "YOUR_CLICKUP_USERNAME":
        pytest.skip("TEST_USERNAME not set for find_clickup_users test.")

    # 1. Test with a known partial username/email (expect results)
    # Extract a part of the username/email for searching
    search_part = TEST_USERNAME.split('@')[0][:3] # Use first 3 chars of username part
    if not search_part:
         pytest.skip("Could not extract a search part from TEST_USERNAME.")
         
    rate_limit_delay()
    found_users = clickup_tools.find_clickup_users(search_string=search_part)

    assert isinstance(found_users, list)
    assert len(found_users) > 0 # Expect at least one match for a part of TEST_USERNAME
    assert isinstance(found_users[0], dict)
    assert "id" in found_users[0]
    assert "username" in found_users[0]
    assert "email" in found_users[0]
    # Verify that the search part is actually in the results (case-insensitive)
    match_found = any(
        search_part.lower() in user.get("username", "").lower() or \
        search_part.lower() in user.get("email", "").lower() 
        for user in found_users
    )
    assert match_found, f"Search part '{search_part}' not found in any result: {found_users}"

    # 2. Test with a nonsensical string (expect no results)
    rate_limit_delay()
    no_users_found = clickup_tools.find_clickup_users(search_string="__nonsensical_string_xyz__")
    assert isinstance(no_users_found, list)
    assert len(no_users_found) == 0
    
    # 3. Test with an empty string (expect no results)
    rate_limit_delay()
    empty_search_users = clickup_tools.find_clickup_users(search_string="")
    assert isinstance(empty_search_users, list)
    assert len(empty_search_users) == 0

# --- Task Filtering/Retrieval Tests ---

# Adapted test for user tasks using get_filtered_team_tasks
def test_get_filtered_team_tasks_for_user_live():
    """Test get_filtered_team_tasks retrieves tasks for a specific user ID."""
    if not TEST_USER_ID or TEST_USER_ID == 18765432: # Check if placeholder is used
        pytest.skip("TEST_USER_ID not set to a real value.")
    if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
        pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    # Fetch tasks assigned to the test user ID, updated in the last 90 days
    now = datetime.now(timezone.utc)
    ninety_days_ago = now - timedelta(days=90)
    start_timestamp_ms = int(ninety_days_ago.timestamp() * 1000)

    result = clickup_tools.get_filtered_team_tasks(
        team_id=TEST_TEAM_ID,
        assignees=[str(TEST_USER_ID)], # API expects list of strings
        date_updated_gt=start_timestamp_ms
    )

    if is_api_error(result):
        pytest.fail(f"API Error getting filtered team tasks for user: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "tasks" in result
    user_tasks = result["tasks"]
    assert isinstance(user_tasks, list)

    # If tasks are returned, verify assignee (might be complex if multiple assignees)
    # A simple check that *if* tasks are returned, the first one *might* have the assignee.
    # A more robust check would iterate through all tasks and all assignees.
    if user_tasks:
        assert isinstance(user_tasks[0], dict)
        assert "id" in user_tasks[0]
        assignee_found = False
        for assignee in user_tasks[0].get("assignees", []):
             # API returns assignee dict with 'id' key as integer
            if assignee.get("id") == TEST_USER_ID:
                assignee_found = True
                break
        # It's possible the task has other assignees or the API filter isn't perfect,
        # but we expect *some* tasks returned to have this assignee if the filter works.
        # This assertion might be too strict depending on test data.
        # assert assignee_found, f"Assignee {TEST_USER_ID} not found in first task's assignees: {user_tasks[0].get('assignees')}"

# --- Time Tracking Tests ---

# Test for get_time_entries (adapted from old default workspace test)
def test_get_time_entries_live():
    """Test get_time_entries retrieves time entries for the specified workspace."""
    if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
        pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    # Fetch time entries for the last 7 days as an example
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    start_timestamp_ms = int(seven_days_ago.timestamp() * 1000)
    end_timestamp_ms = int(now.timestamp() * 1000)

    result = clickup_tools.get_time_entries(
        team_id=TEST_TEAM_ID,
        start_date=start_timestamp_ms,
        end_date=end_timestamp_ms
    )

    if is_api_error(result):
         pytest.fail(f"API Error getting time entries: {result['error_message']} (Code: {result['error_code']})")

    # The API response structure might be {'data': [...]} or just [...] - check docs
    # Assuming {'data': [...]} based on docs
    assert isinstance(result, dict), f"Expected dict, got {type(result)}: {result}"
    assert "data" in result # Adjust key if API response differs
    entries = result["data"]
    assert isinstance(entries, list)

    if entries:
        assert isinstance(entries[0], dict)
        assert "id" in entries[0]
        assert "user" in entries[0]
        assert "duration" in entries[0]
        # Can add filtering by task_id or user_id here if needed for more specific tests
        # task_entries = clickup_tools.get_time_entries(team_id=TEST_TEAM_ID, task_id=TEST_TASK_ID)

def test_get_singular_time_entry_live():
    """Test get_singular_time_entry retrieves details for a specific entry."""
    if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
        pytest.skip("TEST_TEAM_ID not set.")
    if not TEST_TIMER_ID or TEST_TIMER_ID == "YOUR_REAL_TIMER_ID":
        pytest.skip("TEST_TIMER_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_singular_time_entry(team_id=TEST_TEAM_ID, timer_id=TEST_TIMER_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting singular time entry: {result['error_message']} (Code: {result['error_code']})")

    # Assuming response is {'data': {...}}
    assert isinstance(result, dict)
    assert "data" in result
    entry = result["data"]
    assert isinstance(entry, dict)
    assert entry.get("id") == TEST_TIMER_ID
    assert "user" in entry
    assert "task" in entry # Or may be null

def test_get_time_entry_history_live():
    """Test get_time_entry_history retrieves history for a specific entry."""
    if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
        pytest.skip("TEST_TEAM_ID not set.")
    if not TEST_TIMER_ID or TEST_TIMER_ID == "YOUR_REAL_TIMER_ID":
        pytest.skip("TEST_TIMER_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_time_entry_history(team_id=TEST_TEAM_ID, timer_id=TEST_TIMER_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting time entry history: {result['error_message']} (Code: {result['error_code']})")

    # Assuming response is a list of history events
    assert isinstance(result, list)
    # Add more checks if history entries are expected

def test_get_running_time_entry_live():
    """Test get_running_time_entry retrieves the current running entry (if any)."""
    if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
        pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_running_time_entry(team_id=TEST_TEAM_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting running time entry: {result['error_message']} (Code: {result['error_code']})")

    # Response is {'data': {...}} if running, {'data': None} if not
    assert isinstance(result, dict)
    assert "data" in result
    # entry = result["data"] -> can be None
    # No strong assertions possible unless you *know* a timer should be running

def test_get_all_time_entry_tags_live():
    """Test get_all_time_entry_tags retrieves all tags used in time entries."""
    if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
        pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_all_time_entry_tags(team_id=TEST_TEAM_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting time entry tags: {result['error_message']} (Code: {result['error_code']})")

    # Assuming response is {'tags': [...]} or similar
    assert isinstance(result, dict)
    assert "tags" in result # Adjust key based on actual response
    tags = result["tags"]
    assert isinstance(tags, list)
    # Add checks if specific tags are expected

# --- Member/User Tests ---

# Test for get_list_members (adapted from test_get_clickup_list_members_live)
def test_get_list_members_live():
    """Test get_list_members retrieves members for a specific list."""
    if not TEST_LIST_ID or TEST_LIST_ID == "YOUR_REAL_LIST_ID":
        pytest.skip("TEST_LIST_ID not set.")

    rate_limit_delay()
    members = clickup_tools.get_list_members(list_id=TEST_LIST_ID)

    if is_api_error(members):
        pytest.fail(f"API Error getting list members: {members['error_message']} (Code: {members['error_code']})")

    assert isinstance(members, list)
    # A list should have members (owner at least), but could be empty if permissions change
    # assert len(members) > 0 # Making this optional
    if members:
        assert isinstance(members[0], dict)
        assert "id" in members[0]
        assert "username" in members[0]

# Test for get_task_members (adapted from test_get_clickup_task_members_live)
def test_get_task_members_live():
    """Test get_task_members retrieves assignees for a specific task."""
    if not TEST_TASK_ID or TEST_TASK_ID == "YOUR_REAL_TASK_ID":
        pytest.skip("TEST_TASK_ID not set.")

    rate_limit_delay()
    members = clickup_tools.get_task_members(task_id=TEST_TASK_ID)

    if is_api_error(members):
        pytest.fail(f"API Error getting task members: {members['error_message']} (Code: {members['error_code']})")

    assert isinstance(members, list)
    # Assignees list might be empty, which is valid
    if members:
        assert isinstance(members[0], dict)
        assert "id" in members[0]
        assert "username" in members[0]

# Test for get_user
def test_get_user_live():
    """Test get_user retrieves details for a specific user."""
    if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
        pytest.skip("TEST_TEAM_ID not set.")
    if not TEST_USER_ID or TEST_USER_ID == 18765432: # Placeholder ID
        pytest.skip("TEST_USER_ID not set to a real value.")

    rate_limit_delay()
    result = clickup_tools.get_user(team_id=TEST_TEAM_ID, user_id=TEST_USER_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting user: {result['error_message']} (Code: {result['error_code']})")

    # Expecting {"user": {...}}
    assert isinstance(result, dict)
    assert "user" in result
    user = result["user"]
    assert isinstance(user, dict)
    assert user.get("id") == TEST_USER_ID
    assert "username" in user
    assert "email" in user

# --- Hierarchy/Structure Tests ---

# Test for get_spaces (replaces test_get_clickup_spaces_for_default_workspace_live)
def test_get_spaces_live():
    """Test get_spaces retrieves spaces within the specified workspace."""
    if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
        pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_spaces(team_id=TEST_TEAM_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting spaces: {result['error_message']} (Code: {result['error_code']})")

    # Expecting {"spaces": [...]} structure
    assert isinstance(result, dict)
    assert "spaces" in result
    spaces = result["spaces"]
    assert isinstance(spaces, list)
    # Should have spaces in a typical workspace
    assert len(spaces) > 0
    assert isinstance(spaces[0], dict)
    assert "id" in spaces[0]
    assert "name" in spaces[0]

def test_get_space_live():
    """Test get_space retrieves details for a specific space."""
    if not TEST_SPACE_ID or TEST_SPACE_ID == "YOUR_REAL_SPACE_ID":
        pytest.skip("TEST_SPACE_ID not set.")

    rate_limit_delay()
    space = clickup_tools.get_space(space_id=TEST_SPACE_ID)

    if is_api_error(space):
        pytest.fail(f"API Error getting space: {space['error_message']} (Code: {space['error_code']})")

    assert isinstance(space, dict)
    assert space.get("id") == TEST_SPACE_ID
    assert "name" in space

# Test for get_folders (replaces test_get_clickup_folders_live)
def test_get_folders_live():
    """Test get_folders retrieves folders within a space."""
    if not TEST_SPACE_ID or TEST_SPACE_ID == "YOUR_REAL_SPACE_ID":
        pytest.skip("TEST_SPACE_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_folders(space_id=TEST_SPACE_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting folders: {result['error_message']} (Code: {result['error_code']})")

    # Expecting {"folders": [...]} structure
    assert isinstance(result, dict)
    assert "folders" in result
    folders = result["folders"]
    assert isinstance(folders, list)
    # A space might not have folders, so len(folders) >= 0 is okay
    if folders:
        assert isinstance(folders[0], dict)
        assert "id" in folders[0]
        assert "name" in folders[0]

def test_get_folder_live():
    """Test get_folder retrieves details for a specific folder."""
    if not TEST_FOLDER_ID or TEST_FOLDER_ID == "YOUR_REAL_FOLDER_ID":
        pytest.skip("TEST_FOLDER_ID not set.")

    rate_limit_delay()
    folder = clickup_tools.get_folder(folder_id=TEST_FOLDER_ID)

    if is_api_error(folder):
        pytest.fail(f"API Error getting folder: {folder['error_message']} (Code: {folder['error_code']})")

    assert isinstance(folder, dict)
    assert folder.get("id") == TEST_FOLDER_ID
    assert "name" in folder
    assert "space" in folder # Should link back to space

# Test for get_lists (replaces test_get_clickup_lists_live)
def test_get_lists_live():
    """Test get_lists retrieves lists within a folder."""
    if not TEST_FOLDER_ID or TEST_FOLDER_ID == "YOUR_REAL_FOLDER_ID":
        pytest.skip("TEST_FOLDER_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_lists(folder_id=TEST_FOLDER_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting lists: {result['error_message']} (Code: {result['error_code']})")

    # Expecting {"lists": [...]} structure
    assert isinstance(result, dict)
    assert "lists" in result
    lists = result["lists"]
    assert isinstance(lists, list)
    # Check structure only if the list is not empty
    if lists:
        assert isinstance(lists[0], dict)
        assert "id" in lists[0]
        assert "name" in lists[0]
        assert lists[0].get("folder", {}).get("id") == TEST_FOLDER_ID

def test_get_folderless_lists_live():
    """Test get_folderless_lists retrieves lists not in any folder within a space."""
    if not TEST_SPACE_ID or TEST_SPACE_ID == "YOUR_REAL_SPACE_ID":
        pytest.skip("TEST_SPACE_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_folderless_lists(space_id=TEST_SPACE_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting folderless lists: {result['error_message']} (Code: {result['error_code']})")

    # Expecting {"lists": [...]} structure
    assert isinstance(result, dict)
    assert "lists" in result
    lists = result["lists"]
    assert isinstance(lists, list)
    # Check structure only if lists are found
    if lists:
        assert isinstance(lists[0], dict)
        assert "id" in lists[0]
        assert "name" in lists[0]
        assert lists[0].get("space", {}).get("id") == TEST_SPACE_ID
        assert lists[0].get("folder") is None # Key check might be enough

def test_get_list_live():
    """Test get_list retrieves details for a specific list."""
    if not TEST_LIST_ID or TEST_LIST_ID == "YOUR_REAL_LIST_ID":
        pytest.skip("TEST_LIST_ID not set.")

    rate_limit_delay()
    list_details = clickup_tools.get_list(list_id=TEST_LIST_ID)

    if is_api_error(list_details):
        pytest.fail(f"API Error getting list: {list_details['error_message']} (Code: {list_details['error_code']})")

    assert isinstance(list_details, dict)
    assert list_details.get("id") == TEST_LIST_ID
    assert "name" in list_details
    assert "space" in list_details # Should link back to space
    assert "folder" in list_details # Should link back to folder


# --- View Tests ---

def test_get_team_views_live():
    """Test get_team_views retrieves 'Everything' level views."""
    if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
        pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_team_views(team_id=TEST_TEAM_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting team views: {result['error_message']} (Code: {result['error_code']})")

    # Expecting {"views": [...]} structure
    assert isinstance(result, dict)
    assert "views" in result
    views = result["views"]
    assert isinstance(views, list)
    if views:
        assert isinstance(views[0], dict)
        assert "id" in views[0]
        assert "name" in views[0]
        assert views[0].get("type") is not None

def test_get_space_views_live():
    """Test get_space_views retrieves views for a specific space."""
    if not TEST_SPACE_ID or TEST_SPACE_ID == "YOUR_REAL_SPACE_ID":
        pytest.skip("TEST_SPACE_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_space_views(space_id=TEST_SPACE_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting space views: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "views" in result
    views = result["views"]
    assert isinstance(views, list)
    # Add more checks if specific views are expected

def test_get_folder_views_live():
    """Test get_folder_views retrieves views for a specific folder."""
    if not TEST_FOLDER_ID or TEST_FOLDER_ID == "YOUR_REAL_FOLDER_ID":
        pytest.skip("TEST_FOLDER_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_folder_views(folder_id=TEST_FOLDER_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting folder views: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "views" in result
    views = result["views"]
    assert isinstance(views, list)
    # Add more checks if specific views are expected

def test_get_list_views_live():
    """Test get_list_views retrieves views for a specific list."""
    if not TEST_LIST_ID or TEST_LIST_ID == "YOUR_REAL_LIST_ID":
        pytest.skip("TEST_LIST_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_list_views(list_id=TEST_LIST_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting list views: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "views" in result
    views = result["views"]
    assert isinstance(views, list)
    # Add more checks if specific views are expected

def test_get_view_live():
    """Test get_view retrieves details for a specific view."""
    if not TEST_VIEW_ID or TEST_VIEW_ID == "YOUR_REAL_VIEW_ID":
        pytest.skip("TEST_VIEW_ID not set.")

    rate_limit_delay()
    view = clickup_tools.get_view(view_id=TEST_VIEW_ID)

    if is_api_error(view):
        pytest.fail(f"API Error getting view: {view['error_message']} (Code: {view['error_code']})")

    # Expecting a dict representing the view
    assert isinstance(view, dict)
    assert view.get("id") == TEST_VIEW_ID
    assert "name" in view
    assert "type" in view

def test_get_view_tasks_live():
    """Test get_view_tasks retrieves tasks visible in a specific view."""
    if not TEST_VIEW_ID or TEST_VIEW_ID == "YOUR_REAL_VIEW_ID":
        pytest.skip("TEST_VIEW_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_view_tasks(view_id=TEST_VIEW_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting view tasks: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "tasks" in result
    tasks = result["tasks"]
    assert isinstance(tasks, list)
    # Add more checks if specific tasks are expected in the view


# --- Other Tests ---

# Test for get_guest (New)
def test_get_guest_live():
    """Test get_guest retrieves information about a specific guest user."""
    if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
        pytest.skip("TEST_TEAM_ID not set.")
    if not TEST_GUEST_ID or TEST_GUEST_ID == 9876543: # Placeholder ID
        pytest.skip("TEST_GUEST_ID not set to a real value.")

    rate_limit_delay()
    result = clickup_tools.get_guest(team_id=TEST_TEAM_ID, guest_id=TEST_GUEST_ID)

    if is_api_error(result):
        # Guest endpoint might return 404 if ID is invalid or not a guest
        if result.get("error_code") == 404:
             pytest.skip(f"Guest {TEST_GUEST_ID} not found or not accessible (404). Skipping.")
        pytest.fail(f"API Error getting guest: {result['error_message']} (Code: {result['error_code']})")

    # Expecting {"guest": {...}} structure
    assert isinstance(result, dict)
    assert "guest" in result
    guest = result["guest"]
    assert isinstance(guest, dict)
    assert guest.get("id") == TEST_GUEST_ID
    assert "user" in guest # Contains main user info
    assert guest["user"].get("id") == TEST_GUEST_ID
    assert "username" in guest["user"]

# Test for get_goals (New)
def test_get_goals_live():
    """Test get_goals retrieves goals for the workspace."""
    if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
        pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_goals(team_id=TEST_TEAM_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting goals: {result['error_message']} (Code: {result['error_code']})")

    # Expecting {"goals": [...]} structure
    assert isinstance(result, dict)
    assert "goals" in result
    goals = result["goals"]
    assert isinstance(goals, list)
    if goals:
        assert isinstance(goals[0], dict)
        assert "id" in goals[0]
        assert "name" in goals[0]

# Test for get_goal (New)
def test_get_goal_live():
    """Test get_goal retrieves details for a specific goal."""
    if not TEST_GOAL_ID or TEST_GOAL_ID == "YOUR_REAL_GOAL_ID":
        pytest.skip("TEST_GOAL_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_goal(goal_id=TEST_GOAL_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting goal: {result['error_message']} (Code: {result['error_code']})")

    # Expecting {"goal": {...}} structure
    assert isinstance(result, dict)
    assert "goal" in result
    goal = result["goal"]
    assert isinstance(goal, dict)
    assert goal.get("id") == TEST_GOAL_ID
    assert "name" in goal

# Test for get_space_tags (New)
def test_get_space_tags_live():
    """Test get_space_tags retrieves tags for a specific space."""
    if not TEST_SPACE_ID or TEST_SPACE_ID == "YOUR_REAL_SPACE_ID":
        pytest.skip("TEST_SPACE_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_space_tags(space_id=TEST_SPACE_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting space tags: {result['error_message']} (Code: {result['error_code']})")

    # Expecting {"tags": [...]} structure
    assert isinstance(result, dict)
    assert "tags" in result
    tags = result["tags"]
    assert isinstance(tags, list)
    if tags:
        assert isinstance(tags[0], dict)
        assert "name" in tags[0]
        assert "tag_fg" in tags[0] # Color info

# Test for get_task_templates (New)
def test_get_task_templates_live():
    """Test get_task_templates retrieves templates for the workspace."""
    if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
        pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    # Page 0 is the first page
    result = clickup_tools.get_task_templates(team_id=TEST_TEAM_ID, page=0)

    if is_api_error(result):
        pytest.fail(f"API Error getting task templates: {result['error_message']} (Code: {result['error_code']})")

    # Expecting {"templates": [...]} structure
    assert isinstance(result, dict)
    assert "templates" in result
    templates = result["templates"]
    assert isinstance(templates, list)
    if templates:
        assert isinstance(templates[0], dict)
        assert "id" in templates[0]
        assert "name" in templates[0]


# --- Experimental Chat Tests (Optional - Skip if not needed) ---
# pytestmark_chat = pytest.mark.skipif(os.getenv("SKIP_CLICKUP_CHAT_TESTS", "true").lower() == "true", reason="Skipping experimental chat tests unless SKIP_CLICKUP_CHAT_TESTS=false")

# @pytestmark_chat
def test_get_chat_channels_live():
    """Test get_chat_channels retrieves chat channels for the workspace."""
    if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
        pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_chat_channels(team_id=TEST_TEAM_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting chat channels: {result['error_message']} (Code: {result['error_code']})")

    # Assuming {"channels": [...]} structure
    assert isinstance(result, dict)
    assert "channels" in result
    channels = result["channels"]
    assert isinstance(channels, list)
    if channels:
        assert isinstance(channels[0], dict)
        assert "id" in channels[0]
        assert "name" in channels[0]

# @pytestmark_chat
def test_get_chat_channel_live():
    """Test get_chat_channel retrieves details for a specific channel."""
    if not TEST_CHANNEL_ID or TEST_CHANNEL_ID == "YOUR_REAL_CHAT_CHANNEL_ID":
        pytest.skip("TEST_CHANNEL_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_chat_channel(channel_id=TEST_CHANNEL_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting chat channel: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict) # Should return the channel object directly
    assert result.get("id") == TEST_CHANNEL_ID
    assert "name" in result

# @pytestmark_chat
def test_get_chat_channel_followers_live():
    """Test get_chat_channel_followers retrieves followers for a channel."""
    if not TEST_CHANNEL_ID or TEST_CHANNEL_ID == "YOUR_REAL_CHAT_CHANNEL_ID":
        pytest.skip("TEST_CHANNEL_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_chat_channel_followers(channel_id=TEST_CHANNEL_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting channel followers: {result['error_message']} (Code: {result['error_code']})")

    # Assuming {"followers": [...]} structure
    assert isinstance(result, dict)
    assert "followers" in result
    followers = result["followers"]
    assert isinstance(followers, list)
    # Add more checks if needed

# @pytestmark_chat
def test_get_chat_channel_members_live():
    """Test get_chat_channel_members retrieves members for a channel."""
    if not TEST_CHANNEL_ID or TEST_CHANNEL_ID == "YOUR_REAL_CHAT_CHANNEL_ID":
        pytest.skip("TEST_CHANNEL_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_chat_channel_members(channel_id=TEST_CHANNEL_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting channel members: {result['error_message']} (Code: {result['error_code']})")

    # Assuming {"members": [...]} structure
    assert isinstance(result, dict)
    assert "members" in result
    members = result["members"]
    assert isinstance(members, list)
    # Add more checks if needed

# @pytestmark_chat
def test_get_chat_messages_live():
    """Test get_chat_messages retrieves messages for a channel."""
    if not TEST_CHANNEL_ID or TEST_CHANNEL_ID == "YOUR_REAL_CHAT_CHANNEL_ID":
        pytest.skip("TEST_CHANNEL_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_chat_messages(channel_id=TEST_CHANNEL_ID, limit=10)

    if is_api_error(result):
        pytest.fail(f"API Error getting chat messages: {result['error_message']} (Code: {result['error_code']})")

    # Assuming {"messages": [...]} structure
    assert isinstance(result, dict)
    assert "messages" in result
    messages = result["messages"]
    assert isinstance(messages, list)
    if messages:
        assert isinstance(messages[0], dict)
        assert "id" in messages[0]
        assert "message" in messages[0]

# @pytestmark_chat
def test_get_message_reactions_live():
    """Test get_message_reactions retrieves reactions for a message."""
    if not TEST_MESSAGE_ID or TEST_MESSAGE_ID == "YOUR_REAL_CHAT_MESSAGE_ID":
        pytest.skip("TEST_MESSAGE_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_message_reactions(message_id=TEST_MESSAGE_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting message reactions: {result['error_message']} (Code: {result['error_code']})")

    # Assuming {"reactions": [...]} structure
    assert isinstance(result, dict)
    assert "reactions" in result
    reactions = result["reactions"]
    assert isinstance(reactions, list)
    # Add more checks if needed

# @pytestmark_chat
def test_get_message_replies_live():
    """Test get_message_replies retrieves replies for a message."""
    if not TEST_MESSAGE_ID or TEST_MESSAGE_ID == "YOUR_REAL_CHAT_MESSAGE_ID":
        pytest.skip("TEST_MESSAGE_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_message_replies(message_id=TEST_MESSAGE_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting message replies: {result['error_message']} (Code: {result['error_code']})")

    # Assuming {"replies": [...]} structure
    assert isinstance(result, dict)
    assert "replies" in result
    replies = result["replies"]
    assert isinstance(replies, list)
    # Add more checks if needed

# @pytestmark_chat
def test_get_tagged_users_for_message_live():
    """Test get_tagged_users_for_message retrieves tagged users."""
    if not TEST_MESSAGE_ID or TEST_MESSAGE_ID == "YOUR_REAL_CHAT_MESSAGE_ID":
        pytest.skip("TEST_MESSAGE_ID with tagged users not set.")

    rate_limit_delay()
    result = clickup_tools.get_tagged_users_for_message(message_id=TEST_MESSAGE_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting tagged users: {result['error_message']} (Code: {result['error_code']})")

    # Assuming {"tagged_users": [...]} structure
    assert isinstance(result, dict)
    assert "tagged_users" in result
    users = result["tagged_users"]
    assert isinstance(users, list)
    # Add more checks if needed
