from google.adk.agents import Agent
# from google.adk.models.lite_llm import LiteLlm # Original ADK import
from ..adk_patch.lite_llm_patched import LiteLlm # Using patched ADK LiteLlm for parallel tool calls fix
from google.genai import types # For creating message Content/Parts
from dotenv import load_dotenv  
from lucident_agent.config import Config
from lucident_agent.tools.slack_tools.slack_tools import *
import os
import logging
from typing import Dict, Any, Optional
from lucident_agent.tools.basic_tools import (
    get_current_time,
    calculate,
    calculate_date,
    convert_ms_to_hhmmss
)

load_dotenv()

OPENAI_MODEL = Config.OPENAI_MODEL
GEMINI_MODEL = Config.GEMINI_MODEL
APP_NAME = Config.APP_NAME
USER_ID = Config.USER_ID
SESSION_ID = Config.SESSION_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the root agent
slack_agent = Agent(
    name="slack_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    #model=GEMINI_MODEL,
    description="Agent to process Slack messages using GPT-4 and MCP server.",
    instruction="I can process Slack messages and respond using GPT-4.",
    tools=[
        get_current_time,
        calculate,
        calculate_date,
        convert_ms_to_hhmmss
    ]
)

# Export the agent instance
__all__ = ['slack_agent'] 