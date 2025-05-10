"""
Slack user-related tools module.

This module provides functions for interacting with Slack users.
"""

import logging
from typing import Dict, Any
from slack_sdk.errors import SlackApiError
from .client import get_slack_client
from .channel_tools import get_slack_context_from_supabase

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_bot_user_id() -> Dict[str, Any]:
    """
    Get the user ID of the bot.
    
    Returns:
        A dictionary containing:
        - 'success': Boolean indicating if the operation succeeded
        - 'bot_id': The bot's user ID if successful
        - 'error': Error message if unsuccessful
    """
    client = get_slack_client()
    
    try:
        # Get the bot's info
        auth_test = client.auth_test()
        bot_id = auth_test["user_id"]
        
        return {
            "success": True,
            "bot_id": bot_id
        }
    except SlackApiError as e:
        logger.error(f"Error getting bot user ID: {e}")
        return {
            "success": False,
            "error": f"Error getting bot user ID: {str(e)}"
        }

def get_slack_bot_info() -> Dict[str, Any]:
    """
    Get information about the Slack bot.
    
    Returns:
        A dictionary containing:
        - 'success': Boolean indicating if the operation succeeded
        - 'bot_id': The bot's user ID
        - 'bot_name': The bot's display name
        - 'team_id': The ID of the workspace
        - 'team_name': The name of the workspace
        - 'error': Error message if unsuccessful
    """
    client = get_slack_client()
    
    try:
        # Get bot info
        auth_test = client.auth_test()
        bot_id = auth_test["user_id"]
        bot_name = auth_test["user"]
        team_id = auth_test["team_id"]
        team_name = auth_test["team"]
        
        return {
            "success": True,
            "bot_id": bot_id,
            "bot_name": bot_name,
            "team_id": team_id,
            "team_name": team_name
        }
    except SlackApiError as e:
        logger.error(f"Error getting bot info: {e}")
        return {
            "success": False,
            "error": f"Error getting bot info: {str(e)}"
        }

def list_slack_users() -> Dict[str, Any]:
    """
    Lists all users in the Slack workspace.
    
    First attempts to retrieve from Supabase cache for faster response, then falls
    back to the Slack API if needed.
    
    Returns:
        A dictionary containing:
        - 'success': Boolean indicating if the operation succeeded
        - 'users_markdown': Markdown-formatted user list if from Supabase
        - 'users': List of user objects if from API
        - 'source': Where the data came from ('supabase' or 'api')
        - 'error': Error message if unsuccessful
    """
    client = get_slack_client()
    
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
        users = response["members"]
        
        # Format as markdown for consistent response format with Supabase
        users_markdown = "# Slack Users\n\n"
        for user in sorted(users, key=lambda x: x.get("real_name", x.get("name", ""))):
            # Skip deleted, bots, and app users unless they're our bot
            if user.get("deleted", False) and not user.get("is_bot", False):
                continue
                
            user_id = user["id"]
            user_name = user.get("real_name") or user.get("name", "Unknown")
            user_type = "🤖 Bot" if user.get("is_bot", False) else "👤 User"
            
            # Get additional details
            display_name = user.get("profile", {}).get("display_name", "")
            email = user.get("profile", {}).get("email", "")
            
            # Format the user entry
            users_markdown += f"- **{user_name}** ({user_id}): {user_type}\n"
            if display_name and display_name != user_name:
                users_markdown += f"  - Display Name: {display_name}\n"
            if email:
                users_markdown += f"  - Email: {email}\n"
        
        return {
            "success": True,
            "users": users,
            "users_markdown": users_markdown,
            "source": "api"
        }
    except SlackApiError as e:
        logger.error(f"Error listing users: {e}")
        return {
            "success": False,
            "error": f"Error listing users: {str(e)}"
        } 