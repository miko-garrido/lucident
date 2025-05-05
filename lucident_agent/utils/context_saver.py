from ..tools.clickup_tools import get_workspace_structure, get_all_users
# from ..tools.gmail_tools import get_recent_contacts

def get_context():
    workspace_structure = get_workspace_structure()
    all_users = get_all_users()
    return workspace_structure, all_users

def convert_json_to_markdown():
    pass

def save_to_supabase():
    pass

def main():
    pass

if __name__ == "__main__":
    main()