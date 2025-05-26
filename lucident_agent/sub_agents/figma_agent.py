from google.adk.agents import Agent
from ..adk_patch.lite_llm_patched import LiteLlm
from dotenv import load_dotenv
import os
from lucident_agent.tools import figma_tools
from lucident_agent.tools.basic_tools import (
    get_current_time,
    calculate,
    calculate_date,
    convert_ms_to_hhmmss,
    convert_datetime_to_unix
)
from typing import Optional
from lucident_agent.utils.figma_context_saver import fetch_figma_context_from_supabase

load_dotenv()

# Load saved context
figma_users = fetch_figma_context_from_supabase("figma_users")
figma_projects = fetch_figma_context_from_supabase("figma_projects")

# Wrappers to inject per-user Figma OAuth token
def fetch_file_wrapper(file_id: str):
    return figma_tools.fetch_file(file_id)

def list_projects_wrapper(team_id: Optional[str] = None):
    if team_id is None:
        team_id = figma_tools.get_team_id()
    return figma_tools.list_projects(team_id)

def list_files_wrapper(project_id: str):
    return figma_tools.list_files(project_id)

def traverse_nodes_wrapper(node: dict, node_type: Optional[str] = None):
    return figma_tools.traverse_nodes(node, node_type)

def extract_metadata_wrapper(node: dict):
    return figma_tools.extract_metadata(node)

def extract_text_and_styles_wrapper(node: dict):
    return figma_tools.extract_text_and_styles(node)

def export_asset_wrapper(file_id: str, node_id: str, format: str = 'png', scale: float = 1.0):
    return figma_tools.export_asset(file_id, node_id, format, scale)

def fetch_comments_wrapper(file_id: str):
    return figma_tools.fetch_comments(file_id)

def post_comment_wrapper(file_id: str, message: str, node_id: Optional[str] = None):
    return figma_tools.post_comment(file_id, message, node_id)

def resolve_comment_wrapper(file_id: str, comment_id: str):
    return figma_tools.resolve_comment(file_id, comment_id)

def compare_versions_wrapper(file_id: str, version_a: str, version_b: str):
    return figma_tools.compare_versions(file_id, version_a, version_b)

def fetch_project_details_wrapper(project_id: str):
    return figma_tools.fetch_project_details(project_id)

def fetch_project_comments_wrapper(project_id: str, limit: int = 5):
    return figma_tools.fetch_project_comments(project_id, limit)

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "openai/gpt-4.1")

figma_agent = Agent(
    name="figma_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    description=f"""
    You are a specialized Figma assistant. Your primary function is to interact with the Figma API using the provided tools
    to manage and retrieve information about files, projects, nodes, comments, and assets. Use the user's Figma OAuth token for authentication.
    Focus solely on Figma-related actions defined by your tools. Do not perform actions outside of Figma management.
    
    Current Figma Context:
    Users:
    {figma_users if figma_users else "No user data available"}
    
    Projects and Files:
    {figma_projects if figma_projects else "No project data available"}
    """,
    tools=[
        fetch_file_wrapper,
        list_projects_wrapper,
        list_files_wrapper,
        fetch_project_details_wrapper,
        traverse_nodes_wrapper,
        extract_metadata_wrapper,
        extract_text_and_styles_wrapper,
        export_asset_wrapper,
        fetch_comments_wrapper,
        fetch_project_comments_wrapper,
        post_comment_wrapper,
        resolve_comment_wrapper,
        compare_versions_wrapper,
        get_current_time,
        calculate,
        calculate_date,
        convert_ms_to_hhmmss,
        convert_datetime_to_unix
    ]
)

__all__ = ["figma_agent"]
