# import os
# import asyncio
# from google.adk.agents import Agent
# from google.adk.models.lite_llm import LiteLlm # For multi-model support
# from google.adk.sessions import InMemorySessionService
# from google.adk.runners import Runner
# from google.adk.tools.tool_context import ToolContext
# from google.genai import types # For creating message Content/Parts
from dotenv import load_dotenv  
from config import Config
from sub_agents.gmail_agent import gmail_agent
from sub_agents.slack_agent import slack_agent
from sub_agents.clickup_agent import clickup_agent

AGENT_MODEL = Config.MODEL_NAME
APP_NAME = Config.APP_NAME
USER_ID = Config.USER_ID
SESSION_ID = Config.SESSION_ID

import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent

load_dotenv()


root_agent = Agent(
    name="harpy_agent",
    model="gemini-2.0-flash-exp",
    description=(
        "Agent to answer questions about the time and weather in a city."
    ),
    instruction=(
        "I can answer your questions about the time and weather in a city."
    ),
    tools=[gmail_agent, slack_agent, clickup_agent],
)