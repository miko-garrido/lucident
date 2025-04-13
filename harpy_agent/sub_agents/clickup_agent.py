from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For multi-model support
from google.genai import types # For creating message Content/Parts
from dotenv import load_dotenv  
from config import Config
from ..tools.clickup_tools import *

load_dotenv()

MODEL_NAME = Config.MODEL_NAME
APP_NAME = Config.APP_NAME
USER_ID = Config.USER_ID
SESSION_ID = Config.SESSION_ID

clickup_agent = Agent(
        # Can use the same or a different model
        model=LiteLlm(model=MODEL_NAME), # Sticking with GPT for this example
        name="clickup_agent",
        instruction="You are the ClickUp Agent. You find tasks in ClickUp."
                    "Do not perform any other actions.",
        description="Finds tasks in ClickUp.", # Crucial for delegation
        tools=[get_tasks],
    )