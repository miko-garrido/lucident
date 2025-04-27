from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For multi-model support
from google.genai import types # For creating message Content/Parts
from dotenv import load_dotenv  
from config import Config
from harpy_agent.tools.slack_tools.slack_tools import *
import os
import logging
from typing import Dict, Any, Optional
from harpy_agent.tools.basic_tools import (
    get_current_time,
    calculate,
    calculate_date,
    calculate_many
)

load_dotenv()

MODEL_NAME = Config.MODEL_NAME
APP_NAME = Config.APP_NAME
USER_ID = Config.USER_ID
SESSION_ID = Config.SESSION_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the root agent
slack_agent = Agent(
    name="slack_agent",
    model=LiteLlm(model=MODEL_NAME),
    description="Agent to process Slack messages using GPT-4 and MCP server.",
    instruction="I can process Slack messages and respond using GPT-4.",
    tools=[
        get_current_time,
        calculate,
        calculate_date,
        calculate_many
    ]
)

# Export the agent instance
__all__ = ['slack_agent'] 