# import os
# import asyncio
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For multi-model support
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from google.genai import types # For creating message Content/Parts
from dotenv import load_dotenv  
from config import Config
from .sub_agents.gmail_agent import gmail_agent
from .sub_agents.slack_agent import slack_agent
from .sub_agents.clickup_agent import clickup_agent
from datetime import datetime
from harpy_agent.tools.basic_tools import (
    get_current_time,
    calculate,
    calculate_date
)
from google.adk.sessions import InMemorySessionService

AGENT_MODEL = Config.MODEL_NAME
APP_NAME = Config.APP_NAME
USER_ID = Config.USER_ID
SESSION_ID = Config.SESSION_ID
TIMEZONE = Config.TIMEZONE

session_service = InMemorySessionService()
initial_state = {"current_time": get_current_time(TIMEZONE)}
session = session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID,
    state=initial_state
)

load_dotenv()

# Create root agent with sub-agents
root_agent = Agent(
    name="harpy_agent",
    model=LiteLlm(model=AGENT_MODEL),
    description=(
        "Harpy is an AI-powered project management assistant that provides a unified interface "
        "for managing projects across ClickUp, Gmail, and Slack, intelligently understanding "
        "and responding to user queries about project status, tasks, and communications."
    ),
    instruction=("""You are Harpy, an AI project management assistant.
You provide a unified interface for managing projects across ClickUp, Gmail, and Slack.
NEVER assume the current time. If the user mentions anything time or date related, alway use the get_current_time tool before passing information to the sub-agents.
ALWAYS use calculate and calculate_date tools for any mathematical calculations.
When you need to use all sub-agents, use them only sequentially and one at a time to build context.
When a user asks a question related to project status, tasks, timelines, or communications:
1. Understand the user's query and determine which platform(s) (ClickUp, Gmail, Slack) are relevant.
2. Route the query to the appropriate sub-agent (`clickup_agent`, `gmail_agent`, `slack_agent`) to gather information. 
3. Use multiple agents to gather information from different platforms.
4. Synthesize the information gathered from the sub-agents into a unified response.
5. Respond clearly to the user, providing the requested information or insights.
Example Query: "What are my overdue tasks in ClickUp and any related emails in Gmail?"
Example Response: "You have 2 overdue tasks in ClickUp: [Task 1 Name], [Task 2 Name]. In Gmail, I found 3 emails possibly related to these tasks: [Email Subject 1], [Email Subject 2], [Email Subject 3]."
"""),
    sub_agents=[gmail_agent, slack_agent, clickup_agent],
    tools=[get_current_time, calculate, calculate_date]
)

# Export root_agent
__all__ = ['root_agent']