"""
Slack message-related tools module.

This module provides functions for sending, updating, and retrieving Slack messages.
"""

import logging
import re
from typing import Dict, Any, List, Set
from slack_sdk.errors import SlackApiError
from .client import get_slack_client, SlackClient
from .channel_tools import resolve_channel_id
from .formatting import format_slack_message, create_slack_message_link

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default workspace ID - this should be set to your actual workspace ID
DEFAULT_WORKSPACE_ID = "T0123456789"  # Update this with your actual workspace ID

def send_slack_message(channel: str, message: str) -> Dict[str, Any]:
    """
    Send a message to a Slack channel.
    
    Args:
        channel: The channel name or ID to send the message to
        message: The message text to send
        
    Returns:
        A dictionary containing:
        - 'success': Boolean indicating if the operation succeeded
        - 'channel': The channel ID the message was sent to
        - 'ts': The timestamp of the sent message (for threading)
        - 'error': Error message if unsuccessful
    """
    client = get_slack_client()
    
    # Resolve channel ID if a name was provided
    channel_id, error = resolve_channel_id(channel)
    if error:
        return {
            "success": False,
            "error": error
        }
    
    try:
        # Send the message
        response = client.chat_postMessage(
            channel=channel_id,
            text=message,
            unfurl_links=True
        )
        
        return {
            "success": True,
            "channel": channel_id,
            "ts": response["ts"]
        }
    except SlackApiError as e:
        logger.error(f"Error sending message: {e}")
        return {
            "success": False,
            "error": f"Error sending message: {str(e)}"
        }

def update_slack_message(channel: str, message_ts: str, new_message: str) -> Dict[str, Any]:
    """
    Update an existing Slack message.
    
    Args:
        channel: The channel name or ID where the message exists
        message_ts: The timestamp of the message to update
        new_message: The new message text
        
    Returns:
        A dictionary containing:
        - 'success': Boolean indicating if the operation succeeded
        - 'channel': The channel ID the message was updated in
        - 'ts': The timestamp of the updated message
        - 'error': Error message if unsuccessful
    """
    client = get_slack_client()
    
    # Resolve channel ID if a name was provided
    channel_id, error = resolve_channel_id(channel)
    if error:
        return {
            "success": False,
            "error": error
        }
    
    try:
        # Update the message
        response = client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=new_message
        )
        
        return {
            "success": True,
            "channel": channel_id,
            "ts": response["ts"]
        }
    except SlackApiError as e:
        logger.error(f"Error updating message: {e}")
        return {
            "success": False,
            "error": f"Error updating message: {str(e)}"
        }

def get_slack_channel_history(channel: str, limit: int = 100, workspace_id: str = DEFAULT_WORKSPACE_ID) -> Dict[str, Any]:
    """
    Get message history from a Slack channel.
    
    Args:
        channel: The channel name or ID to get history from
        limit: The maximum number of messages to retrieve (default: 100)
        workspace_id: The Slack workspace/team ID (default: DEFAULT_WORKSPACE_ID)
        
    Returns:
        A dictionary containing:
        - 'success': Boolean indicating if the operation succeeded
        - 'channel': The channel ID the history was retrieved from
        - 'channel_name': The name of the channel if available
        - 'messages': List of formatted messages
        - 'raw_messages': List of unformatted messages with metadata
        - 'error': Error message if unsuccessful
    """
    client = get_slack_client()
    
    # Resolve channel ID if a name was provided
    channel_id, error = resolve_channel_id(channel)
    if error:
        return {
            "success": False,
            "error": error
        }
    
    try:
        # Get channel info
        channel_name = None
        try:
            channel_info = client.conversations_info(channel=channel_id)
            channel_name = channel_info["channel"]["name"]
        except SlackApiError as e:
            logger.warning(f"Could not get channel name: {e}")
        
        # Get all users mentioned in messages to prefetch their info
        response = client.conversations_history(
            channel=channel_id,
            limit=limit
        )
        
        if not response["ok"]:
            return {
                "success": False,
                "error": f"API error: {response.get('error', 'Unknown error')}"
            }
        
        messages = response["messages"]
        
        if not messages:
            return {
                "success": True,
                "channel": channel_id,
                "channel_name": channel_name,
                "messages": [],
                "raw_messages": []
            }
        
        # Extract all user IDs from messages to batch prefetch
        user_ids = set()
        for msg in messages:
            user_id = msg.get("user", "UNKNOWN")
            user_ids.add(user_id)
            
            # Also get users from message text with <@USER_ID> format
            if "text" in msg:
                user_mentions = re.findall(r'<@([A-Z0-9]+)>', msg["text"])
                user_ids.update(user_mentions)
        
        # Prefetch all users at once
        SlackClient.batch_prefetch_users(user_ids)
        
        # Format the messages
        formatted_messages = []
        raw_messages_with_links = []
        
        for msg in messages:
            # Format timestamp
            ts = msg.get("ts", "")
            
            # Format the message
            raw_text = msg.get("text", "")
            
            # Handle message formatting
            if msg.get("subtype") == "bot_message":
                # Bot messages
                bot_name = msg.get("username", "Bot")
                formatted_text = f"{bot_name}: {raw_text}"
            elif msg.get("subtype") == "channel_join" or msg.get("subtype") == "channel_leave":
                # System messages
                formatted_text = raw_text
            else:
                # Regular user messages
                user_id = msg.get("user", "UNKNOWN")
                user_data = SlackClient.get_user_info(user_id)
                name = user_data.get("real_name") or user_data.get("name", "Unknown User")
                formatted_text = f"{name}: {raw_text}"
            
            # Format the complete message
            formatted_messages.append(format_slack_message(formatted_text))
            
            # Add message link for raw messages
            msg_with_link = msg.copy()
            thread_ts = msg.get("thread_ts")
            msg_with_link["link"] = create_slack_message_link(
                workspace_id,
                channel_id,
                ts,
                thread_ts
            )
            raw_messages_with_links.append(msg_with_link)
        
        return {
            "success": True,
            "channel": channel_id,
            "channel_name": channel_name,
            "messages": formatted_messages,
            "raw_messages": raw_messages_with_links
        }
    except SlackApiError as e:
        logger.error(f"Error getting channel history: {e}")
        return {
            "success": False,
            "error": f"Error getting channel history: {str(e)}"
        }

def get_slack_thread_replies(channel: str, thread_ts: str, limit: int = 100, workspace_id: str = DEFAULT_WORKSPACE_ID) -> Dict[str, Any]:
    """
    Get replies from a Slack thread.
    
    Args:
        channel: The channel name or ID where the thread exists
        thread_ts: The timestamp of the parent message
        limit: The maximum number of replies to retrieve (default: 100)
        workspace_id: The Slack workspace/team ID (default: DEFAULT_WORKSPACE_ID)
        
    Returns:
        A dictionary containing:
        - 'success': Boolean indicating if the operation succeeded
        - 'channel': The channel ID the thread was retrieved from
        - 'thread_ts': The timestamp of the parent message
        - 'replies': List of formatted reply messages
        - 'raw_replies': List of unformatted replies with metadata
        - 'error': Error message if unsuccessful
    """
    client = get_slack_client()
    
    # Resolve channel ID if a name was provided
    channel_id, error = resolve_channel_id(channel)
    if error:
        return {
            "success": False,
            "error": error
        }
    
    try:
        # Get replies to the thread
        response = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            limit=limit
        )
        
        if not response["ok"]:
            return {
                "success": False,
                "error": f"API error: {response.get('error', 'Unknown error')}"
            }
        
        messages = response["messages"]
        
        if not messages:
            return {
                "success": True,
                "channel": channel_id,
                "thread_ts": thread_ts,
                "replies": [],
                "raw_replies": []
            }
        
        # Extract all user IDs from messages to batch prefetch
        user_ids = set()
        for msg in messages:
            user_id = msg.get("user", "UNKNOWN")
            user_ids.add(user_id)
            
            # Also get users from message text with <@USER_ID> format
            if "text" in msg:
                user_mentions = re.findall(r'<@([A-Z0-9]+)>', msg["text"])
                user_ids.update(user_mentions)
        
        # Prefetch all users at once
        SlackClient.batch_prefetch_users(user_ids)
        
        # Format the messages
        formatted_replies = []
        raw_replies_with_links = []
        
        # Skip the first message which is the parent message
        for msg in messages[1:]:
            # Format timestamp
            ts = msg.get("ts", "")
            
            # Format the message
            raw_text = msg.get("text", "")
            
            # Handle message formatting
            if msg.get("subtype") == "bot_message":
                # Bot messages
                bot_name = msg.get("username", "Bot")
                formatted_text = f"{bot_name}: {raw_text}"
            else:
                # Regular user messages
                user_id = msg.get("user", "UNKNOWN")
                user_data = SlackClient.get_user_info(user_id)
                name = user_data.get("real_name") or user_data.get("name", "Unknown User")
                formatted_text = f"{name}: {raw_text}"
            
            # Format the complete message
            formatted_replies.append(format_slack_message(formatted_text))
            
            # Add message link for raw messages
            msg_with_link = msg.copy()
            msg_with_link["link"] = create_slack_message_link(
                workspace_id,
                channel_id,
                ts,
                thread_ts
            )
            raw_replies_with_links.append(msg_with_link)
        
        return {
            "success": True,
            "channel": channel_id,
            "thread_ts": thread_ts,
            "replies": formatted_replies,
            "raw_replies": raw_replies_with_links
        }
    except SlackApiError as e:
        logger.error(f"Error getting thread replies: {e}")
        return {
            "success": False,
            "error": f"Error getting thread replies: {str(e)}"
        } 