"""
Script to save Slack context to Supabase.

This script uses the refactored functions to avoid circular imports.
"""

import argparse
import logging
from typing import Dict, Any

# Import the necessary functions
from .user_tools import list_slack_users, get_bot_user_id
from .channel_tools import list_slack_channels
from ...utils.slack_context_saver import (
    save_slack_context_to_supabase, 
    delete_slack_context_from_supabase,
    format_slack_users_markdown,
    format_slack_channels_markdown
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def save_slack_context() -> Dict[str, bool]:
    """
    Save Slack context to Supabase (without deleting previous records).
    
    Returns:
        Dictionary with success status for users and channels
    """
    # Get data
    users_data = list_slack_users()
    channels_data = list_slack_channels()
    
    # Format the data
    users_markdown = format_slack_users_markdown(users_data, get_bot_user_id)
    channels_markdown = format_slack_channels_markdown(channels_data)
    
    # Save to Supabase
    users_saved = save_slack_context_to_supabase("slack_users", users_markdown)
    channels_saved = save_slack_context_to_supabase("slack_channels", channels_markdown)
    
    if users_saved and channels_saved:
        logger.info("Successfully saved Slack users and channels to Supabase")
    else:
        if not users_saved:
            logger.error("Failed to save Slack users to Supabase")
        if not channels_saved:
            logger.error("Failed to save Slack channels to Supabase")
            
    return {
        "users_saved": users_saved,
        "channels_saved": channels_saved
    }

def refresh_slack_context() -> Dict[str, bool]:
    """
    Force refresh the Slack context in Supabase by deleting existing records first.
    
    Returns:
        Dictionary with success status for users and channels
    """
    logger.info("Deleting existing Slack context data...")
    
    # Delete existing slack context records
    users_deleted = delete_slack_context_from_supabase("slack_users")
    channels_deleted = delete_slack_context_from_supabase("slack_channels")
    
    if users_deleted and channels_deleted:
        logger.info("Successfully deleted existing Slack context")
    
    logger.info("Saving fresh Slack context...")
    result = save_slack_context()
    logger.info("Done! Slack context has been refreshed in Supabase.")
    
    return {
        "users_deleted": users_deleted,
        "channels_deleted": channels_deleted,
        "users_saved": result["users_saved"],
        "channels_saved": result["channels_saved"]
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Save or refresh Slack context in Supabase')
    parser.add_argument('--refresh', action='store_true', help='Delete existing records before saving new ones')
    args = parser.parse_args()
    
    if args.refresh:
        refresh_slack_context()
    else:
        save_slack_context() 