"""
Slack message formatting module.

This module provides functions for formatting Slack messages, such as 
replacing user IDs with names and cleaning up Slack-specific formatting.
"""

import re
import logging
from slack_sdk.errors import SlackApiError
from .client import get_slack_client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def replace_user_ids_with_names(message_text: str) -> str:
    """
    Replace user IDs in a Slack message with user names.
    
    Args:
        message_text: The text of the message containing <@USER_ID> mentions
        
    Returns:
        The message text with user IDs replaced by user names
    """
    client = get_slack_client()
    
    # Find all user mentions in the format <@USER_ID>
    user_mentions = re.findall(r'<@([A-Z0-9]+)>', message_text)
    
    if not user_mentions:
        return message_text
    
    # Get user info for each mentioned user
    for user_id in user_mentions:
        try:
            user_info = client.users_info(user=user_id)
            user_name = user_info["user"].get("real_name") or user_info["user"].get("name", "Unknown User")
            
            # For system messages like "<@USER_ID> has joined the group"
            if f"<@{user_id}>" in message_text and not message_text.startswith("from ") and not message_text.startswith("(display"):
                message_text = message_text.replace(f"<@{user_id}>", user_name)
            else:
                # For regular mentions within messages
                message_text = message_text.replace(f"<@{user_id}>", user_name)
        except SlackApiError as e:
            logger.error(f"Error getting user info for {user_id}: {e}")
            # Keep the original mention if we can't get the user info
    
    return message_text

def create_slack_message_link(workspace_id: str, channel_id: str, message_ts: str, thread_ts: str = None) -> str:
    """
    Create a direct link to a Slack message.
    
    Args:
        workspace_id: The workspace/team ID (T...)
        channel_id: The channel ID (C...)
        message_ts: The message timestamp 
        thread_ts: The thread timestamp (if message is in a thread)
        
    Returns:
        URL to the message in Slack web client
    """
    # Convert timestamp format by replacing dots with underscores
    formatted_message_ts = message_ts.replace(".", "_")
    
    # If it's a thread message
    if thread_ts:
        formatted_thread_ts = thread_ts.replace(".", "_")
        return f"https://app.slack.com/client/{workspace_id}/{channel_id}/thread/{formatted_thread_ts}?thread_ts={formatted_thread_ts}&ts={formatted_message_ts}"
    
    # If it's a regular message
    return f"https://app.slack.com/client/{workspace_id}/{channel_id}/p{formatted_message_ts}"

def format_slack_message(message_text: str, include_metadata: bool = False) -> str:
    """
    Format a Slack message by replacing user IDs with names and cleaning up Slack-specific formatting.
    
    Args:
        message_text: The text of the Slack message to format
        include_metadata: Whether to include sender metadata like (display/user ID: UXXXX)
        
    Returns:
        The cleaned and formatted message text
    """
    # Check if it's a system message about user actions
    is_system_message = False
    if "<@U" in message_text and any(action in message_text for action in 
                                     ["has joined", "has left", "added", "removed", "set the topic"]):
        is_system_message = True
    
    # Replace user IDs with names
    formatted_text = replace_user_ids_with_names(message_text)
    
    # Replace common Slack formatting
    # Replace @here and @channel
    formatted_text = formatted_text.replace("<!here>", "@here")
    formatted_text = formatted_text.replace("<!channel>", "@channel")
    
    # For system messages, we just want to replace the user IDs but keep the message format
    if is_system_message:
        return formatted_text
    
    # For regular messages, continue with additional formatting
    if not include_metadata:
        # Remove patterns like "Kai (display/user ID: U069RFXNASJ)"
        formatted_text = re.sub(r'\w+ \(display/user ID: [A-Z0-9]+\):', '', formatted_text)
        
        # Remove patterns like "from Kai:"
        formatted_text = re.sub(r'from \w+:', '', formatted_text)
        
        # Clean up any extra whitespace
        formatted_text = re.sub(r'\s+', ' ', formatted_text).strip()
    
    return formatted_text

def format_slack_system_message(message_text: str) -> str:
    """
    Format a Slack system message, such as "<@USER_ID> has joined the channel".
    
    Args:
        message_text: The text of the system message
        
    Returns:
        The formatted system message with user IDs replaced by names
    """
    return replace_user_ids_with_names(message_text) 