import os
from google.adk.agents import Agent
# from google.adk.models.lite_llm import LiteLlm # Original ADK import
from .adk_patch.lite_llm_patched import LiteLlm # Using patched ADK LiteLlm for parallel tool calls fix
from google.adk.tools.tool_context import ToolContext
from google.genai import types # For creating message Content/Parts
from dotenv import load_dotenv  
from lucident_agent.config import Config
from .sub_agents.gmail_agent import gmail_agent
from .sub_agents.slack_agent import slack_agent
from .sub_agents.clickup_agent import clickup_agent
from .sub_agents.calendar_agent import calendar_agent
from .sub_agents.figma_agent import figma_agent
from .tools.basic_tools import (
    get_current_time,
    calculate,
    calculate_date,
    convert_ms_to_hhmmss,
    convert_datetime_to_unix
)

OPENAI_MODEL = Config.OPENAI_MODEL
GEMINI_MODEL = Config.GEMINI_MODEL
TIMEZONE = Config.TIMEZONE
current_time = get_current_time(TIMEZONE)

root_agent = Agent(
    name="lucident_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    # model=GEMINI_MODEL,
    description=(
        f"""
        Lucident is an AI-powered project management assistant that provides a unified interface 
        for managing projects across ClickUp, Gmail, Slack, and Google Calendar, intelligently understanding 
        and responding to user queries about project status, tasks, and communications.
        """
    ),
    instruction=("""
        You are Lucident, an AI project management assistant.
        You provide a unified interface for managing projects across ClickUp, Gmail, Slack, and Google Calendar.
        When a user asks a question related to project status, tasks, timelines, or communications:
        1. Understand the user's query and determine which platform(s) (ClickUp, Gmail, Slack, Google Calendar) are relevant.
        2. Route the query to the appropriate sub-agent (`clickup_agent`, `gmail_agent`, `slack_agent`, `calendar_agent`) to gather information. 
        3. Use multiple agents to gather information from different platforms.
        4. Synthesize the information gathered from the sub-agents into a unified response.
        Example Query: "What are my overdue tasks in ClickUp and any related emails in Gmail?"
        Example Response: "You have 2 overdue tasks in ClickUp: [Task 1 Name], [Task 2 Name]. In Gmail, I found 3 emails possibly related to these tasks: [Email Subject 1], [Email Subject 2], [Email Subject 3]."
        """
        ),
    global_instruction=(
        f"""
        NEVER DO ANY MATH EVER without using a calculation tool.
        ALWAYS use the calculate, calculate_date, convert_ms_to_hhmmss, convert_datetime_to_unix tools for any math or date calculations.
        The date today is {current_time}.
        When retrieving paginated data from an API or tool, ensure you request and process all available pages of results, not just the first page.
        For each page, use the provided pagination parameters (such as page, cursor, or next_page_token), and continue fetching until there are no more results.
        Combine, aggregate, or summarize the data across all pages before responding to the user.
        If an answer is based on only a partial set (such as the first page), always inform the user that more data may be available and offer to continue.
        """
    ),
    sub_agents=[gmail_agent, slack_agent, clickup_agent, calendar_agent, figma_agent],
    tools=[get_current_time, calculate, calculate_date, convert_ms_to_hhmmss, convert_datetime_to_unix]
)