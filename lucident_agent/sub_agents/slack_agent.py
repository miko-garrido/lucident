"""
Slack agent module.

This module provides the main Slack agent for the Lucident system.
It exports a pre-configured Slack agent instance.
"""

# Import the slack agent factory
from .slack_agent_factory import slack_agent

# Export the agent instance
__all__ = ['slack_agent'] 