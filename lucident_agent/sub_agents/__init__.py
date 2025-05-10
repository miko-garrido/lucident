"""
Sub-agents module for the Harpy agent system.

This module provides specialized agents for different platforms.
"""
from typing import Any

from .gmail_agent import gmail_agent
from .slack_agent import slack_agent
from .clickup_agent import clickup_agent
from .calendar_agent import calendar_agent

__all__: list[str] = ["gmail_agent", "slack_agent", "clickup_agent", "calendar_agent"]