import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from lucident_agent.tools.figma_account_manager import FigmaAccountManager
from lucident_agent.Database import Database
import requests
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    for user_id in figma_account_manager.get_all_account_ids():
        creds = figma_account_manager.get_account_credentials(user_id)
        access_token = creds.get("access_token")
        # You must provide team IDs manually or store them somewhere
        # Example: team_ids = ["your_team_id1", "your_team_id2"]
        team_ids = creds.get("team_ids", [])
        for team_id in team_ids:
            projects = get_figma_projects(access_token, team_id)
            lines.append(f"**Team {team_id}**")
            if projects:
                for proj in projects:
                    lines.append(f"- {proj.get('name')} (_ID: {proj.get('id')})")
            else:
                lines.append("- _No projects found_")
            lines.append("")
    return "\n".join(lines)

def save_figma_context():
    users_markdown = format_figma_users_markdown()
    projects_markdown = format_figma_projects_markdown()
    users_response = db.table("saved_context").insert({"type": "figma_users", "body": users_markdown}).execute()
    projects_response = db.table("saved_context").insert({"type": "figma_projects", "body": projects_markdown}).execute()
    print(users_response)
    print(projects_response)

if __name__ == "__main__":
    # Try all accounts first
    if figma_account_manager.get_all_account_ids():
        save_figma_context()
    else:
        # Try FIGMA_PERSONAL_ACCESS_TOKEN from .env
        token = os.getenv("FIGMA_PERSONAL_ACCESS_TOKEN")
        if token:
            info = get_figma_user_info(token)
            print("FIGMA_PERSONAL_ACCESS_TOKEN user info:", info)
        else:
            print("No Figma account or FIGMA_PERSONAL_ACCESS_TOKEN found.") 