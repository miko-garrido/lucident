#!/usr/bin/env python3
"""
Gmail Agent

This is the main agent for Gmail functionality, built with Google's Agent Development Kit (ADK).
"""
from config import Config
AGENT_MODEL = Config.MODEL_NAME

from google.adk.models.lite_llm import LiteLlm
from google.adk.agents import Agent
from harpy_agent.tools.gmail_tools import (
    get_gmail_messages,
    search_by_from,
    search_by_subject,
    categorized_search_gmail,
    analyze_email_content,
    extract_email_metadata,
    add_gmail_account,
    list_gmail_accounts,
    search_gmail_with_query
)

gmail_agent = Agent(
    name="gmail_agent",
    model=LiteLlm(model=AGENT_MODEL),
    description=(
        "Agent to manage multiple Gmail accounts and answer questions about email"
    ),
    instruction=(
        "I can help with emails from multiple Gmail accounts, including reading, searching, and categorizing emails. "
        "\n\nAccount Management:"
        "\n- Add account: add_gmail_account(account_id)"
        "\n- List accounts: list_gmail_accounts()"
        "\n- Search across accounts: search_gmail_with_query(query, account_id=None)"
        "\n\nEmail Operations:"
        "\n- To get recent emails: Use get_gmail_messages(max_results=N) where N is the number of emails to retrieve"
        "\n- To search for emails from someone: Use search_by_from(sender, max_results=N)"
        "\n- To search for emails with a specific subject: Use search_by_subject(subject_text, max_results=N)"
        "\n- To search by category: Use categorized_search_gmail(category, max_results=N)"
        "\n- To analyze an email: Use analyze_email_content with the email ID"
        "\n- To extract metadata: Use extract_email_metadata with the email ID"
        "\n- To check deadlines: Use check_upcoming_deadlines()"
        "\n\nCRITICAL - Tool Call Handling:"
        "\n1. NEVER make multiple tool calls in parallel"
        "\n2. ALWAYS follow this sequence:"
        "\n   a. Make ONE tool call"
        "\n   b. Wait for the response"
        "\n   c. Process the response"
        "\n   d. Make the next tool call if needed"
    ),
    tools=[
        get_gmail_messages,
        search_by_from,
        search_by_subject,
        categorized_search_gmail,
        analyze_email_content,
        extract_email_metadata,
        add_gmail_account,
        list_gmail_accounts,
        search_gmail_with_query
    ]
)
    
#     return agent

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