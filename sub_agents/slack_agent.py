from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For multi-model support
from google.genai import types # For creating message Content/Parts
from dotenv import load_dotenv  
from config import Config
from tools.slack_tools import *

load_dotenv()

MODEL_NAME = Config.MODEL_NAME
APP_NAME = Config.APP_NAME
USER_ID = Config.USER_ID
SESSION_ID = Config.SESSION_ID

slack_agent = Agent(
        # Can use the same or a different model
        model=LiteLlm(model=MODEL_NAME), # Sticking with GPT for this example
        name="slack_agent",
        instruction="You are the Slack Agent. You find messages in Slack."
                    "Do not perform any other actions.",
        description="Finds messages in Slack.", # Crucial for delegation
        tools=[get_channel_messages],
    )