from google.adk.agents import Agent
# from google.adk.models.lite_llm import LiteLlm # Original ADK import
from adk_patch.lite_llm_patched import LiteLlm # Using patched ADK LiteLlm for parallel tool calls fix
from google.genai import types
from dotenv import load_dotenv  
from config import Config
from ..tools.clickup_tools import (
    get_task_comments, get_chat_view_comments, get_list_comments,
    get_threaded_comments, get_custom_task_types, get_list_custom_fields,
    get_folder_available_custom_fields, get_space_available_custom_fields,
    get_team_available_custom_fields, search_docs, get_doc, get_doc_page_listing,
    get_doc_pages, get_page, get_folders, get_folder, get_goals, get_goal,
    get_guest, get_lists, get_folderless_lists, get_list, get_task_members,
    get_list_members, get_shared_hierarchy, get_spaces, get_space,
    get_space_tags, get_tasks_from_list, get_task, get_filtered_team_tasks,
    get_task_time_in_status, get_bulk_tasks_time_in_status,
    get_task_templates, get_time_entries_for_users, get_singular_time_entry,
    get_time_entry_history, get_running_time_entry, get_all_time_entry_tags,
    get_user, get_team_views, get_space_views, get_folder_views,
    get_list_views, get_view, get_view_tasks, get_chat_channels,
    get_chat_channel, get_chat_channel_followers, get_chat_channel_members,
    get_chat_messages, get_message_reactions, get_message_replies,
    get_tagged_users_for_message,
    #custom tools
    get_many_tasks, get_time_entries_for_list, get_workspace_structure,
    get_all_users
)
from lucident_agent.tools.basic_tools import (
    get_current_time,
    calculate,
    calculate_date,
    convert_ms_to_hhmmss,
    convert_datetime_to_unix
)

load_dotenv()

all_users = get_all_users()
workspace_structure = get_workspace_structure()

OPENAI_MODEL = Config.OPENAI_MODEL
GEMINI_MODEL = Config.GEMINI_MODEL
APP_NAME = Config.APP_NAME
USER_ID = Config.USER_ID
SESSION_ID = Config.SESSION_ID
TEAM_ID = Config.CLICKUP_TEAM_ID

clickup_agent = Agent(
        model=LiteLlm(model=OPENAI_MODEL),
        # model=GEMINI_MODEL,
        name="clickup_agent",
        instruction=(
            f"""
            You are a specialized ClickUp assistant. Your primary function is to interact with the ClickUp API using the provided tools
            to manage and retrieve information about tasks, comments, time entries, users.
            If necessary IDs are missing, use navigational tools sequentially to find them, or ask the user for clarification.
            Carefully analyze user requests to determine the appropriate tool and required parameters (like task IDs, list IDs, user names, etc.).
            If the user does not provide the correct format for user names, tasks, lists, or other entities, use the appropriate tool to find the correct format.
            Always return time tracked in hours and minutes, in the format '1h 30m'.
            Focus solely on ClickUp-related actions defined by your tools. Do not perform actions outside of ClickUp management.
            When responding to any prompt asking about a space, ALWAYS search for both folderless lists directly under the space AND for all lists inside every folder within that space.
            For each list (regardless of whether it is folderless or within a folder), aggregate your results as appropriate for the request.
            The workspace ID or team ID is {TEAM_ID}.
            Below is the workspace structure:
            ```json
            {workspace_structure}
            ```
            Below is the list of all users in the workspace:
            ```json
            {all_users}
            ```
            """
        ),
        description=(
            """
            Manages and retrieves information from ClickUp, including tasks, comments, time entries,
            users, and organizational structure (teams, spaces, folders, lists).
            """
        ),
        tools=[
            get_task_comments, get_chat_view_comments, get_list_comments,
            get_threaded_comments, get_custom_task_types, get_list_custom_fields,
            get_folder_available_custom_fields, get_space_available_custom_fields,
            get_team_available_custom_fields, search_docs, get_doc, get_doc_page_listing,
            get_doc_pages, get_page, get_folders, get_folder, get_goals, get_goal,
            get_guest, get_lists, get_folderless_lists, get_list, get_task_members,
            get_list_members, get_shared_hierarchy, get_spaces, get_space,
            get_space_tags, get_tasks_from_list, get_task, get_filtered_team_tasks,
            get_task_time_in_status, get_bulk_tasks_time_in_status,
            get_task_templates, get_time_entries_for_users, get_singular_time_entry,
            get_time_entry_history, get_running_time_entry, get_all_time_entry_tags,
            get_user, get_team_views, get_space_views, get_folder_views,
            get_list_views, get_view, get_view_tasks, get_chat_channels,
            get_chat_channel, get_chat_channel_followers, get_chat_channel_members,
            get_chat_messages, get_message_reactions, get_message_replies,
            get_tagged_users_for_message,
            #custom clickup tools
            get_many_tasks, get_time_entries_for_list, get_workspace_structure,
            #basic tools
            get_current_time, calculate, calculate_date,
            convert_ms_to_hhmmss, convert_datetime_to_unix,
            get_all_users
        ],
    )