from typing import List, Dict, Any, Optional
import os
import logging
import ssl
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from ..Database import Database

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a custom SSL context that doesn't verify certificates
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Initialize Slack client with SSL verification disabled
slack_token = os.getenv("SLACK_BOT_TOKEN")
client = WebClient(token=slack_token, ssl=ssl_context)

def get_slack_context_from_supabase(context_type: str) -> Optional[str]:
    """
    Retrieve saved Slack context from Supabase
    
    Args:
        context_type: The type of context to retrieve ('slack_users' or 'slack_channels')
        
    Returns:
        The saved context as markdown string if found, None otherwise
    """
    try:
        db = Database().client
        result = db.table('saved_context') \
            .select('body') \
            .eq('type', context_type) \
            .order('"created_at"', desc=True) \
            .limit(1) \
            .execute()
        
        return result.data[0]['body'] if result.data else None
    except Exception as e:
        logger.error(f"Error retrieving {context_type} from Supabase: {e}")
        return None

def get_bot_user_id():
    """
    Get the bot user ID using the Slack API.
    
    Returns:
        str: The bot user ID.
    """
    try:
        response = client.auth_test()
        return response["user_id"]
    except SlackApiError as e:
        logger.error(f"Error getting bot user ID: {e}")
        return None

def get_channel_id(channel_name: str) -> Optional[str]:
    """
    Get a channel ID from its name.
    
    Args:
        channel_name: The name of the channel (without the # symbol).
        
    Returns:
        The channel ID if found, None otherwise.
    """
    try:
        # First try public channels
        response = client.conversations_list(types="public_channel")
        
        for channel in response["channels"]:
            if channel["name"] == channel_name:
                return channel["id"]
        
        # If not found, try private channels if we have permission
        try:
            response = client.conversations_list(types="private_channel")
            for channel in response["channels"]:
                if channel["name"] == channel_name:
                    return channel["id"]
        except SlackApiError:
            # Might not have permission for private channels
            pass
            
        logger.warning(f"Channel '{channel_name}' not found")
        return None
    except SlackApiError as e:
        logger.error(f"Error getting channel ID: {e}")
        return None

def get_slack_bot_info() -> Dict[str, Any]:
    """
    Retrieves information about the bot itself, including the bot's user ID.
    
    Returns:
        A dictionary containing information about the bot, including its user ID.
    """
    try:
        # Get auth info which includes the bot's user ID
        auth_response = client.auth_test()
        user_id = auth_response["user_id"]
        bot_name = auth_response["user"]
        
        # Get more detailed information about the bot
        bot_info = client.users_info(user=user_id)
        
        return {
            "success": True,
            "bot_id": user_id,
            "name": bot_name,
            "info": bot_info["user"]
        }
    except SlackApiError as e:
        logger.error(f"Error getting bot info: {e}")
        return {"success": False, "error": str(e)}

def send_slack_message(channel: str, message: str) -> Dict[str, Any]:
    """
    Sends a message to a Slack channel.
    
    Args:
        channel: The channel name or ID. If a name is provided (without #), 
                it will be converted to an ID.
        message: The text content of the message to send.
        
    Returns:
        A dictionary containing the response from the Slack API.
    """
    try:
        # Check if channel is an ID (starts with C or D or G)
        if not (channel.startswith('C') or channel.startswith('D') or channel.startswith('G')):
            # It's a name, convert to ID
            channel_id = get_channel_id(channel)
            if not channel_id:
                return {
                    "success": False, 
                    "error": f"Channel '{channel}' not found. Make sure the bot is added to the channel."
                }
        else:
            channel_id = channel
            
        response = client.chat_postMessage(
            channel=channel_id,
            text=message
        )
        return {"success": True, "response": response}
    except SlackApiError as e:
        logger.error(f"Error sending message: {e}")
        return {"success": False, "error": str(e)}

def get_slack_channel_history(channel: str, limit: int = 100) -> Dict[str, Any]:
    """
    Retrieves message history from a Slack channel.
    
    Args:
        channel: The channel name or ID. If a name is provided (without #), 
                it will be converted to an ID.
        limit: Maximum number of messages to return (default: 100).
        
    Returns:
        A dictionary containing the message history.
    """
    try:
        # Check if channel is an ID (starts with C or D or G)
        if not (channel.startswith('C') or channel.startswith('D') or channel.startswith('G')):
            # It's a name, convert to ID
            channel_id = get_channel_id(channel)
            if not channel_id:
                return {
                    "success": False, 
                    "error": f"Channel '{channel}' not found. Make sure the bot is added to the channel."
                }
        else:
            channel_id = channel
            
        response = client.conversations_history(
            channel=channel_id,
            limit=limit
        )
        return {"success": True, "messages": response["messages"]}
    except SlackApiError as e:
        logger.error(f"Error getting channel history: {e}")
        return {"success": False, "error": str(e)}

def get_slack_thread_replies(channel: str, thread_ts: str, limit: int = 100) -> Dict[str, Any]:
    """
    Retrieves replies to a thread in a Slack channel.
    
    Args:
        channel: The channel name or ID. If a name is provided (without #), 
                it will be converted to an ID.
        thread_ts: The timestamp of the parent message.
        limit: Maximum number of replies to return (default: 100).
        
    Returns:
        A dictionary containing the thread replies.
    """
    try:
        # Check if channel is an ID (starts with C or D or G)
        if not (channel.startswith('C') or channel.startswith('D') or channel.startswith('G')):
            # It's a name, convert to ID
            channel_id = get_channel_id(channel)
            if not channel_id:
                return {
                    "success": False, 
                    "error": f"Channel '{channel}' not found. Make sure the bot is added to the channel."
                }
        else:
            channel_id = channel
            
        response = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            limit=limit
        )
        return {"success": True, "messages": response["messages"]}
    except SlackApiError as e:
        logger.error(f"Error getting thread replies: {e}")
        return {"success": False, "error": str(e)}

def list_slack_channels() -> Dict[str, Any]:
    """
    Lists all channels in the Slack workspace.
    First tries to retrieve from Supabase cache, falls back to Slack API if needed.
    
    Returns:
        A dictionary containing the list of channels.
    """
    # First try to get from Supabase
    channels_markdown = get_slack_context_from_supabase('slack_channels')
    if channels_markdown:
        return {
            "success": True, 
            "channels_markdown": channels_markdown,
            "source": "supabase"
        }
    
    # Fall back to Slack API
    try:
        channels = []
        # Get public channels
        public_response = client.conversations_list(types="public_channel")
        channels.extend(public_response["channels"])
        
        # Try to get private channels if we have permission
        try:
            private_response = client.conversations_list(types="private_channel")
            channels.extend(private_response["channels"])
        except SlackApiError:
            # Might not have permission for private channels
            pass
        
        # Format the channels to include name and ID
        formatted_channels = [
            {
                "id": channel["id"],
                "name": channel["name"],
                "is_private": channel.get("is_private", False),
                "is_archived": channel.get("is_archived", False),
                "num_members": channel.get("num_members", 0)
            }
            for channel in channels
        ]
        
        return {"success": True, "channels": formatted_channels, "source": "api"}
    except SlackApiError as e:
        logger.error(f"Error listing channels: {e}")
        return {"success": False, "error": str(e)}

def update_slack_message(channel: str, message_ts: str, new_message: str) -> Dict[str, Any]:
    """
    Updates an existing message in a Slack channel.
    
    Args:
        channel: The channel name or ID. If a name is provided (without #), 
                it will be converted to an ID.
        message_ts: The timestamp of the message to update.
        new_message: The new text content for the message.
        
    Returns:
        A dictionary containing the response from the Slack API.
    """
    try:
        # Check if channel is an ID (starts with C or D or G)
        if not (channel.startswith('C') or channel.startswith('D') or channel.startswith('G')):
            # It's a name, convert to ID
            channel_id = get_channel_id(channel)
            if not channel_id:
                return {
                    "success": False, 
                    "error": f"Channel '{channel}' not found. Make sure the bot is added to the channel."
                }
        else:
            channel_id = channel
            
        response = client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=new_message
        )
        return {"success": True, "response": response}
    except SlackApiError as e:
        logger.error(f"Error updating message: {e}")
        return {"success": False, "error": str(e)}

def list_slack_users() -> Dict[str, Any]:
    """
    Lists all users in the Slack workspace.
    First tries to retrieve from Supabase cache, falls back to Slack API if needed.
    
    Returns:
        A dictionary containing the list of users.
    """
    # First try to get from Supabase
    users_markdown = get_slack_context_from_supabase('slack_users')
    if users_markdown:
        return {
            "success": True, 
            "users_markdown": users_markdown,
            "source": "supabase"
        }
    
    # Fall back to Slack API
    try:
        response = client.users_list()
        
        # Format the users to include name and ID
        formatted_users = [
            {
                "id": user["id"],
                "name": user["name"],
                "real_name": user.get("real_name", ""),
                "email": user.get("profile", {}).get("email", ""),
                "is_bot": user.get("is_bot", False),
                "is_admin": user.get("is_admin", False)
            }
            for user in response["members"]
            if not user.get("deleted", False)  # Filter out deleted users
        ]
        
        return {"success": True, "users": formatted_users, "source": "api"}
    except SlackApiError as e:
        logger.error(f"Error listing users: {e}")
        return {"success": False, "error": str(e)}

# Export the functions for direct import
__all__ = [
    'get_bot_user_id',
    'get_channel_id',
    'get_slack_bot_info',
    'send_slack_message',
    'get_slack_channel_history',
    'get_slack_thread_replies',
    'list_slack_channels',
    'list_slack_users',
    'update_slack_message',
    'get_slack_context_from_supabase'
]
