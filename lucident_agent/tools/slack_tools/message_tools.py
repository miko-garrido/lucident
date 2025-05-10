"""
Slack message-related tools module.

This module provides functions for sending, updating, and retrieving Slack messages.
"""

import logging
from typing import Dict, Any, List, Set
from slack_sdk.errors import SlackApiError
from .client import get_slack_client
from .channel_tools import resolve_channel_id
from .formatting import format_slack_message

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def get_slack_channel_history(channel: str, limit: int = 100) -> Dict[str, Any]:
    """
    Get message history from a Slack channel.
    
    Args:
        channel: The channel name or ID to get history from
        limit: The maximum number of messages to retrieve (default: 100)
        
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
        except SlackApiError:
            # Not critical if we can't get the channel name
            pass
        
        # Get message history
        history = client.conversations_history(
            channel=channel_id,
            limit=limit
        )
        
        raw_messages = history["messages"]
        
        # Collect unique user IDs to pre-fetch user info
        user_ids = {msg.get("user", "UNKNOWN") for msg in raw_messages if msg.get("user")}
        _batch_get_users(user_ids)
        
        formatted_messages = []
        
        # Format messages for readability with cached user info
        for msg in raw_messages:
            text = msg.get("text", "")
            user_id = msg.get("user", "UNKNOWN")
            
            # Get user info from cache
            user_data = _get_user_info(user_id)
            username = user_data.get("real_name") or user_data.get("name", "Unknown User")
                
            ts = msg.get("ts", "")
            
            # Format the message text
            formatted_text = format_slack_message(text)
            
            # Add to formatted messages
            formatted_messages.append({
                "user": username,
                "user_id": user_id,
                "text": formatted_text,
                "ts": ts,
                "thread_ts": msg.get("thread_ts"),
                "reply_count": msg.get("reply_count", 0)
            })
        
        return {
            "success": True,
            "channel": channel_id,
            "channel_name": channel_name,
            "messages": formatted_messages,
            "raw_messages": raw_messages
        }
    except SlackApiError as e:
        logger.error(f"Error getting channel history: {e}")
        return {
            "success": False,
            "error": f"Error getting channel history: {str(e)}"
        }

def get_slack_thread_replies(channel: str, thread_ts: str, limit: int = 100) -> Dict[str, Any]:
    """
    Get replies in a thread from a Slack channel.
    
    Args:
        channel: The channel name or ID containing the thread
        thread_ts: The timestamp of the parent message
        limit: The maximum number of messages to retrieve (default: 100)
        
    Returns:
        A dictionary containing:
        - 'success': Boolean indicating if the operation succeeded
        - 'channel': The channel ID the thread was retrieved from
        - 'thread_ts': The timestamp of the parent message
        - 'messages': List of formatted messages in the thread
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
        # Get thread replies
        replies = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            limit=limit
        )
        
        raw_messages = replies["messages"]
        
        # Collect unique user IDs to pre-fetch user info
        user_ids = {msg.get("user", "UNKNOWN") for msg in raw_messages if msg.get("user")}
        _batch_get_users(user_ids)
        
        formatted_messages = []
        
        # Format messages for readability with cached user info
        for msg in raw_messages:
            text = msg.get("text", "")
            user_id = msg.get("user", "UNKNOWN")
            
            # Get user info from cache
            user_data = _get_user_info(user_id)
            username = user_data.get("real_name") or user_data.get("name", "Unknown User")
                
            ts = msg.get("ts", "")
            
            # Format the message text
            formatted_text = format_slack_message(text)
            
            # Add to formatted messages
            formatted_messages.append({
                "user": username,
                "user_id": user_id,
                "text": formatted_text,
                "ts": ts,
                "is_parent": ts == thread_ts
            })
        
        return {
            "success": True,
            "channel": channel_id,
            "thread_ts": thread_ts,
            "messages": formatted_messages,
            "raw_messages": raw_messages
        }
    except SlackApiError as e:
        logger.error(f"Error getting thread replies: {e}")
        return {
            "success": False,
            "error": f"Error getting thread replies: {str(e)}"
        } 