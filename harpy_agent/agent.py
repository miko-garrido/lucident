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
from .sub_agents.basic_agent import basic_agent

AGENT_MODEL = Config.MODEL_NAME
APP_NAME = Config.APP_NAME
USER_ID = Config.USER_ID
SESSION_ID = Config.SESSION_ID

load_dotenv()

root_agent = Agent(
    name="harpy_agent",
    model="gemini-2.0-flash-exp",
    description=(
        "Harpy is an AI-powered project management assistant that provides a unified interface "
        "for managing projects across ClickUp, Gmail, and Slack, intelligently understanding "
        "and responding to user queries about project status, tasks, and communications."
    ),
    instruction=(
        "I can help with your project management needs by providing information and insights "
        "across ClickUp, Gmail, and Slack. Ask me about project status, tasks, timelines, "
        "or communications, and I'll provide unified responses drawing from all connected platforms."
    ),
    sub_agents=[gmail_agent, slack_agent, clickup_agent, basic_agent],
)