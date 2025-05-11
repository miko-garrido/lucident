import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from lucident_agent.tools.figma_account_manager import FigmaAccountManager
from lucident_agent.Database import Database
import requests
import logging
from dotenv import load_dotenv
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
db = Database().client
figma_account_manager = FigmaAccountManager()

# Helper to get user info from Figma API
def get_figma_user_info(access_token):
    headers = {"X-Figma-Token": access_token}
    resp = requests.get("https://api.figma.com/v1/me", headers=headers)
    if resp.status_code == 200:
        return resp.json()
    return None

# Helper to get teams for a user (Figma API does not have a direct endpoint for all teams, so this is limited)
def get_figma_teams(access_token):
    # Figma API does not provide a /v1/teams endpoint for all teams a user belongs to
    # This is a placeholder for future expansion or if you have team IDs
    return []

# Helper to get projects for a team
def get_figma_projects(access_token, team_id):
    headers = {"X-Figma-Token": access_token}
    url = f"https://api.figma.com/v1/teams/{team_id}/projects"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json().get("projects", [])
    return []

def get_figma_files(project_id: str, access_token: str):
    """Helper to get files for a project."""
    headers = {"X-Figma-Token": access_token}
    url = f"https://api.figma.com/v1/projects/{project_id}/files"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json().get("files", [])
    return []

def format_figma_users_markdown():
    lines = []
    for user_id in figma_account_manager.get_all_account_ids():
        creds = figma_account_manager.get_account_credentials(user_id)
        access_token = creds.get("access_token")
        user_info = get_figma_user_info(access_token)
        if user_info:
            lines.append(f"*{user_info.get('handle', user_id)}*")
            lines.append(f"- id: {user_info.get('id', user_id)}")
            lines.append(f"- email: {user_info.get('email', 'N/A')}")
            lines.append("")
        else:
            lines.append(f"*{user_id}* (Could not fetch user info)")
            lines.append("")
    return "\n".join(lines)

def format_figma_projects_markdown():
    lines = []
    team_id = os.getenv('FIGMA_TEAM_ID')
    if not team_id:
        logger.warning("FIGMA_TEAM_ID not found in .env")
        return "No team ID configured"
        
    for user_id in figma_account_manager.get_all_account_ids():
        creds = figma_account_manager.get_account_credentials(user_id)
        access_token = creds.get("access_token")
        projects = get_figma_projects(access_token, team_id)
        lines.append(f"**Team {team_id}**")
        if projects:
            for proj in projects:
                lines.append(f"- **{proj.get('name')}** (_ID: {proj.get('id')}_)")
                files = get_figma_files(proj.get('id'), access_token)
                if files:
                    for file in files:
                        lines.append(f"  - [{file.get('name')}](https://www.figma.com/file/{file.get('key')}) (_ID: {file.get('key')}_)")
                else:
                    lines.append("  - _No files_")
        else:
            lines.append("- _No projects found_")
        lines.append("")
    return "\n".join(lines)

def fetch_figma_context_from_supabase(context_type: str):
    """Retrieve saved Figma context from Supabase."""
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

def save_figma_context():
    """Save Figma context to Supabase."""
    users_markdown = format_figma_users_markdown()
    projects_markdown = format_figma_projects_markdown()
    
    users_response = db.table("saved_context").insert({
        "type": "figma_users", 
        "body": users_markdown
    }).execute()
    
    projects_response = db.table("saved_context").insert({
        "type": "figma_projects", 
        "body": projects_markdown
    }).execute()
    
    logger.info(f"Saved {len(users_response.data)} Figma users record to Supabase")
    logger.info(f"Saved {len(projects_response.data)} Figma projects record to Supabase")

def refresh_figma_context():
    """Force refresh the Figma context in Supabase."""
    logger.info("Deleting existing Figma context data...")
    
    delete_projects = db.table("saved_context").delete().eq("type", "figma_projects").execute()
    delete_users = db.table("saved_context").delete().eq("type", "figma_users").execute()
    
    logger.info(f"Deleted {len(delete_projects.data)} project records")
    logger.info(f"Deleted {len(delete_users.data)} user records")
    
    logger.info("Saving fresh Figma context...")
    save_figma_context()
    logger.info("Done! Figma context has been refreshed in Supabase.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Save or refresh Figma context in Supabase')
    parser.add_argument('--refresh', action='store_true', help='Delete existing records before saving new ones')
    args = parser.parse_args()
    
    if args.refresh:
        refresh_figma_context()
    else:
        save_figma_context() 