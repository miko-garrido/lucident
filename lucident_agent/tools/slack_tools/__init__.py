"""
Slack tools package for the Lucident agent.

This package provides modular tools for interacting with Slack APIs.
"""

from .message_tools import (
    send_slack_message,
    update_slack_message,
    get_slack_channel_history,
    get_slack_thread_replies
)

from .user_tools import (
    get_bot_user_id,
    get_slack_bot_info,
    list_slack_users
)

from .channel_tools import (
    list_slack_channels,
    get_channel_id,
    resolve_channel_id
)

from .formatting import (
    format_slack_message,
    replace_user_ids_with_names,
    format_slack_system_message
)

__all__ = [
    # Message operations
    'send_slack_message',
    'update_slack_message',
    'get_slack_channel_history',
    'get_slack_thread_replies',
    
    # User operations
    'get_bot_user_id',
    'get_slack_bot_info',
    'list_slack_users',
    
    # Channel operations
    'list_slack_channels',
    'get_channel_id',
    'resolve_channel_id',
    
    # Formatting utilities
    'format_slack_message',
    'replace_user_ids_with_names',
    'format_slack_system_message'
] 