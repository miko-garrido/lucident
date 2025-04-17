#!/usr/bin/env python3
"""
Basic Utility Agent
"""

from config import Config
AGENT_MODEL = Config.MODEL_NAME

from google.adk.models.lite_llm import LiteLlm
from google.adk.agents import Agent
from harpy_agent.tools.basic_tools import (
    get_current_time,
    calculate,
    calculate_date
)

basic_agent = Agent(
    name="basic_agent",
    model=LiteLlm(model=AGENT_MODEL),
    description="Agent for basic utility tasks like calculations, and date/time operations.",
    instruction=(
        "You are a helpful assistant for basic utility tasks.\n\n"
        "Tool Usage Guide:\n"
        "- If the user asks for the current time, use the `get_current_time` tool. You can optionally provide an IANA timezone (e.g., 'America/New_York'). If no timezone is given, it defaults to UTC. If the tool returns an error about an unknown timezone, inform the user and ask for a valid IANA timezone name.\n"
        "- If the user asks for a calculation, use the `calculate` tool with the mathematical expression provided by the user.\n"
        "- If the user asks to calculate a date (e.g., '3 weeks from today', '2 months before 2024-01-01'), use the `calculate_date` tool. You need the start date, the operation ('add' or 'subtract'), and the duration (e.g., '3 weeks', '1 month 5 days'). If the tool returns an error, inform the user about the expected input format."
    ),
    tools=[get_current_time, calculate, calculate_date]
) 