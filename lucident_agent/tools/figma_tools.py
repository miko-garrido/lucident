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

def fetch_file(file_id: str):
    access_token = get_access_token()
    url = f'https://api.figma.com/v1/files/{file_id}'
    headers = get_headers(access_token)
    return requests.get(url, headers=headers).json()

def list_projects(team_id: str):
    access_token = get_access_token()
    url = f'https://api.figma.com/v1/teams/{team_id}/projects'
    headers = get_headers(access_token)
    return requests.get(url, headers=headers).json()

def list_files(project_id: str):
    access_token = get_access_token()
    url = f'https://api.figma.com/v1/projects/{project_id}/files'
    headers = get_headers(access_token)
    return requests.get(url, headers=headers).json()

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
    """Fetch comments for a file."""
    access_token = get_access_token()
    url = f'https://api.figma.com/v1/files/{file_id}/comments'
    headers = get_headers(access_token)
    return requests.get(url, headers=headers).json()

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
