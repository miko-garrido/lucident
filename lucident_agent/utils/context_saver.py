import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from lucident_agent.tools.clickup_tools import get_workspace_structure, get_all_users
from lucident_agent.Database import Database
# from ..tools.gmail_tools import get_recent_contacts

db = Database().client

def format_users_markdown():
    users_data = get_all_users()
    lines = []
    for m in users_data["team"]["members"]:
        u = m["user"]
        lines.extend([
            f"*{u['username']}*",
            f"- email: {u['email']}",
            f"- id: {u['id']}",
            f"- role: {u['role_key']}"
            ""  # blank line between users
        ])
    return "\n".join(lines)

def format_workspace_structure_markdown():
    ws = get_workspace_structure().get("data", {}).get("spaces", [])
    lines = []
    for space in ws:
        lines.append(f"**{space['name']}** (_ID: {space['id']}) (Space)")
        lines.append("- *Folderless Lists*  ")
        flists = space.get("folderless_lists", [])
        if flists:
            for fl in flists:
                lines.append(f"  - **{fl['name']}** (_ID: {fl['id']}) (List)")
        else:
            lines.append("  - _None_")
        lines.append("- *Folders*  ")
        folders = space.get("folders", [])
        if folders:
            for folder in folders:
                lines.append(f"  - **{folder['name']}** (_ID: {folder['id']}) (Folder)")
                for lst in folder.get("lists", []):
                    lines.append(f"    - {lst['name']} (_ID: {lst['id']}) (List)")
        else:
            lines.append("  - _None_")
        lines.append("")  # blank line between spaces
    return "\n".join(lines)

def fetch_context_from_supabase(context_type, limit=1):
    result = db.table('saved_context') \
        .select('body') \
        .eq('type', context_type) \
        .order('"created_at"', desc=True) \
        .limit(limit) \
        .execute()
    
    return result.data[0]['body'] if result.data else f"Error: No {context_type} found"

def save_context():
    users_markdown = format_users_markdown()
    workspace_structure_markdown = format_workspace_structure_markdown()
    users_response = db.table("saved_context").insert({"type": "all_users", "body": users_markdown}).execute()
    workspace_structure_response = db.table("saved_context").insert({"type": "workspace_structure", "body": workspace_structure_markdown}).execute()
    print(users_response)
    print(workspace_structure_response)

if __name__ == "__main__":
    save_context()