# harpy





# Gmail Agent

An intelligent agent built with Google's Agent Development Kit (ADK) that provides access to Gmail, weather information, and time.

## Features

- Retrieve and search Gmail messages
- Search emails by categories (people, projects, tasks, attachments, meetings)
- Analyze email content and extract metadata
- Get weather information for specific cities
- Get current time for specific locations

## Setup

1. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

2. Set up Gmail API credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Gmail API:
     - Go to "APIs & Services" > "Library"
     - Search for "Gmail API" and click on it
     - Click "Enable"
   - Create OAuth credentials:
     - Go to "APIs & Services" > "Credentials"
     - Click "Create Credentials" > "OAuth client ID"
     - Set Application type to "Desktop application" 
     - Name your client and click "Create"
     - Download the JSON file and save it as `credentials.json` in the project root

3. Authenticate with Gmail:
   ```
   python3 gmail_tools.py auth
   ```

4. Start the ADK API server:
   ```
   adk api_server --port 8001
   ```

5. Open a new terminal and send a query:
   ```
   curl -X POST http://localhost:8001/run \
   -H "Content-Type: application/json" \
   -d '{
     "app_name": "gmail_agent",
     "user_id": "u_123",
     "session_id": "s_123",
     "new_message": {
       "role": "user",
       "parts": [{
         "text": "Show me my recent emails"
       }]
     }
   }'
   ```

## Example Queries

- "What is the weather in New York?"
- "What time is it in New York?"
- "Show me my recent emails"
- "Find emails from john@example.com"
- "Search for emails with subject meeting"
- "Find emails in the projects category"
- "Analyze email content for [email_id]"
- "Extract metadata from email [email_id]"

## Gmail Search Query Syntax

The Gmail API supports advanced search operators:

- `from:sender` - Emails from a specific sender
- `to:recipient` - Emails to a specific recipient
- `subject:topic` - Emails with specific words in the subject
- `has:attachment` - Emails with attachments
- `is:unread` - Unread emails