import pytest
from unittest.mock import patch, MagicMock
import os
import sys
from dotenv import load_dotenv
import time
from datetime import datetime, timezone, timedelta

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from harpy_agent.tools import clickup_tools

load_dotenv()

# Check if the API key is actually loaded
api_key = os.getenv("CLICKUP_API_KEY")
if not api_key:
    pytest.skip("CLICKUP_API_KEY not found in environment variables. Skipping integration tests.", allow_module_level=True)

# --- Marker for integration tests ---
pytestmark = pytest.mark.integration

# --- Helper function to introduce delay ---
def rate_limit_delay():
    time.sleep(1)  # Adjust delay as needed based on ClickUp rate limits

# --- Placeholder IDs - REPLACE THESE WITH YOUR ACTUAL IDs ---
TEST_LIST_ID = "901805343302"
TEST_TASK_ID = "86ertcmf5"
TEST_TASK_WITH_COMMENTS_ID = "86ertcmf5"
TEST_PARENT_TASK_ID = "86et65e20"
TEST_COMMENT_ID = "90180108845811"
TEST_USERNAME = "josh@dorxata.com"
TEST_USER_ID = 3833265
# TEST_TEAM_ID = "3723297"
TEST_SPACE_ID = "43795741"
TEST_FOLDER_ID = "90184491751"
TEST_VIEW_ID = "3hm11-56478"
TEST_CHAT_VIEW_ID = "3hm11-3260"
TEST_DOC_ID = "3hm11-2595"
TEST_PAGE_ID = "3hm11-9105"
TEST_GOAL_ID = "f2ff1f14-b2c8-42c6-a0d7-a5ce900ec03e"
TEST_GUEST_ID = 3455671
TEST_TIMER_ID = "4492931707339476846"
TEST_CHANNEL_ID = "3hm11-57378"
TEST_MESSAGE_ID = "80180002933247"
TEST_FOLDERLESS_LIST_ID = "901805379671"
TEST_TASK_IDS = ["86et1a9yj", "86erk6jef", "86erwfmbz", "invalid-id"]

# Helper function to check for API error responses
def is_api_error(response):
    return isinstance(response, dict) and "error_code" in response

def test_get_tasks_from_list_live():
    if not TEST_LIST_ID or TEST_LIST_ID == "YOUR_REAL_LIST_ID":
        pytest.skip("TEST_LIST_ID not set.")

    rate_limit_delay()
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    start_timestamp_ms = int(thirty_days_ago.timestamp() * 1000)

    result = clickup_tools.get_tasks_from_list(list_id=TEST_LIST_ID, date_updated_gt=start_timestamp_ms)

    if is_api_error(result):
        pytest.fail(f"API Error: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "tasks" in result
    tasks = result["tasks"]
    assert isinstance(tasks, list)

    if tasks:
        assert isinstance(tasks[0], dict)
        assert "id" in tasks[0]
        assert "name" in tasks[0]

def test_get_task_live():
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
    assert "assignees" in details

def test_get_task_comments_live():
    if not TEST_TASK_WITH_COMMENTS_ID or TEST_TASK_WITH_COMMENTS_ID == "YOUR_TASK_ID_WITH_COMMENTS":
        pytest.skip("TEST_TASK_WITH_COMMENTS_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_task_comments(task_id=TEST_TASK_WITH_COMMENTS_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting task comments: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert 'comments' in result
    comments = result['comments']
    assert isinstance(comments, list)

    if comments:
        assert isinstance(comments[0], dict)
        assert "id" in comments[0]
        assert "comment_text" in comments[0] or "comment" in comments[0]
        assert "user" in comments[0]

def test_get_chat_view_comments_live():
    if not TEST_CHAT_VIEW_ID or TEST_CHAT_VIEW_ID == "YOUR_REAL_VIEW_ID":
        pytest.skip("TEST_VIEW_ID not set for chat view comments test.")

    rate_limit_delay()
    result = clickup_tools.get_chat_view_comments(view_id=TEST_CHAT_VIEW_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting chat view comments: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert 'comments' in result
    comments = result['comments']
    assert isinstance(comments, list)

def test_get_list_comments_live():
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

def test_get_threaded_comments_live():
    if not TEST_COMMENT_ID or TEST_COMMENT_ID == "YOUR_REAL_COMMENT_ID_WITH_REPLIES":
        pytest.skip("TEST_COMMENT_ID not set for threaded comments test.")

    rate_limit_delay()
    result = clickup_tools.get_threaded_comments(comment_id=TEST_COMMENT_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting threaded comments: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert 'comments' in result
    replies = result['comments']
    assert isinstance(replies, list)

# Note: This test also uses the `clickup_tools.get_tasks` function,
# specifically testing the retrieval of subtasks using the `parent` parameter.
def test_get_subtasks_via_get_tasks_from_list_live():
    if not TEST_PARENT_TASK_ID or TEST_PARENT_TASK_ID == "YOUR_PARENT_TASK_ID":
        pytest.skip("TEST_PARENT_TASK_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_tasks_from_list(list_id=TEST_LIST_ID, parent=TEST_PARENT_TASK_ID)
    
    assert isinstance(result, dict)
    assert "tasks" in result
    subtasks = result["tasks"]
    assert isinstance(subtasks, list)

    if subtasks:
        assert isinstance(subtasks[0], dict)
        assert "id" in subtasks[0]
        assert "name" in subtasks[0]
        assert subtasks[0].get("parent") == TEST_PARENT_TASK_ID

def test_get_filtered_team_tasks_for_user_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    now = datetime.now(timezone.utc)
    ninety_days_ago = now - timedelta(days=90)
    start_timestamp_ms = int(ninety_days_ago.timestamp() * 1000)

    result = clickup_tools.get_filtered_team_tasks(
        # team_id=TEST_TEAM_ID,
        assignees=[str(TEST_USER_ID)],
        date_updated_gt=start_timestamp_ms
    )

    if is_api_error(result):
        pytest.fail(f"API Error getting filtered team tasks for user: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "tasks" in result
    user_tasks = result["tasks"]
    assert isinstance(user_tasks, list)

def test_get_time_entries_for_task_live():
    if not TEST_TASK_ID or TEST_TASK_ID == "YOUR_REAL_TASK_ID":
        pytest.skip("TEST_TASK_ID not set.")

    rate_limit_delay()
    # Using specific date range April 20-28, 2025
    start_timestamp_ms = 1745059200000
    end_timestamp_ms = 1745836799999

    result = clickup_tools.get_time_entries_for_task(
        task_id=TEST_TASK_ID,
        start_date=start_timestamp_ms,
        end_date=end_timestamp_ms
    )

    if is_api_error(result):
        pytest.fail(f"API Error getting time entries for task: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "data" in result
    assert "totals" in result

    entries = result["data"]
    totals = result["totals"]

    assert isinstance(entries, list)
    assert isinstance(totals, dict)
    assert "grand_total" in totals
    assert isinstance(totals["grand_total"], int)
    assert "user_totals" in totals
    assert isinstance(totals["user_totals"], dict)
    assert "task_totals" in totals
    assert isinstance(totals["task_totals"], dict)
    # Check task_totals specifically contains the current task ID
    assert TEST_TASK_ID in totals["task_totals"]
    assert isinstance(totals["task_totals"][TEST_TASK_ID], int)

    # Check structure of entries if list is not empty
    if entries:
        entry = entries[0]
        assert isinstance(entry, dict)
        assert "intervals" in entry
        assert "time" in entry
        assert "user" in entry
        assert isinstance(entry["user"], dict)
        assert "id" in entry["user"]
        # Verify user totals contain user IDs from entries
        if "id" in entry["user"]:
            assert entry["user"]["id"] in totals["user_totals"]

def test_get_time_entries_for_users_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    # Using specific date range April 20-28, 2025
    start_timestamp_ms = 1745059200000
    end_timestamp_ms = 1745836799999

    result = clickup_tools.get_time_entries_for_users(
        user_ids=[str(TEST_USER_ID)],
        # team_id=TEST_TEAM_ID,
        start_date=start_timestamp_ms,
        end_date=end_timestamp_ms
    )

    if is_api_error(result):
        pytest.fail(f"API Error getting time entries: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "data" in result
    assert "totals" in result

    entries = result["data"]
    totals = result["totals"]

    assert isinstance(entries, list)
    assert isinstance(totals, dict)
    assert "grand_total" in totals
    assert isinstance(totals["grand_total"], int)
    assert "user_totals" in totals
    assert isinstance(totals["user_totals"], dict)
    assert "task_totals" in totals
    assert isinstance(totals["task_totals"], dict)

    # Verify totals if entries exist
    if entries:
        first_entry = entries[0]
        assert isinstance(first_entry, dict)
        # Check user_totals contain the requested user ID if they logged time
        if totals["user_totals"]:
            assert str(TEST_USER_ID) in totals["user_totals"]

        # Check structure of entries
        assert "id" in first_entry
        assert "duration" in first_entry
        assert "user" in first_entry
        assert "task" in first_entry

def test_get_singular_time_entry_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")
    if not TEST_TIMER_ID or TEST_TIMER_ID == "YOUR_REAL_TIMER_ID":
        pytest.skip("TEST_TIMER_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_singular_time_entry(
        # team_id=TEST_TEAM_ID, 
        timer_id=TEST_TIMER_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting singular time entry: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "data" in result
    entry = result["data"]
    assert isinstance(entry, dict)
    assert entry.get("id") == TEST_TIMER_ID
    assert "user" in entry
    assert "task" in entry

def test_get_time_entry_history_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")
    if not TEST_TIMER_ID or TEST_TIMER_ID == "YOUR_REAL_TIMER_ID":
        pytest.skip("TEST_TIMER_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_time_entry_history(
        # team_id=TEST_TEAM_ID, 
        timer_id=TEST_TIMER_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting time entry history: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "data" in result
    assert isinstance(result["data"], list)

def test_get_running_time_entry_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_running_time_entry(
        # team_id=TEST_TEAM_ID
        )

    if is_api_error(result):
        pytest.fail(f"API Error getting running time entry: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "data" in result

def test_get_all_time_entry_tags_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_all_time_entry_tags(
        # team_id=TEST_TEAM_ID
        )

    if is_api_error(result):
        pytest.fail(f"API Error getting time entry tags: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "data" in result or "tags" in result
    tags = result.get("data", result.get("tags"))
    assert isinstance(tags, list)

def test_get_list_members_live():
    if not TEST_LIST_ID or TEST_LIST_ID == "YOUR_REAL_LIST_ID":
        pytest.skip("TEST_LIST_ID not set.")

    rate_limit_delay()
    members = clickup_tools.get_list_members(list_id=TEST_LIST_ID)

    if is_api_error(members):
        pytest.fail(f"API Error getting list members: {members['error_message']} (Code: {members['error_code']})")

    assert isinstance(members, list)
    if members:
        assert isinstance(members[0], dict)
        assert "id" in members[0]
        assert "username" in members[0]
        assert "email" in members[0]

def test_get_task_members_live():
    if not TEST_TASK_ID or TEST_TASK_ID == "YOUR_REAL_TASK_ID":
        pytest.skip("TEST_TASK_ID not set.")

    rate_limit_delay()
    members = clickup_tools.get_task_members(task_id=TEST_TASK_ID)

    if is_api_error(members):
        pytest.fail(f"API Error getting task members: {members['error_message']} (Code: {members['error_code']})")

    assert isinstance(members, list)
    if members:
        assert isinstance(members[0], dict)
        assert "id" in members[0]
        assert "username" in members[0]

def test_get_user_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_user(
        # team_id=TEST_TEAM_ID, 
        user_id=TEST_USER_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting user: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "member" in result
    assert "user" in result["member"]
    user = result["member"]["user"]

    assert isinstance(user, dict)
    assert user.get("id") == TEST_USER_ID
    assert "username" in user
    assert "email" in user

def test_get_spaces_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_spaces(
        # team_id=TEST_TEAM_ID
        )

    if is_api_error(result):
        pytest.fail(f"API Error getting spaces: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "spaces" in result
    spaces = result["spaces"]
    assert isinstance(spaces, list)
    assert len(spaces) > 0
    assert isinstance(spaces[0], dict)
    assert "id" in spaces[0]
    assert "name" in spaces[0]

def test_get_space_live():
    if not TEST_SPACE_ID or TEST_SPACE_ID == "YOUR_REAL_SPACE_ID":
        pytest.skip("TEST_SPACE_ID not set.")

    rate_limit_delay()
    space = clickup_tools.get_space(space_id=TEST_SPACE_ID)

    if is_api_error(space):
        pytest.fail(f"API Error getting space: {space['error_message']} (Code: {space['error_code']})")

    assert isinstance(space, dict)
    assert space.get("id") == TEST_SPACE_ID
    assert "name" in space

def test_get_folders_live():
    if not TEST_SPACE_ID or TEST_SPACE_ID == "YOUR_REAL_SPACE_ID":
        pytest.skip("TEST_SPACE_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_folders(space_id=TEST_SPACE_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting folders: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "folders" in result
    folders = result["folders"]
    assert isinstance(folders, list)
    if folders:
        assert isinstance(folders[0], dict)
        assert "id" in folders[0]
        assert "name" in folders[0]
        assert "space" in folders[0]

def test_get_folder_live():
    if not TEST_FOLDER_ID or TEST_FOLDER_ID == "YOUR_REAL_FOLDER_ID":
        pytest.skip("TEST_FOLDER_ID not set.")

    rate_limit_delay()
    folder = clickup_tools.get_folder(folder_id=TEST_FOLDER_ID)

    if is_api_error(folder):
        pytest.fail(f"API Error getting folder: {folder['error_message']} (Code: {folder['error_code']})")

    assert isinstance(folder, dict)
    assert folder.get("id") == TEST_FOLDER_ID
    assert "name" in folder
    assert "space" in folder

def test_get_lists_live():
    if not TEST_FOLDER_ID or TEST_FOLDER_ID == "YOUR_REAL_FOLDER_ID":
        pytest.skip("TEST_FOLDER_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_lists(folder_id=TEST_FOLDER_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting lists: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "lists" in result
    lists = result["lists"]
    assert isinstance(lists, list)
    if lists:
        assert isinstance(lists[0], dict)
        assert "id" in lists[0]
        assert "name" in lists[0]
        assert lists[0].get("folder", {}).get("id") == TEST_FOLDER_ID

def test_get_folderless_lists_live():
    if not TEST_SPACE_ID or TEST_SPACE_ID == "YOUR_REAL_SPACE_ID":
        pytest.skip("TEST_SPACE_ID not set.")
    # Ensure TEST_FOLDERLESS_LIST_ID is set for this test
    if not TEST_FOLDERLESS_LIST_ID or TEST_FOLDERLESS_LIST_ID == "YOUR_FOLDERLESS_LIST_ID":
        pytest.skip("TEST_FOLDERLESS_LIST_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_folderless_lists(space_id=TEST_SPACE_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting folderless lists: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "lists" in result
    lists = result["lists"]
    assert isinstance(lists, list)

    found_list = None
    for lst in lists:
        if lst.get("id") == TEST_FOLDERLESS_LIST_ID:
            found_list = lst
            break

    assert found_list is not None, f"Folderless list {TEST_FOLDERLESS_LIST_ID} not found in space {TEST_SPACE_ID}"
    assert isinstance(found_list, dict)
    assert "id" in found_list
    assert "name" in found_list
    assert found_list.get("space", {}).get("id") == TEST_SPACE_ID
    # Adjusted Assertion: Allow folder to be None OR a dict, acknowledging API might return folder info
    # even if UI considers it folderless, especially for specific default lists.
    folder_data = found_list.get("folder")
    assert folder_data is None or isinstance(folder_data, dict), \
        f"Expected folder to be None or a dict, but got {type(folder_data)} for list {TEST_FOLDERLESS_LIST_ID}"

def test_get_list_live():
    if not TEST_LIST_ID or TEST_LIST_ID == "YOUR_REAL_LIST_ID":
        pytest.skip("TEST_LIST_ID not set.")

    rate_limit_delay()
    list_details = clickup_tools.get_list(list_id=TEST_LIST_ID)

    if is_api_error(list_details):
        pytest.fail(f"API Error getting list: {list_details['error_message']} (Code: {list_details['error_code']})")

    assert isinstance(list_details, dict)
    assert list_details.get("id") == TEST_LIST_ID
    assert "name" in list_details
    assert "space" in list_details
    assert "folder" in list_details

def test_get_shared_hierarchy_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_shared_hierarchy(
        # team_id=TEST_TEAM_ID
        )

    if is_api_error(result):
        pytest.fail(f"API Error getting shared hierarchy: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "shared" in result
    shared = result["shared"]
    assert isinstance(shared, dict)

def test_get_team_views_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_team_views(
        # team_id=TEST_TEAM_ID
        )

    if is_api_error(result):
        pytest.fail(f"API Error getting team views: {result['error_message']} (Code: {result['error_code']})")

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

def test_get_folder_views_live():
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

def test_get_list_views_live():
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

def test_get_view_live():
    if not TEST_VIEW_ID or TEST_VIEW_ID == "YOUR_REAL_VIEW_ID":
        pytest.skip("TEST_VIEW_ID not set.")

    rate_limit_delay()
    view = clickup_tools.get_view(view_id=TEST_VIEW_ID)

    if is_api_error(view):
        pytest.fail(f"API Error getting view: {view['error_message']} (Code: {view['error_code']})")

    assert isinstance(view, dict)
    # Check nested structure
    view_data = view.get("view", {})
    assert isinstance(view_data, dict)
    assert view_data.get("id") == TEST_VIEW_ID
    assert "name" in view_data
    assert "type" in view_data

def test_get_view_tasks_live():
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

def test_get_guest_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_guest(
        # team_id=TEST_TEAM_ID, 
        guest_id=TEST_GUEST_ID)

    if is_api_error(result):
        if result.get("error_code") == 404:
            pytest.skip(f"Guest {TEST_GUEST_ID} not found or not accessible (404). Skipping.")
        pytest.fail(f"API Error getting guest: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "guest" in result
    guest = result["guest"]
    assert isinstance(guest, dict)
    assert "user" in guest
    assert guest["user"].get("id") == TEST_GUEST_ID
    assert "username" in guest["user"]

def test_get_goals_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_goals(
        # team_id=TEST_TEAM_ID
        )

    if is_api_error(result):
        pytest.fail(f"API Error getting goals: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "goals" in result
    goals = result["goals"]
    assert isinstance(goals, list)
    if goals:
        assert isinstance(goals[0], dict)
        assert "id" in goals[0]
        assert "name" in goals[0]

def test_get_goal_live():
    if not TEST_GOAL_ID or TEST_GOAL_ID == "YOUR_REAL_GOAL_ID":
        pytest.skip("TEST_GOAL_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_goal(goal_id=TEST_GOAL_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting goal: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "goal" in result
    goal = result["goal"]
    assert isinstance(goal, dict)
    assert goal.get("id") == TEST_GOAL_ID
    assert "name" in goal

def test_get_space_tags_live():
    if not TEST_SPACE_ID or TEST_SPACE_ID == "YOUR_REAL_SPACE_ID":
        pytest.skip("TEST_SPACE_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_space_tags(space_id=TEST_SPACE_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting space tags: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "tags" in result
    tags = result["tags"]
    assert isinstance(tags, list)
    if tags:
        assert isinstance(tags[0], dict)
        assert "name" in tags[0]
        assert "tag_fg" in tags[0]

def test_get_task_templates_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_task_templates(
        # team_id=TEST_TEAM_ID, 
        page=0)

    if is_api_error(result):
        pytest.fail(f"API Error getting task templates: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "templates" in result
    templates = result["templates"]
    assert isinstance(templates, list)
    if templates:
        assert isinstance(templates[0], dict)
        assert "id" in templates[0]
        assert "name" in templates[0]

def test_get_chat_channels_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_chat_channels(
        # team_id=TEST_TEAM_ID
        )

    if is_api_error(result):
        pytest.fail(f"API Error getting chat channels: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "data" in result
    channels = result["data"]
    assert isinstance(channels, list)
    if channels:
        assert isinstance(channels[0], dict)
        assert "id" in channels[0]
        assert "name" in channels[0]

def test_get_chat_channel_live():
    if not TEST_CHANNEL_ID or TEST_CHANNEL_ID == "YOUR_REAL_CHAT_CHANNEL_ID":
        pytest.skip("TEST_CHANNEL_ID not set.")
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_chat_channel(
        # team_id=TEST_TEAM_ID, 
        channel_id=TEST_CHANNEL_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting chat channel: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "data" in result
    channel_data = result["data"]
    assert isinstance(channel_data, dict)
    assert channel_data.get("id") == TEST_CHANNEL_ID
    assert "name" in channel_data

def test_get_chat_channel_followers_live():
    if not TEST_CHANNEL_ID or TEST_CHANNEL_ID == "YOUR_REAL_CHAT_CHANNEL_ID":
        pytest.skip("TEST_CHANNEL_ID not set.")
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_chat_channel_followers(
        # team_id=TEST_TEAM_ID, 
        channel_id=TEST_CHANNEL_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting channel followers: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "data" in result
    followers = result["data"]
    assert isinstance(followers, list)

def test_get_chat_channel_members_live():
    if not TEST_CHANNEL_ID or TEST_CHANNEL_ID == "YOUR_REAL_CHAT_CHANNEL_ID":
        pytest.skip("TEST_CHANNEL_ID not set.")
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_chat_channel_members(
        # team_id=TEST_TEAM_ID, 
        channel_id=TEST_CHANNEL_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting chat channel members: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "data" in result
    members = result["data"]
    assert isinstance(members, list)

def test_get_chat_messages_live():
    if not TEST_CHANNEL_ID or TEST_CHANNEL_ID == "YOUR_REAL_CHAT_CHANNEL_ID":
        pytest.skip("TEST_CHANNEL_ID not set.")
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_chat_messages(
        # team_id=TEST_TEAM_ID, 
        channel_id=TEST_CHANNEL_ID, limit=10)

    if is_api_error(result):
        pytest.fail(f"API Error getting chat messages: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "data" in result
    messages = result["data"]
    assert isinstance(messages, list)
    if messages:
        assert isinstance(messages[0], dict)
        assert "id" in messages[0]
        assert "content" in messages[0]

def test_get_message_reactions_live():
    if not TEST_MESSAGE_ID or TEST_MESSAGE_ID == "YOUR_REAL_CHAT_MESSAGE_ID":
        pytest.skip("TEST_MESSAGE_ID not set.")
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_message_reactions(
        # team_id=TEST_TEAM_ID, 
        message_id=TEST_MESSAGE_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting message reactions: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "data" in result
    reactions = result["data"]
    assert isinstance(reactions, list)

def test_get_message_replies_live():
    if not TEST_MESSAGE_ID or TEST_MESSAGE_ID == "YOUR_REAL_CHAT_MESSAGE_ID":
        pytest.skip("TEST_MESSAGE_ID not set.")
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_message_replies(
        # team_id=TEST_TEAM_ID, 
        message_id=TEST_MESSAGE_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting message replies: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "data" in result
    replies = result["data"]
    assert isinstance(replies, list)

def test_get_tagged_users_for_message_live():
    if not TEST_MESSAGE_ID or TEST_MESSAGE_ID == "YOUR_REAL_CHAT_MESSAGE_ID":
        pytest.skip("TEST_MESSAGE_ID with tagged users not set.")
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_tagged_users_for_message(
        # team_id=TEST_TEAM_ID, 
        message_id=TEST_MESSAGE_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting tagged users: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "data" in result
    users = result["data"]
    assert isinstance(users, list)

def test_get_custom_task_types_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_custom_task_types(
        # team_id=TEST_TEAM_ID
        )

    if is_api_error(result):
        pytest.fail(f"API Error getting custom task types: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "custom_items" in result  # Corrected key from 'data'
    items = result["custom_items"]   # Corrected key from 'data'
    assert isinstance(items, list)
    if items:
        assert isinstance(items[0], dict)
        assert "id" in items[0]
        assert "name" in items[0]

def test_get_list_custom_fields_live():
    if not TEST_LIST_ID or TEST_LIST_ID == "YOUR_REAL_LIST_ID":
        pytest.skip("TEST_LIST_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_list_custom_fields(list_id=TEST_LIST_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting list custom fields: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "fields" in result
    fields = result["fields"]
    assert isinstance(fields, list)
    if fields:
        assert isinstance(fields[0], dict)
        assert "id" in fields[0]
        assert "name" in fields[0]
        assert "type" in fields[0]

def test_get_folder_available_custom_fields_live():
    if not TEST_FOLDER_ID or TEST_FOLDER_ID == "YOUR_REAL_FOLDER_ID":
        pytest.skip("TEST_FOLDER_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_folder_available_custom_fields(folder_id=TEST_FOLDER_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting folder custom fields: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "fields" in result
    fields = result["fields"]
    assert isinstance(fields, list)
    if fields:
        assert isinstance(fields[0], dict)
        assert "id" in fields[0]
        assert "name" in fields[0]

def test_get_space_available_custom_fields_live():
    if not TEST_SPACE_ID or TEST_SPACE_ID == "YOUR_REAL_SPACE_ID":
        pytest.skip("TEST_SPACE_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_space_available_custom_fields(space_id=TEST_SPACE_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting space custom fields: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "fields" in result
    fields = result["fields"]
    assert isinstance(fields, list)
    if fields:
        assert isinstance(fields[0], dict)
        assert "id" in fields[0]
        assert "name" in fields[0]

def test_get_team_available_custom_fields_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_team_available_custom_fields(
        # team_id=TEST_TEAM_ID
        )

    if is_api_error(result):
        pytest.fail(f"API Error getting team custom fields: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "fields" in result
    fields = result["fields"]
    assert isinstance(fields, list)
    if fields:
        assert isinstance(fields[0], dict)
        assert "id" in fields[0]
        assert "name" in fields[0]

def test_search_docs_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    query = "test"
    result = clickup_tools.search_docs(
        # team_id=TEST_TEAM_ID, 
        query=query)

    if is_api_error(result):
        pytest.fail(f"API Error searching docs: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "docs" in result or "data" in result
    docs = result.get("docs", result.get("data", []))
    assert isinstance(docs, list)
    if docs:
        assert isinstance(docs[0], dict)
        assert "id" in docs[0]
        assert "title" in docs[0] or "name" in docs[0]

def test_get_doc_live():
    if not TEST_DOC_ID or TEST_DOC_ID == "YOUR_REAL_DOC_ID":
        pytest.skip("TEST_DOC_ID not set.")
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set (required for V3 get_doc).")

    rate_limit_delay()
    doc = clickup_tools.get_doc(doc_id=TEST_DOC_ID)
    # doc = clickup_tools.get_doc(workspace_id=TEST_TEAM_ID, doc_id=TEST_DOC_ID)

    if is_api_error(doc):
        pytest.fail(f"API Error getting doc: {doc['error_message']} (Code: {doc['error_code']})")

    assert isinstance(doc, dict)
    assert doc.get("id") == TEST_DOC_ID
    assert "title" in doc or "name" in doc

def test_get_doc_page_listing_live():
    if not TEST_DOC_ID or TEST_DOC_ID == "YOUR_REAL_DOC_ID":
        pytest.skip("TEST_DOC_ID not set.")
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set (assuming required for V3).")

    rate_limit_delay()
    result = clickup_tools.get_doc_page_listing(doc_id=TEST_DOC_ID)
    # result = clickup_tools.get_doc_page_listing(workspace_id=TEST_TEAM_ID, doc_id=TEST_DOC_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting doc page listing: {result['error_message']} (Code: {result['error_code']})")

    # Check if the result is a list (as observed in failure)
    assert isinstance(result, list)
    pages = result # Assign the list directly

    # Keep the rest of the assertions on the list content
    assert isinstance(pages, list)
    if pages:
        assert isinstance(pages[0], dict)
        assert "id" in pages[0]
        assert "title" in pages[0] or "name" in pages[0]

def test_get_doc_pages_live():
    if not TEST_DOC_ID or TEST_DOC_ID == "YOUR_REAL_DOC_ID":
        pytest.skip("TEST_DOC_ID not set.")
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set (assuming required for V3).")

    rate_limit_delay()
    result = clickup_tools.get_doc_pages(doc_id=TEST_DOC_ID)
    # result = clickup_tools.get_doc_pages(workspace_id=TEST_TEAM_ID, doc_id=TEST_DOC_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting doc pages: {result['error_message']} (Code: {result['error_code']})")

    # Check if the result is a list (as observed in failure)
    assert isinstance(result, list)
    pages = result # Assign the list directly

    # Keep the rest of the assertions on the list content
    assert isinstance(pages, list)
    if pages:
        assert isinstance(pages[0], dict)
        assert "id" in pages[0]
        assert "title" in pages[0] or "name" in pages[0]

def test_get_page_live():
    if not TEST_PAGE_ID or TEST_PAGE_ID == "YOUR_REAL_PAGE_ID":
        pytest.skip("TEST_PAGE_ID not set.")
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set (assuming required for V3).")
    if not TEST_DOC_ID or TEST_DOC_ID == "YOUR_REAL_DOC_ID":
        pytest.skip("TEST_DOC_ID not set.")

    rate_limit_delay()
    page = clickup_tools.get_page(doc_id=TEST_DOC_ID, page_id=TEST_PAGE_ID)
    # page = clickup_tools.get_page(workspace_id=TEST_TEAM_ID, doc_id=TEST_DOC_ID, page_id=TEST_PAGE_ID)

    if is_api_error(page):
        pytest.fail(f"API Error getting page: {page['error_message']} (Code: {page['error_code']})")

    assert isinstance(page, dict)
    assert page.get("id") == TEST_PAGE_ID
    assert "title" in page or "name" in page

def test_get_task_time_in_status_live():
    if not TEST_TASK_ID or TEST_TASK_ID == "YOUR_REAL_TASK_ID":
        pytest.skip("TEST_TASK_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_task_time_in_status(task_id=TEST_TASK_ID)

    if is_api_error(result):
        pytest.fail(f"API Error getting task time in status: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "current_status" in result
    assert "status_history" in result
    assert isinstance(result["status_history"], list)

def test_get_bulk_tasks_time_in_status_live():
    if not TEST_TASK_ID or TEST_TASK_ID == "YOUR_REAL_TASK_ID":
        pytest.skip("TEST_TASK_ID not set.")

    task_ids_to_test = [TEST_TASK_ID, TEST_TASK_ID]

    rate_limit_delay()
    result = clickup_tools.get_bulk_tasks_time_in_status(task_ids=task_ids_to_test)

    if is_api_error(result):
        pytest.fail(f"API Error getting bulk task time in status: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    if result:
        assert TEST_TASK_ID in result
        task_status_data = result[TEST_TASK_ID]
        assert isinstance(task_status_data, dict)
        assert "current_status" in task_status_data
        assert "status_history" in task_status_data

def test_get_workspace_structure_live():
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.")

    rate_limit_delay()
    result = clickup_tools.get_workspace_structure(
        # team_id=TEST_TEAM_ID
        )

    if is_api_error(result):
        pytest.fail(f"API Error getting workspace structure: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "data" in result
    structure = result["data"]
    assert isinstance(structure, dict)
    assert "spaces" in structure
    spaces = structure["spaces"]
    assert isinstance(spaces, list)

    if spaces:
        first_space = spaces[0]
        assert isinstance(first_space, dict)
        assert "id" in first_space
        assert "name" in first_space
        assert "folderless_lists" in first_space
        assert isinstance(first_space["folderless_lists"], list)
        assert "folders" in first_space
        assert isinstance(first_space["folders"], list)

        if first_space["folders"]:
            first_folder = first_space["folders"][0]
            assert isinstance(first_folder, dict)
            assert "id" in first_folder
            assert "name" in first_folder
            assert "lists" in first_folder
            assert isinstance(first_folder["lists"], list)
            if first_folder["lists"]:
                first_list = first_folder["lists"][0]
                assert isinstance(first_list, dict)
                assert "id" in first_list
                assert "name" in first_list

        if first_space["folderless_lists"]:
            first_folderless_list = first_space["folderless_lists"][0]
            assert isinstance(first_folderless_list, dict)
            assert "id" in first_folderless_list
            assert "name" in first_folderless_list

def test_get_time_entries_for_list_live():
    if not TEST_LIST_ID or TEST_LIST_ID == "YOUR_REAL_LIST_ID":
        pytest.skip("TEST_LIST_ID not set.")

    rate_limit_delay()
    # Using specific date range April 20-28, 2025
    start_timestamp_ms = 1745059200000
    end_timestamp_ms = 1745836799999

    result = clickup_tools.get_time_entries_for_list(
        list_id=TEST_LIST_ID,
        start_date=start_timestamp_ms,
        end_date=end_timestamp_ms
    )

    # Function now returns a dict {'data': [], 'totals': {}, 'errors': []}
    assert isinstance(result, dict)
    assert "data" in result
    assert "totals" in result
    assert "errors" in result

    entries = result["data"]
    totals = result["totals"]
    errors = result["errors"]

    assert isinstance(entries, list)
    assert isinstance(totals, dict)
    assert isinstance(errors, list)

    # Log errors if any, but don't necessarily fail
    if errors:
        print(f"Warnings/Errors encountered during get_time_entries_for_list: {errors}")

    # Check totals structure regardless of errors
    assert "grand_total" in totals
    assert isinstance(totals["grand_total"], int)
    assert "user_totals" in totals
    assert isinstance(totals["user_totals"], dict)
    assert "task_totals" in totals
    assert isinstance(totals["task_totals"], dict)

    # Check structure of entries if list is not empty
    if entries:
        entry = entries[0]
        assert isinstance(entry, dict)
        # Check that task_id was added
        assert "task_id" in entry
        assert isinstance(entry["task_id"], str)
        # Verify task_totals contain task IDs from entries
        assert entry["task_id"] in totals["task_totals"]

        # Legacy endpoint entries contain 'intervals', 'time', and 'user'
        assert "intervals" in entry
        assert "time" in entry
        assert "user" in entry
        assert isinstance(entry["user"], dict)
        assert "id" in entry["user"]
        # Verify user totals contain user IDs from entries
        if "id" in entry["user"]:
            assert entry["user"]["id"] in totals["user_totals"]

def test_get_many_tasks_live():
    if not TEST_TASK_IDS: # Check if the list itself is populated
        pytest.skip("TEST_TASK_IDS list is empty.")

    task_ids_to_test = TEST_TASK_IDS # Use the constant directly

    rate_limit_delay()
    result = clickup_tools.get_many_tasks(task_ids=task_ids_to_test)

    if is_api_error(result):
        pytest.fail(f"API Error getting many tasks: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "data" in result
    task_results = result["data"]
    assert isinstance(task_results, list)
    assert len(task_results) == len(task_ids_to_test)

    # Check that exactly one task retrieval resulted in an error
    # and all valid IDs were retrieved successfully.
    valid_task_ids = {tid for tid in task_ids_to_test if tid != "invalid-id"}
    error_results = [r for r in task_results if "error_code" in r]
    successful_results = [r for r in task_results if "error_code" not in r]
    retrieved_successful_ids = {r["id"] for r in successful_results}

    assert len(error_results) == 1, f"Expected exactly one error result, but got {len(error_results)}: {error_results}"
    assert valid_task_ids == retrieved_successful_ids, \
        f"Expected successful IDs {valid_task_ids}, but got {retrieved_successful_ids}"

def test_get_all_users_live():
    """Tests retrieving all users from the workspace."""
    # if not TEST_TEAM_ID or TEST_TEAM_ID == "YOUR_REAL_TEAM_ID":
    #     pytest.skip("TEST_TEAM_ID not set.") # Assuming default is okay for now

    rate_limit_delay()
    result = clickup_tools.get_all_users()

    if is_api_error(result):
        pytest.fail(f"API Error getting all users: {result['error_message']} (Code: {result['error_code']})")

    assert isinstance(result, dict)
    assert "team" in result
    team_data = result["team"]
    assert isinstance(team_data, dict)
    assert "members" in team_data
    members = team_data["members"]
    assert isinstance(members, list)

    if members:
        first_member = members[0]
        assert isinstance(first_member, dict)
        assert "user" in first_member
        user_data = first_member["user"]
        assert isinstance(user_data, dict)
        assert "id" in user_data
        assert "username" in user_data
        assert "email" in user_data