import pytest
from unittest.mock import patch, MagicMock
import os
import sys # Add sys import
from dotenv import load_dotenv
import time # For potential rate limiting delays

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
TEST_LIST_ID = "901805343302"  # Replace with a List ID you have access to
TEST_TASK_ID = "86ertcmf5" # Replace with a Task ID within the above list
TEST_TASK_WITH_COMMENTS_ID = "86ertcmf5" # Replace if different from TEST_TASK_ID
TEST_TASK_WITH_SUBTASKS_ID = "86et65e20" # Replace with a Task ID that has subtasks
TEST_USERNAME = "miko@dorxata.com" # Replace with your ClickUp username
TEST_TEAM_ID = "3723297" # Replace with your Team/Workspace ID
TEST_SPACE_ID = "43795741" # Replace with a Space ID within the team
TEST_FOLDER_ID = "90184491751" # Replace with a Folder ID within the space

# --- Test Functions ---

# Test for get_clickup_tasks
def test_get_clickup_tasks_live():
    """Test get_clickup_tasks retrieves tasks from the live API."""
    if not TEST_LIST_ID or TEST_LIST_ID == "YOUR_REAL_LIST_ID":
        pytest.skip("TEST_LIST_ID not set.")
        
    rate_limit_delay()
    tasks = clickup_tools.get_clickup_tasks(list_id=TEST_LIST_ID, days=30) # Look back 30 days
    
    assert isinstance(tasks, list)
    # If you expect tasks, you can add more checks
    if tasks:
        assert isinstance(tasks[0], dict)
        assert "id" in tasks[0]
        assert "name" in tasks[0]
    # Note: This test might return an empty list if no tasks were updated recently.

# Test for get_clickup_task_details
def test_get_clickup_task_details_live():
    """Test get_clickup_task_details retrieves details for a specific task."""
    if not TEST_TASK_ID or TEST_TASK_ID == "YOUR_REAL_TASK_ID":
        pytest.skip("TEST_TASK_ID not set.")

    rate_limit_delay()
    details = clickup_tools.get_clickup_task_details(task_id=TEST_TASK_ID)
    
    assert isinstance(details, dict)
    assert details.get("id") == TEST_TASK_ID
    assert "name" in details
    assert "status" in details
    assert "assignees" in details # Even if empty, the key should exist

# Test for get_clickup_comments
def test_get_clickup_comments_live():
    """Test get_clickup_comments retrieves comments for a specific task."""
    if not TEST_TASK_WITH_COMMENTS_ID or TEST_TASK_WITH_COMMENTS_ID == "YOUR_TASK_ID_WITH_COMMENTS":
        pytest.skip("TEST_TASK_WITH_COMMENTS_ID not set.")

    rate_limit_delay()
    comments = clickup_tools.get_clickup_comments(task_id=TEST_TASK_WITH_COMMENTS_ID)
    
    assert isinstance(comments, list)
    # If you expect comments on the test task, check their structure
    if comments:
        assert isinstance(comments[0], dict)
        assert "id" in comments[0]
        assert "comment_text" in comments[0]
        assert "user" in comments[0]

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
    if not TEST_TASK_WITH_SUBTASKS_ID or TEST_TASK_WITH_SUBTASKS_ID == "YOUR_PARENT_TASK_ID":
         pytest.skip("TEST_TASK_WITH_SUBTASKS_ID not set.")

    rate_limit_delay()
    subtasks = clickup_tools.get_clickup_subtasks(task_id=TEST_TASK_WITH_SUBTASKS_ID)
    
    assert isinstance(subtasks, list)
    # Check structure if subtasks are expected
    if subtasks:
         assert isinstance(subtasks[0], dict)
         assert "id" in subtasks[0]
         assert "name" in subtasks[0]
         assert subtasks[0].get("parent") == TEST_TASK_WITH_SUBTASKS_ID

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
