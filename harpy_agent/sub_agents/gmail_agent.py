#!/usr/bin/env python3
"""
Gmail Agent

This is the main agent for Gmail functionality, built with Google's Agent Development Kit (ADK).
"""

# 123

from google.adk.agents import Agent
from harpy_agent.tools.gmail_tools import (
    get_gmail_messages,
    search_gmail,
    categorized_search_gmail,
    analyze_email_content,
    extract_email_metadata,
    gmail_auth
)

gmail_agent = Agent(
    name="gmail_agent",
    model="gemini-1.5-flash",
    description=(
        "Agent to answer questions about email. Can also search and categorize emails."
    ),
    instruction=(
        "I can help with emails from your Gmail account, including reading, searching, and categorizing emails. "
        "I can search emails by categories (people, projects, tasks, attachments, meetings) and specific tags. "
        "I can extract structured metadata from emails to identify client, project name, task description, "
        "assignee, deadline, and deliverable information."
    ),
    tools=[
        get_gmail_messages, 
        search_gmail, 
        categorized_search_gmail, 
        analyze_email_content, 
        extract_email_metadata
    ],
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