"""
Slack channel-related tools module.

This module provides functions for interacting with Slack channels.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from slack_sdk.errors import SlackApiError
from .client import get_slack_client
# Remove the circular import
# from ...utils.slack_context_saver import get_slack_context_from_supabase

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add a function to get context from Supabase directly
def _get_slack_channels_from_supabase() -> Optional[str]:
    """
    Helper function to get slack channels context from Supabase.
    This avoids circular imports.
    """
    try:
        from lucident_agent.Database import Database
        db = Database().client
        
        result = db.table('saved_context') \
            .select('body') \
            .eq('type', 'slack_channels') \
            .order('"created_at"', desc=True) \
            .limit(1) \
            .execute()
        
        if result.data:
            return result.data[0]['body']
        return None
    except Exception as e:
        logger.error(f"Error retrieving slack_channels from Supabase: {e}")
        return None

def get_channel_id(channel_name: str) -> Optional[str]:
    """
    Get a channel ID from its name.
    
    Args:
        channel_name: The name of the channel (with or without the # symbol).
        
    Returns:
        The channel ID if found, None otherwise.
    """
    client = get_slack_client()
    
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

def resolve_channel_id(channel: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve a channel name or ID to a channel ID.
    
    Args:
        channel: The channel name or ID. If name (without #), it will be converted to ID.
        
    Returns:
        A tuple containing (channel_id, error_message). If successful, error_message will be None.
    """
    # Check if channel is already an ID (starts with C, D, or G)
    if channel.startswith('C') or channel.startswith('D') or channel.startswith('G'):
        return channel, None
    
    # It's a name, convert to ID
    channel_id = get_channel_id(channel)
    if not channel_id:
        return None, f"Channel '{channel}' not found. Make sure the bot is added to the channel."
    
    return channel_id, None

def list_slack_channels() -> Dict[str, Any]:
    """
    Lists all channels in the Slack workspace.
    
    First attempts to retrieve from Supabase cache for faster response, then falls
    back to the Slack API if needed.
    
    Returns:
        A dictionary containing:
        - 'success': Boolean indicating if the operation succeeded
        - 'channels_markdown': Markdown-formatted channel list if from Supabase
        - 'channels': List of channel objects if from API
        - 'source': Where the data came from ('supabase' or 'api')
        - 'error': Error message if unsuccessful
    """
    client = get_slack_client()
    
    # First try to get from Supabase using direct function instead of import
    channels_markdown = _get_slack_channels_from_supabase()
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
        
        # Try to get private channels if possible
        try:
            private_response = client.conversations_list(types="private_channel")
            channels.extend(private_response["channels"])
        except SlackApiError:
            # Might not have permissions for private channels
            pass
            
        # Format as markdown for consistent response format with Supabase
        channels_markdown = "# Slack Channels\n\n"
        for channel in sorted(channels, key=lambda x: x["name"]):
            channel_type = "🔒 Private" if channel.get("is_private", False) else "# Public"
            channel_name = channel["name"]
            channel_id = channel["id"]
            member_count = channel.get("num_members", 0)
            purpose = channel.get("purpose", {}).get("value", "").replace("\n", " ")
            
            channels_markdown += f"- **{channel_name}** ({channel_id}): {channel_type}, {member_count} members\n"
            if purpose:
                channels_markdown += f"  - Purpose: {purpose}\n"
        
        return {
            "success": True,
            "channels": channels,
            "channels_markdown": channels_markdown,
            "source": "api"
        }
    except SlackApiError as e:
        logger.error(f"Error listing channels: {e}")
        return {
            "success": False,
            "error": f"Error listing channels: {str(e)}"
        } 