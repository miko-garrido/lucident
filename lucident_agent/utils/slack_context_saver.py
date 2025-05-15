import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from lucident_agent.tools.slack_tools import (
    list_slack_users, 
    list_slack_channels, 
    get_bot_user_id, 
    get_slack_bot_info
)
from lucident_agent.Database import Database
import logging
import argparse
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database client
db = Database().client

def get_slack_context_from_supabase(context_type: str) -> Optional[str]:
    """
    Retrieve saved Slack context from Supabase database.
    
    Args:
        context_type: The type of context to retrieve ('slack_users' or 'slack_channels')
        
    Returns:
        The saved context as markdown string if found, None otherwise
    """
    try:
        result = db.table('saved_context') \
            .select('body') \
            .eq('type', context_type) \
            .order('"created_at"', desc=True) \
            .limit(1) \
            .execute()
        
        if result.data:
            return result.data[0]['body']
        return None
    except Exception as e:
        logger.error(f"Error retrieving {context_type} from Supabase: {e}")
        return None

def save_slack_context_to_supabase(context_type: str, body: str) -> bool:
    """
    Save Slack context to Supabase database.
    
    Args:
        context_type: The type of context to save ('slack_users' or 'slack_channels')
        body: The context data to save (typically formatted markdown)
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        response = db.table("saved_context").insert({
            "type": context_type, 
            "body": body
        }).execute()
        
        if response.data:
            logger.info(f"Saved {context_type} to Supabase")
            return True
        return False
    except Exception as e:
        logger.error(f"Error saving {context_type} to Supabase: {e}")
        return False

def delete_slack_context_from_supabase(context_type: str) -> bool:
    """
    Delete Slack context from Supabase database.
    
    Args:
        context_type: The type of context to delete ('slack_users' or 'slack_channels')
        
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        response = db.table("saved_context").delete().eq("type", context_type).execute()
        
        logger.info(f"Deleted {len(response.data)} {context_type} records from Supabase")
        return True
    except Exception as e:
        logger.error(f"Error deleting {context_type} from Supabase: {e}")
        return False

def format_slack_users_markdown():
    """
    Format Slack users data in markdown
    Note: This requires 'users:read' scope which may not be available.
    If not available, we'll just save the bot's user ID from auth.test.
    """
    users_data = list_slack_users()
    
    if not users_data.get("success", False):
        # If we don't have permission to list all users, just get basic bot ID
        logger.info("Cannot list all users. Saving basic bot info only.")
        
        try:
            # auth_test doesn't require users:read permission
            bot_id = get_bot_user_id()
            
            if bot_id:
                lines = [
                    "**Slack Bot Info Only**",
                    f"*Bot*",
                    f"- id: {bot_id}",
                    f"- Note: Limited permissions available. Bot token needs 'users:read' scope to list users.",
                    ""
                ]
                return "\n".join(lines)
            else:
                return "Error: Could not retrieve bot user ID."
        except Exception as e:
            logger.error(f"Error getting bot user ID: {e}")
            return f"Error fetching Slack bot ID: {str(e)}"
    
    # Check if we got data from Supabase
    if "source" in users_data and users_data["source"] == "supabase":
        logger.info("Using existing markdown from Supabase for users")
        return users_data["users_markdown"]
    
    lines = []
    for user in users_data.get("users", []):
        lines.extend([
            f"*{user.get('name', 'Unknown')}*",
            f"- id: {user.get('id', '')}",
            f"- real_name: {user.get('real_name', '')}",
            f"- email: {user.get('email', '')}",
            f"- is_bot: {user.get('is_bot', False)}",
            f"- is_admin: {user.get('is_admin', False)}",
            ""  # blank line between users
        ])
    return "\n".join(lines)

def format_slack_channels_markdown():
    """
    Format Slack channels data in markdown
    """
    channels_data = list_slack_channels()
    
    if not channels_data.get("success", False):
        return f"Error fetching Slack channels: {channels_data.get('error', 'Unknown error')}"
    
    # Check if we got data from Supabase
    if "source" in channels_data and channels_data["source"] == "supabase":
        logger.info("Using existing markdown from Supabase for channels")
        return channels_data["channels_markdown"]
    
    lines = []
    lines.append("**Slack Channels**")
    
    # First list public channels
    lines.append("\n*Public Channels*")
    public_channels = [c for c in channels_data.get("channels", []) if not c.get("is_private", False)]
    if public_channels:
        for channel in public_channels:
            lines.append(f"- **{channel.get('name', 'Unknown')}** (_ID: {channel.get('id', '')})")
            lines.append(f"  - members: {channel.get('num_members', 0)}")
            lines.append(f"  - archived: {channel.get('is_archived', False)}")
    else:
        lines.append("- _None_")
    
    # Then list private channels
    lines.append("\n*Private Channels*")
    private_channels = [c for c in channels_data.get("channels", []) if c.get("is_private", False)]
    if private_channels:
        for channel in private_channels:
            lines.append(f"- **{channel.get('name', 'Unknown')}** (_ID: {channel.get('id', '')})")
            lines.append(f"  - members: {channel.get('num_members', 0)}")
            lines.append(f"  - archived: {channel.get('is_archived', False)}")
    else:
        lines.append("- _None_")
    
    return "\n".join(lines)

def save_slack_context():
    """
    Save Slack context to Supabase (without deleting previous records)
    """
    # Format the data
    users_markdown = format_slack_users_markdown()
    channels_markdown = format_slack_channels_markdown()
    
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

def refresh_slack_context():
    """
    Force refresh the Slack context in Supabase by deleting existing records first
    """
    logger.info("Deleting existing Slack context data...")
    
    # Delete existing slack context records
    users_deleted = delete_slack_context_from_supabase("slack_users")
    channels_deleted = delete_slack_context_from_supabase("slack_channels")
    
    if users_deleted and channels_deleted:
        logger.info("Successfully deleted existing Slack context")
    
    logger.info("Saving fresh Slack context...")
    save_slack_context()
    logger.info("Done! Slack context has been refreshed in Supabase.")

def main():
    """
    Main function to save Slack context to Supabase
    """
    save_slack_context()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Save or refresh Slack context in Supabase')
    parser.add_argument('--refresh', action='store_true', help='Delete existing records before saving new ones')
    args = parser.parse_args()
    
    if args.refresh:
        refresh_slack_context()
    else:
        main() 