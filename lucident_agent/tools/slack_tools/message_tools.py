"""
Slack message-related tools module.

This module provides functions for sending, updating, and retrieving Slack messages.
"""

import logging
import re
from typing import Dict, Any, List, Set
from slack_sdk.errors import SlackApiError
from .client import get_slack_client
from .channel_tools import resolve_channel_id
from .formatting import format_slack_message, create_slack_message_link

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default workspace ID - this should be set to your actual workspace ID
DEFAULT_WORKSPACE_ID = "T0123456789"  # Update this with your actual workspace ID

# In-memory user cache for optimizing API calls
_user_cache = {}

def _get_user_info(user_id: str) -> Dict[str, Any]:
    """
    Get user information with caching to reduce API calls.
    
    Args:
        user_id: The ID of the user to get information for
        
    Returns:
        Dictionary with user information or empty dict if not found
    """
    if not user_id or user_id == "UNKNOWN":
        return {"name": "Unknown User", "real_name": "Unknown User"}
        
    # Check cache first
    if user_id in _user_cache:
        return _user_cache[user_id]
    
    # Fetch from API
    client = get_slack_client()
    try:
        user_info = client.users_info(user=user_id)
        user_data = user_info["user"]
        _user_cache[user_id] = user_data
        return user_data
    except SlackApiError as e:
        logger.error(f"Error getting user info for {user_id}: {e}")
        # Store failed lookups to avoid repeated failures
        _user_cache[user_id] = {"name": "Unknown User", "real_name": "Unknown User"}
        return _user_cache[user_id]

def _batch_get_users(user_ids: Set[str]) -> None:
    """
    Pre-fetch user information for multiple users at once.
    This doesn't actually batch the API calls (Slack API limitation)
    but prevents redundant logging and handles all the fetching in one place.
    
    Args:
        user_ids: Set of user IDs to fetch information for
    """
    client = get_slack_client()
    
    # Filter out already cached users
    users_to_fetch = [uid for uid in user_ids if uid not in _user_cache and uid != "UNKNOWN"]
    
    if not users_to_fetch:
        return
        
    logger.info(f"Prefetching information for {len(users_to_fetch)} users")
    
    # Fetch each user (Slack doesn't support batched user fetching)
    for user_id in users_to_fetch:
        try:
            user_info = client.users_info(user=user_id)
            _user_cache[user_id] = user_info["user"]
        except SlackApiError as e:
            logger.error(f"Error batch fetching user {user_id}: {e}")
            _user_cache[user_id] = {"name": "Unknown User", "real_name": "Unknown User"}

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
        _batch_get_users(user_ids)
        
        # Format the messages
        formatted_messages = []
        raw_messages_with_links = []
        
        for msg in messages:
            # Format the message text
            user_id = msg.get("user", "UNKNOWN")
            
            # Get user info for the message sender
            if user_id != "UNKNOWN":
                user_info = _get_user_info(user_id)
                user_name = user_info.get("real_name") or user_info.get("name", "Unknown User")
            else:
                user_name = "Unknown User"
            
            # Create message link
            message_ts = msg.get("ts", "")
            thread_ts = msg.get("thread_ts", None)
            message_link = create_slack_message_link(workspace_id, channel_id, message_ts, thread_ts)
            
            # Add the message to our results
            if "text" in msg:
                # Format the text
                raw_text = msg["text"]
                formatted_text = format_slack_message(raw_text)
                
                # System messages don't need sender prefix
                if raw_text.startswith("<@") and any(action in raw_text for action in 
                                             ["has joined", "has left", "added", "removed", "set the topic"]):
                    formatted_messages.append({
                        "text": formatted_text,
                        "ts": msg["ts"],
                        "link": message_link
                    })
                else:
                    # Regular messages
                    formatted_messages.append({
                        "user": user_name,
                        "text": formatted_text,
                        "ts": msg["ts"],
                        "thread_ts": msg.get("thread_ts"),
                        "link": message_link
                    })
                
            # Add raw message with metadata and link
            raw_message = msg.copy()
            raw_message["user_name"] = user_name
            raw_message["link"] = message_link
            raw_messages_with_links.append(raw_message)
        
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
    Get replies to a thread in a Slack channel.
    
    Args:
        channel: The channel name or ID where the thread exists
        thread_ts: The timestamp of the parent message of the thread
        limit: The maximum number of replies to retrieve (default: 100)
        workspace_id: The Slack workspace/team ID (default: DEFAULT_WORKSPACE_ID)
        
    Returns:
        A dictionary containing:
        - 'success': Boolean indicating if the operation succeeded
        - 'channel': The channel ID the thread is in
        - 'thread_ts': The timestamp of the parent message
        - 'messages': List of formatted thread messages including the parent
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
        # Get replies in the thread
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
        _batch_get_users(user_ids)
        
        # Format the messages
        formatted_messages = []
        raw_messages_with_links = []
        
        for msg in messages:
            # Format the message text
            user_id = msg.get("user", "UNKNOWN")
            
            # Get user info for the message sender
            if user_id != "UNKNOWN":
                user_info = _get_user_info(user_id)
                user_name = user_info.get("real_name") or user_info.get("name", "Unknown User")
            else:
                user_name = "Unknown User"
            
            # Create message link
            message_ts = msg.get("ts", "")
            message_link = create_slack_message_link(workspace_id, channel_id, message_ts, thread_ts)
            
            if "text" in msg:
                # Format the text
                raw_text = msg["text"]
                formatted_text = format_slack_message(raw_text)
                
                # Add to our formatted results
                formatted_messages.append({
                    "user": user_name,
                    "text": formatted_text,
                    "ts": msg["ts"],
                    "is_parent": msg["ts"] == thread_ts,
                    "link": message_link
                })
            
            # Add raw message with metadata and link
            raw_message = msg.copy()
            raw_message["user_name"] = user_name
            raw_message["link"] = message_link
            raw_messages_with_links.append(raw_message)
        
        return {
            "success": True,
            "channel": channel_id,
            "thread_ts": thread_ts,
            "messages": formatted_messages,
            "raw_messages": raw_messages_with_links
        }
    except SlackApiError as e:
        logger.error(f"Error getting thread replies: {e}")
        return {
            "success": False,
            "error": f"Error getting thread replies: {str(e)}"
        } 