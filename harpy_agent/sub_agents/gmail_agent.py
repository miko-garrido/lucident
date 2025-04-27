from config import Config
AGENT_MODEL = Config.MODEL_NAME

from google.adk.models.lite_llm import LiteLlm
from google.adk.agents import Agent
from google.genai import types
from dotenv import load_dotenv
from harpy_agent.tools.gmail_tools import (
    get_gmail_messages,
    search_by_from,
    search_by_subject,
    categorized_search_gmail,
    analyze_email_content,
    extract_email_metadata,
    add_new_gmail_account,
    list_gmail_accounts,
    search_gmail_with_query
)
from harpy_agent.tools.basic_tools import (
    get_current_time,
    calculate,
    calculate_date,
    calculate_many
)

load_dotenv()

MODEL_NAME = Config.MODEL_NAME
APP_NAME = Config.APP_NAME
USER_ID = Config.USER_ID
SESSION_ID = Config.SESSION_ID

# Create the agent instance
gmail_agent = Agent(
    name="gmail_agent",
    model=LiteLlm(model=MODEL_NAME),
    description=(
        "Manages and retrieves information from Gmail accounts, including emails, search, and account management. "
        "Checks accounts one by one and provides clear responses for each account."
    ),
    instruction=(
        "You are a specialized Gmail assistant. Your primary function is to interact with Gmail accounts using the provided tools. "
        "IMPORTANT: You must ALWAYS start by listing available accounts using list_gmail_accounts() before performing any other operations. "
        "After listing accounts, you can proceed with the following steps:"
        "1. For each account, make a SEPARATE tool call to get_gmail_messages() with the specific account_id"
        "2. Provide a clear summary for each account before moving to the next"
        "3. If an account has no emails or returns an error, clearly state that"
        "4. After checking all accounts, provide a final summary"
        "If list_gmail_accounts() returns no accounts, inform the user they need to add a Gmail account first. "
        "Focus solely on Gmail-related actions defined by your tools. Do not perform actions outside of Gmail management. "
        "IMPORTANT: You must wait for each tool call to complete before making the next one. Do not make multiple tool calls simultaneously."
    ),
    tools=[
        list_gmail_accounts,
        get_gmail_messages,
        search_by_from,
        search_by_subject,
        categorized_search_gmail,
        analyze_email_content,
        extract_email_metadata,
        add_new_gmail_account,
        search_gmail_with_query,
        get_current_time,
        calculate,
        calculate_date,
        calculate_many
    ]
)

# Export the agent
__all__ = ['gmail_agent']

# if __name__ == "__main__":
#     # First authenticate
#     auth_success = gmail_auth()
#     if auth_success:
#         # Initialize the agent
#         agent = main()
#         print("Agent initialized successfully")
#     else:
#         print("Authentication failed")
    
#     # Print a success message
#     print("\nGmail Agent successfully initialized!")
#     print("You can now ask questions like:")
#     print("- 'Show me my recent emails'")
#     print("- 'Find emails from john@example.com'")
#     print("- 'Search for emails with subject meeting'") 