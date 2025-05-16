"""
Slack agent module.

This module provides the main Slack agent for the Lucident system.
"""

from google.adk.agents import Agent
# from google.adk.models.lite_llm import LiteLlm  # Original ADK import
from ..adk_patch.lite_llm_patched import LiteLlm  # Using patched ADK LiteLlm for parallel tool calls fix
from google.genai import types
from dotenv import load_dotenv
from lucident_agent.config import Config
from lucident_agent.tools.slack_tools import (
    get_bot_user_id,
    get_slack_bot_info,
    send_slack_message,
    get_slack_channel_history,
    get_slack_thread_replies,
    list_slack_channels,
    list_slack_users,
    update_slack_message,
    extract_promises_from_text,
    extract_promises_from_slack_history,
    get_file_info,
    list_files_in_channel,
    list_files_in_thread,
    get_document_text,
    download_file_content
)
from lucident_agent.tools.basic_tools import (
    get_current_time,
    calculate,
    calculate_date,
    convert_ms_to_hhmmss
)
from lucident_agent.utils.context_saver import fetch_context_from_supabase
import logging

load_dotenv()

OPENAI_MODEL = Config.OPENAI_MODEL
GEMINI_MODEL = Config.GEMINI_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetch Slack context from Supabase
slack_users = fetch_context_from_supabase("slack_users")
slack_channels = fetch_context_from_supabase("slack_channels")

# Create the Slack agent instance
slack_agent = Agent(
    name="slack_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    #model=GEMINI_MODEL,
    description="A Slack assistant that can read and respond to messages in channels",
    instruction=f"""
    I am a Slack assistant that can read and respond to messages in Slack channels.
    I can send messages, read message history, get thread replies, and list available channels.
    
    To use me effectively:
    1. Mention me in a channel (@slack_agent)
    2. Ask me to perform an action related to Slack
    3. I'll respond with the requested information or confirmation of the action
    
    I have access to the following Slack functionality:
    - Get bot information including user ID
    - Send messages to channels
    - Get channel message history
    - Get thread replies
    - List available channels (using cached data from Supabase when available)
    - List workspace users (using cached data from Supabase when available)
    - Update existing messages
    - Extract promises or commitments from messages
    - Detect and process documents shared in Slack conversations
    
    When listing channels or users, I'll first check Supabase for cached information.
    If available, I'll return the cached markdown-formatted data.
    Otherwise, I'll fetch the data directly from the Slack API.
    
    I can identify and extract commitments or promises from messages. A promise is any statement 
    where someone commits to a future action, such as "I'll send you the report tomorrow" or 
    "Let me get back to you next week."
    
    I can also detect, list, and read documents/files shared in Slack conversations. This includes:
    - Detecting when documents are shared in a channel or thread
    - Getting information about a specific file
    - Listing all files in a channel or thread
    - Reading and extracting the text content from documents (when possible)
    - Processing PDF documents, including scanned PDFs with OCR capabilities
    - Reading text from images using OCR technology
    - Downloading file content for processing
    
    For PDFs, I can extract text both from regular machine-readable PDFs and from scanned documents 
    using Optical Character Recognition (OCR). For scanned documents or images of text, I'll attempt 
    to recognize and extract the text using OCR. However, the quality of OCR results depends on the 
    document quality and clarity.
    
    I also have general utility tools for time, date calculations, and basic arithmetic.
    
    Below is the list of all users in the workspace:
    ```
    {slack_users}
    ```
    
    Below is the list of all channels in the workspace:
    ```
    {slack_channels}
    ```
    """,
    tools=[
        # Slack tools
        get_slack_bot_info,
        send_slack_message,
        get_slack_channel_history,
        get_slack_thread_replies,
        list_slack_channels,
        list_slack_users,
        update_slack_message,
        extract_promises_from_text,
        extract_promises_from_slack_history,
        
        # Document handling tools
        get_file_info,
        list_files_in_channel,
        list_files_in_thread,
        get_document_text,
        download_file_content,
        
        # Basic tools
        get_current_time,
        calculate,
        calculate_date,
        convert_ms_to_hhmmss
    ]
)

# Export the agent instance
__all__ = ['slack_agent'] 