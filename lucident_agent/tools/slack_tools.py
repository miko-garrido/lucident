from typing import List, Dict, Any, Optional
import os
import logging
import ssl
import re
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

def replace_user_ids_with_names(message_text: str) -> str:
    """
    Replace user IDs in a Slack message with user names.
    
    Args:
        message_text: The text of the message containing <@USER_ID> mentions
        
    Returns:
        The message text with user IDs replaced by user names
    """
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

def format_slack_message(message_text: str, include_metadata: bool = False) -> str:
    """
    Format a Slack message by replacing user IDs with names and cleaning up other Slack-specific formatting.
    
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

def get_bot_user_id() -> Dict[str, Any]:
    """
    Get the bot user ID using the Slack API.
    
    This function retrieves the bot user ID from Slack, which is needed for 
    identifying the bot's messages and handling mentions.
    
    Returns:
        Dictionary containing the bot user ID or error information.
    """
    try:
        response = client.auth_test()
        return {
            "success": True,
            "user_id": response["user_id"]
        }
    except SlackApiError as e:
        logger.error(f"Error getting bot user ID: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def get_channel_id(channel_name: str) -> Optional[str]:
    """
    Get a channel ID from its name.
    
    Args:
        channel_name: The name of the channel (with or without the # symbol).
        
    Returns:
        The channel ID if found, None otherwise.
    """
    # Remove # if present
    if channel_name.startswith('#'):
        channel_name = channel_name[1:]
        
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
    Retrieves information about the Slack bot.
    
    Gets detailed information about the bot itself, including the bot's user ID,
    name, and other profile details from the Slack API.
    
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
    
    This function posts a message to the specified Slack channel using
    the bot's identity. The channel can be specified by name or ID.
    
    Args:
        channel: The channel name or ID. If providing a name (without #), 
                it will be converted to an ID automatically.
        message: The text content of the message to send.
        
    Returns:
        A dictionary containing the response from the Slack API with
        success or error information.
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
    
    Fetches recent messages from the specified Slack channel, up to the
    specified limit. Useful for understanding conversation context.
    
    Args:
        channel: The channel name or ID. If providing a name (without #), 
                it will be converted to an ID automatically.
        limit: Maximum number of messages to return (default: 100).
        
    Returns:
        A dictionary containing the message history or error information.
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
        
        # Process messages to replace user IDs with names
        messages = response["messages"]
        for message in messages:
            if "user" in message:
                try:
                    user_info = client.users_info(user=message["user"])
                    user_name = user_info["user"].get("real_name") or user_info["user"].get("name", "Unknown User")
                    message["user_name"] = user_name
                except SlackApiError as e:
                    logger.error(f"Error getting user info for {message['user']}: {e}")
                    message["user_name"] = "Unknown User"
                    
            if "text" in message:
                message["text"] = format_slack_message(message["text"], include_metadata=False)
                
        return {"success": True, "messages": messages}
    except SlackApiError as e:
        logger.error(f"Error getting channel history: {e}")
        return {"success": False, "error": str(e)}

def get_slack_thread_replies(channel: str, thread_ts: str, limit: int = 100) -> Dict[str, Any]:
    """
    Retrieves replies to a thread in a Slack channel.
    
    Fetches messages that are part of a specific thread in a Slack channel,
    identified by the parent message's timestamp.
    
    Args:
        channel: The channel name or ID. If providing a name (without #), 
                it will be converted to an ID automatically.
        thread_ts: The timestamp of the parent message that started the thread.
        limit: Maximum number of replies to return (default: 100).
        
    Returns:
        A dictionary containing the thread replies or error information.
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
        
        # Process messages to replace user IDs with names
        messages = response["messages"]
        for message in messages:
            if "user" in message:
                try:
                    user_info = client.users_info(user=message["user"])
                    user_name = user_info["user"].get("real_name") or user_info["user"].get("name", "Unknown User")
                    message["user_name"] = user_name
                except SlackApiError as e:
                    logger.error(f"Error getting user info for {message['user']}: {e}")
                    message["user_name"] = "Unknown User"
                    
            if "text" in message:
                message["text"] = format_slack_message(message["text"], include_metadata=False)
                
        return {"success": True, "messages": messages}
    except SlackApiError as e:
        logger.error(f"Error getting thread replies: {e}")
        return {"success": False, "error": str(e)}

def list_slack_channels() -> Dict[str, Any]:
    """
    Lists all channels in the Slack workspace.
    
    Retrieves a list of all public and private channels that the bot has access to.
    First attempts to retrieve from Supabase cache for faster response, then falls 
    back to the Slack API if needed.
    
    Returns:
        A dictionary containing the list of channels or error information.
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
    
    Modifies the content of a previously sent message, identified by its
    timestamp in the specified channel.
    
    Args:
        channel: The channel name or ID. If providing a name (without #), 
                it will be converted to an ID automatically.
        message_ts: The timestamp of the message to update.
        new_message: The new text content for the message.
        
    Returns:
        A dictionary containing the response from the Slack API or error information.
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
    
    Retrieves information about all users in the workspace. First attempts to
    retrieve from Supabase cache for faster response, then falls back to the
    Slack API if needed.
    
    Returns:
        A dictionary containing the list of users or error information.
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

def format_slack_system_message(message_text: str) -> str:
    """
    Format a Slack system message, specifically for messages like "<@USER_ID> has joined the channel".
    This is optimized for system notifications rather than general user messages.
    
    Args:
        message_text: The text of the system message
        
    Returns:
        The formatted system message with user IDs replaced by names
    """
    return replace_user_ids_with_names(message_text)

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
    'get_slack_context_from_supabase',
    'replace_user_ids_with_names',
    'format_slack_message',
    'format_slack_system_message'
]
