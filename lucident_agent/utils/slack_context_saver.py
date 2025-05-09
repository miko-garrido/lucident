import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from lucident_agent.tools.slack_tools import (
    list_slack_users, 
    list_slack_channels, 
    get_bot_user_id, 
    get_slack_bot_info,
    get_slack_context_from_supabase
)
from lucident_agent.Database import Database
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database().client

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
            f"*{user['name']}*",
            f"- id: {user['id']}",
            f"- real_name: {user['real_name']}",
            f"- email: {user['email']}",
            f"- is_bot: {user['is_bot']}",
            f"- is_admin: {user['is_admin']}",
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
            lines.append(f"- **{channel['name']}** (_ID: {channel['id']})")
            lines.append(f"  - members: {channel['num_members']}")
            lines.append(f"  - archived: {channel['is_archived']}")
    else:
        lines.append("- _None_")
    
    # Then list private channels
    lines.append("\n*Private Channels*")
    private_channels = [c for c in channels_data.get("channels", []) if c.get("is_private", False)]
    if private_channels:
        for channel in private_channels:
            lines.append(f"- **{channel['name']}** (_ID: {channel['id']})")
            lines.append(f"  - members: {channel['num_members']}")
            lines.append(f"  - archived: {channel['is_archived']}")
    else:
        lines.append("- _None_")
    
    return "\n".join(lines)

def main():
    """
    Main function to save Slack context to Supabase
    """
    # Format the data
    users_markdown = format_slack_users_markdown()
    channels_markdown = format_slack_channels_markdown()
    
    # Save to Supabase
    users_response = db.table("saved_context").insert({
        "type": "slack_users", 
        "body": users_markdown
    }).execute()
    
    channels_response = db.table("saved_context").insert({
        "type": "slack_channels", 
        "body": channels_markdown
    }).execute()
    
    logger.info(f"Saved {len(users_response.data)} Slack users record to Supabase")
    logger.info(f"Saved {len(channels_response.data)} Slack channels record to Supabase")

if __name__ == "__main__":
    main() 