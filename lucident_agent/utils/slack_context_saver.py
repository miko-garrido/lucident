import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Remove direct imports from slack_tools to break circular dependency
from lucident_agent.Database import Database
import logging
import argparse
from typing import Optional, Dict, Any, List

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

# Modified to accept data from outside instead of importing slack tools
def format_slack_users_markdown(users_data: Dict[str, Any] = None, get_bot_user_id_fn=None):
    """
    Format Slack users data in markdown
    Note: This requires 'users:read' scope which may not be available.
    If not available, we'll just save the bot's user ID from auth.test.
    
    Args:
        users_data: Dictionary containing user data from slack API
        get_bot_user_id_fn: Function to get bot user ID if users_data not available
    """
    if not users_data or not users_data.get("success", False):
        # If we don't have permission to list all users, just get basic bot ID
        logger.info("Cannot list all users. Saving basic bot info only.")
        
        try:
            # Use the function passed in instead of importing directly
            if get_bot_user_id_fn:
                bot_info = get_bot_user_id_fn()
                bot_id = bot_info.get("bot_id") if bot_info.get("success", False) else None
                
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
            else:
                return "Error: No function provided to get bot user ID."
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

# Modified to accept data from outside instead of importing slack tools
def format_slack_channels_markdown(channels_data: Dict[str, Any] = None):
    """
    Format Slack channels data in markdown
    
    Args:
        channels_data: Dictionary containing channel data from slack API
    """
    if not channels_data or not channels_data.get("success", False):
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

# These functions need to be modified to accept the necessary functions as parameters
def save_slack_context(list_users_fn=None, list_channels_fn=None, get_bot_id_fn=None):
    """
    Save Slack context to Supabase (without deleting previous records)
    
    Args:
        list_users_fn: Function to list Slack users
        list_channels_fn: Function to list Slack channels
        get_bot_id_fn: Function to get bot user ID
    """
    # Get data using passed functions
    users_data = list_users_fn() if list_users_fn else {"success": False}
    channels_data = list_channels_fn() if list_channels_fn else {"success": False}
    
    # Format the data
    users_markdown = format_slack_users_markdown(users_data, get_bot_id_fn)
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

def refresh_slack_context(list_users_fn=None, list_channels_fn=None, get_bot_id_fn=None):
    """
    Force refresh the Slack context in Supabase by deleting existing records first
    
    Args:
        list_users_fn: Function to list Slack users
        list_channels_fn: Function to list Slack channels
        get_bot_id_fn: Function to get bot user ID
    """
    logger.info("Deleting existing Slack context data...")
    
    # Delete existing slack context records
    users_deleted = delete_slack_context_from_supabase("slack_users")
    channels_deleted = delete_slack_context_from_supabase("slack_channels")
    
    if users_deleted and channels_deleted:
        logger.info("Successfully deleted existing Slack context")
    
    logger.info("Saving fresh Slack context...")
    save_slack_context(list_users_fn, list_channels_fn, get_bot_id_fn)
    logger.info("Done! Slack context has been refreshed in Supabase.")

if __name__ == "__main__":
    import sys
    parser = argparse.ArgumentParser(description='Save or refresh Slack context in Supabase')
    parser.add_argument('--refresh', action='store_true', help='Delete existing records before saving new ones')
    args = parser.parse_args()

    # Import Slack functions only when running as script to avoid circular imports
    try:
        from lucident_agent.tools.slack_tools.user_tools import list_slack_users, get_bot_user_id
        from lucident_agent.tools.slack_tools.channel_tools import list_slack_channels
    except ImportError as e:
        logger.error(f"Failed to import Slack tools: {e}")
        sys.exit(1)

    if args.refresh:
        refresh_slack_context(
            list_users_fn=list_slack_users,
            list_channels_fn=list_slack_channels,
            get_bot_id_fn=get_bot_user_id
        )
    else:
        save_slack_context(
            list_users_fn=list_slack_users,
            list_channels_fn=list_slack_channels,
            get_bot_id_fn=get_bot_user_id
        ) 