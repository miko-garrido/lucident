import requests
from typing import Optional, Dict
from .figma_account_manager import FigmaAccountManager
import time
import os
from dotenv import load_dotenv

load_dotenv()

# --- Account Manager ---
figma_account_manager = FigmaAccountManager()

# --- Environment Variables ---
def get_access_token() -> Optional[str]:
    return os.getenv('FIGMA_PERSONAL_ACCESS_TOKEN')

def get_team_id() -> Optional[str]:
    return os.getenv('FIGMA_TEAM_ID')

# --- OAuth Helpers ---
def start_oauth_flow(client_id: str, client_secret: str, redirect_uri: str, scopes: str) -> str:
    """Return the URL to start the Figma OAuth flow."""
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': scopes,
        'response_type': 'code',
        'state': str(int(time.time()))
    }
    base_url = 'https://www.figma.com/oauth'
    return f"{base_url}?" + "&".join(f"{k}={v}" for k, v in params.items())

def exchange_code_for_token(client_id: str, client_secret: str, redirect_uri: str, code: str) -> Dict:
    """Exchange authorization code for access and refresh tokens."""
    url = 'https://www.figma.com/api/oauth/token'
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'code': code,
        'grant_type': 'authorization_code'
    }
    resp = requests.post(url, data=data)
    resp.raise_for_status()
    return resp.json()

def refresh_token(client_id: str, client_secret: str, refresh_token: str) -> Dict:
    url = 'https://www.figma.com/api/oauth/token'
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }
    resp = requests.post(url, data=data)
    resp.raise_for_status()
    return resp.json()

# --- Authentication & File Access ---
def get_headers(access_token: str):
    """Return headers for Figma API requests."""
    return {'X-Figma-Token': access_token}

def create_figma_link(file_id: str, node_id: Optional[str] = None) -> str:
    """
    Create a URL to a Figma file or node.
    
    Args:
        file_id (str): The Figma file ID
        node_id (Optional[str]): The node ID within the file, if applicable
        
    Returns:
        str: URL to the Figma file or node
    """
    base_url = f"https://www.figma.com/file/{file_id}"
    if node_id:
        return f"{base_url}?node-id={node_id}"
    return base_url

def fetch_file(file_id: str):
    """
    Fetch a Figma file with its metadata.
    
    Args:
        file_id (str): The Figma file ID
        
    Returns:
        dict: The file data with an added 'link' field
    """
    access_token = get_access_token()
    url = f'https://api.figma.com/v1/files/{file_id}'
    headers = get_headers(access_token)
    response = requests.get(url, headers=headers).json()
    
    # Add link to the file
    if 'err' not in response:
        response['link'] = create_figma_link(file_id)
    
    return response

def list_projects(team_id: str):
    """
    List all projects for a team.
    
    Args:
        team_id (str): The team ID
        
    Returns:
        dict: Projects data
    """
    access_token = get_access_token()
    url = f'https://api.figma.com/v1/teams/{team_id}/projects'
    headers = get_headers(access_token)
    return requests.get(url, headers=headers).json()

def list_files(project_id: str):
    """
    List all files in a project.
    
    Args:
        project_id (str): The project ID
        
    Returns:
        dict: Files data with added links
    """
    access_token = get_access_token()
    url = f'https://api.figma.com/v1/projects/{project_id}/files'
    headers = get_headers(access_token)
    response = requests.get(url, headers=headers).json()
    
    # Add links to each file
    if 'err' not in response and 'files' in response:
        for file in response['files']:
            if 'key' in file:
                file['link'] = create_figma_link(file['key'])
    
    return response

# --- Node Traversal ---
def traverse_nodes(node: dict, node_type: Optional[str] = None):
    """Recursively traverse nodes, optionally filtering by type."""
    pass

# --- Metadata & Text Extraction ---
def extract_metadata(node: dict):
    """Extract name, type, and properties from a node."""
    pass

def extract_text_and_styles(node: dict):
    """Extract text content, font styles, colors, spacing from a node."""
    pass

# --- Asset Export ---
def export_asset(access_token: str, file_id: str, node_id: str, format: str = 'png', scale: float = 1.0):
    """Export a node as PNG, JPG, or SVG at specified scale."""
    pass

# --- Comment Handling ---
def fetch_comments(file_id: str):
    """
    Fetch comments for a file.
    
    Args:
        file_id (str): The file ID
        
    Returns:
        dict: Comments data with added links
    """
    access_token = get_access_token()
    url = f'https://api.figma.com/v1/files/{file_id}/comments'
    headers = get_headers(access_token)
    response = requests.get(url, headers=headers).json()
    
    # Add links to each comment that references a node
    if 'err' not in response and 'comments' in response:
        for comment in response['comments']:
            if 'client_meta' in comment and comment['client_meta'] and 'node_id' in comment['client_meta']:
                node_id = comment['client_meta']['node_id']
                comment['link'] = create_figma_link(file_id, node_id)
            else:
                comment['link'] = create_figma_link(file_id)
    
    return response

def post_comment(access_token: str, file_id: str, message: str, node_id: Optional[str] = None):
    """Post a comment, optionally linked to a node."""
    pass

def resolve_comment(access_token: str, file_id: str, comment_id: str):
    """Resolve a comment by ID."""
    pass

# --- Design Versioning ---
def compare_versions(access_token: str, file_id: str, version_a: str, version_b: str):
    """Compare two versions of a file and log differences."""
    pass
