#!/usr/bin/env python3
"""
Gmail Agent

This is the main agent for Gmail functionality, built with Google's Agent Development Kit (ADK).
"""

from google.adk.agents import Agent
from gmail_tools import (
    get_weather,
    get_current_time,
    get_gmail_messages,
    search_gmail,
    categorized_search_gmail,
    analyze_email_content,
    extract_email_metadata,
    gmail_auth
)

def main():
    """Initialize and return the Gmail agent."""
    
    agent = Agent(
        name="gmail_agent",
        model="gemini-1.5-flash",
        description=(
            "Agent to answer questions about email, time, and weather. Can also search and categorize emails."
        ),
        instruction=(
            "I can help with emails from your Gmail account, including reading, searching, and categorizing emails. "
            "I can search emails by categories (people, projects, tasks, attachments, meetings) and specific tags. "
            "I can extract structured metadata from emails to identify client, project name, task description, "
            "assignee, deadline, and deliverable information. "
            "I can also provide weather and time information."
        ),
        tools=[
            get_weather, 
            get_current_time, 
            get_gmail_messages, 
            search_gmail, 
            categorized_search_gmail, 
            analyze_email_content, 
            extract_email_metadata
        ],
    )
    
    return agent

if __name__ == "__main__":
    # Create the agent
    root_agent = main()
    
    # Print a success message
    print("\nGmail Agent successfully initialized!")
    print("You can now ask questions like:")
    print("- 'Show me my recent emails'")
    print("- 'Find emails from john@example.com'")
    print("- 'Search for emails with subject meeting'")
    print("- 'What time is it in New York?'")
    print("- 'What's the weather in New York?'") 