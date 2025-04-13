#!/usr/bin/env python3
"""
Test script to verify root_agent can connect to gmail_agent
"""
import os
import sys
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from harpy_agent.agent import root_agent

def test_gmail_connection():
    # Set up a basic ADK runtime environment
    APP_NAME = "harpy_test"
    USER_ID = "test_user"
    SESSION_ID = "test_session"

    # Create services and runner
    session_service = InMemorySessionService()
    session = session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

    # Test query about emails to trigger gmail_agent
    query = "Show me my recent emails"
    content = types.Content(role='user', parts=[types.Part(text=query)])
    
    print(f"Sending query: '{query}'")
    print("This should be routed to the gmail_agent sub-agent...")
    
    # Run the agent and capture events
    events = runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)
    
    # Process events to see the agent's response
    for event in events:
        if hasattr(event, 'content') and hasattr(event.content, 'parts'):
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    print(f"Agent response: {part.text}")
                elif hasattr(part, 'functionCall'):
                    print(f"Function call: {part.functionCall.name}")
                elif hasattr(part, 'functionResponse'):
                    print(f"Function response from: {part.functionResponse.name}")
                    if hasattr(part.functionResponse, 'response'):
                        print(f"Response: {part.functionResponse.response}")

if __name__ == "__main__":
    test_gmail_connection()
