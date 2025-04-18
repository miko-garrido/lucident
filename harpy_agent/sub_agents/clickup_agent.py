from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For multi-model support
from google.genai import types # For creating message Content/Parts
from dotenv import load_dotenv  
from config import Config
from ..tools.clickup_tools import (
    get_clickup_tasks, get_clickup_task_details, get_clickup_comments,
    get_clickup_user_tasks, get_clickup_time_entries, 
    get_clickup_list_members, get_clickup_task_members, get_clickup_subtasks,
    get_clickup_teams, get_clickup_team_members,
    get_clickup_spaces, get_clickup_folders, get_clickup_lists,
    find_clickup_users
)

load_dotenv()

MODEL_NAME = Config.MODEL_NAME
APP_NAME = Config.APP_NAME
USER_ID = Config.USER_ID
SESSION_ID = Config.SESSION_ID

clickup_agent = Agent(
        # Can use the same or a different model
        model=LiteLlm(model=MODEL_NAME),
        name="clickup_agent",
        instruction=(
            "You are a specialized ClickUp assistant. Your primary function is to interact with the ClickUp API using the provided tools "
            "to manage and retrieve information about tasks, comments, time entries, users, and the ClickUp organizational structure (teams, spaces, folders, lists). "
            "Carefully analyze user requests to determine the appropriate tool and required parameters (like task IDs, list IDs, user names, etc.). "
            "Always return time tracked in hours and minutes, in the format '1h 30m'."
            "If necessary IDs are missing, use navigational tools sequentially to find them, or ask the user for clarification. "
            "Focus solely on ClickUp-related actions defined by your tools. Do not perform actions outside of ClickUp management."
        ),
        description=(
            "Manages and retrieves information from ClickUp, including tasks, comments, time entries, users, and organizational structure (teams, spaces, folders, lists). "
            "Can create, update, delete, and query various ClickUp entities."
        ),
        tools=[
            get_clickup_tasks, get_clickup_task_details, get_clickup_comments,
            get_clickup_user_tasks, get_clickup_time_entries, 
            get_clickup_list_members, get_clickup_task_members, get_clickup_subtasks,
            get_clickup_teams, get_clickup_team_members,
            get_clickup_spaces, get_clickup_folders, get_clickup_lists,
            find_clickup_users
        ],
    )