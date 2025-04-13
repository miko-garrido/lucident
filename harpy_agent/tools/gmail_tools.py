#!/usr/bin/env python3
"""
Gmail Tools Module

This module contains all the tools and authentication functionality for Gmail.
"""

import datetime
import os
import os.path
import sys
import json
import base64
import socket
import webbrowser
from zoneinfo import ZoneInfo
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from email.mime.text import MIMEText

# Define the scopes needed for Gmail API
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/calendar'
]

# Gmail authentication functions
def is_port_in_use(port):
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_free_port():
    """Find a free port to use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def gmail_auth(account_id="default"):
    """Authenticates with Gmail API and sets up credentials.
    
    Args:
        account_id (str, optional): ID of the Gmail account to use. Defaults to "default".
        
    Returns:
        bool: True if authentication was successful, False otherwise.
    """
    print(f"\n=== Gmail API Authentication Setup for {account_id} ===\n")
    
    # Define the token file name based on account ID
    token_file = f'token_{account_id}.json' if account_id != "default" else 'token.json'
    
    # Check if credentials.json exists
    if not os.path.exists('credentials.json'):
        print("ERROR: 'credentials.json' file not found!")
        print("\nFollow these steps to get your credentials.json file:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select an existing one")
        print("3. Go to 'APIs & Services' > 'Library'")
        print("4. Search for 'Gmail API' and enable it")
        print("5. Go to 'APIs & Services' > 'Credentials'")
        print("6. Click 'Create Credentials' > 'OAuth client ID'")
        print("7. Set Application type to 'Desktop application'")
        print("8. Name your client and click 'Create'")
        print("9. Download the JSON file and save it as 'credentials.json' in this directory")
        return False
    
    # Remove existing token if any
    if os.path.exists(token_file):
        os.remove(token_file)
        print(f"Removed existing {token_file} file for a fresh authentication.\n")
    
    try:
        # Allow insecure localhost
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        
        # Try each of these ports, in order
        ports_to_try = [8001, 8080, 8090, 8000]
        
        creds = None
        success = False
        
        for port in ports_to_try:
            if is_port_in_use(port):
                print(f"Port {port} is already in use, trying next port...")
                continue
                
            print(f"Using port {port}...")
            
            try:
                # Create the flow
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json',
                    SCOPES
                )
                
                print(f"Starting OAuth authentication flow on port {port}...")
                print("This will open a browser window for you to sign in to your Google account.")
                
                # Run the local server
                creds = flow.run_local_server(
                    port=port,
                    open_browser=True,
                    success_message="Authentication successful! You can close this window and return to the terminal.",
                    access_type='offline',
                    prompt='consent'
                )
                
                success = True
                break  # Found a working port and completed authentication
                
            except Exception as e:
                print(f"Error with port {port}: {e}")
                # Try the next port
                continue
        
        if not success:
            print("All ports failed. Trying a random free port...")
            
            try:
                # Find a random free port
                port = find_free_port()
                print(f"Using random free port: {port}")
                
                # Create the flow
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json',
                    SCOPES
                )
                
                print(f"Starting OAuth authentication flow on port {port}...")
                print("This will open a browser window for you to sign in to your Google account.")
                
                # Run the local server
                creds = flow.run_local_server(
                    port=port,
                    open_browser=True,
                    success_message="Authentication successful! You can close this window and return to the terminal.",
                    access_type='offline',
                    prompt='consent'
                )
                
                success = True
                
            except Exception as e:
                print(f"Error with random port {port}: {e}")
                success = False
        
        # Check if we got credentials
        if not success or not creds or not creds.refresh_token:
            print("\nWARNING: Did not receive valid credentials or refresh token!")
            print("This could happen if you've already authorized this app previously.")
            print("Please go to https://myaccount.google.com/permissions and revoke access")
            print("for this app, then run this script again.")
            return False
        
        # Save the credentials for future runs as properly formatted JSON
        with open(token_file, 'w') as token:
            token_data = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes,
                'expiry': creds.expiry.isoformat() if creds.expiry else None
            }
            json.dump(token_data, token)
        
        print("\nAuthentication successful!")
        print(f"Refresh token obtained: {bool(creds.refresh_token)}")
        print(f"Credentials saved to '{token_file}'\n")
        return True
        
    except Exception as e:
        print(f"\nError during authentication: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure your credentials.json is valid and downloaded directly from Google Cloud Console")
        print("2. Ensure your OAuth consent screen is configured properly")
        print("3. Make sure one of these redirect URIs is authorized in Google Cloud:")
        print("   - http://localhost:8001")
        print("   - http://localhost:8080")
        print("   - http://localhost:8000")
        print("   - http://localhost (without a port)")
        print("4. Try closing any browser windows that might be caching credentials")
        print("5. Go to https://myaccount.google.com/permissions and revoke access for this app, then try again")
        print("6. Check if your firewall is blocking localhost connections")
        return False

def get_gmail_service():
    """Authenticates with Gmail API and returns a service object.
        
    Returns:
        dict: Contains status, error message (if any), and service object (if successful).
    """
    # Use default account
    account_id = "default"
    
    # Check if token file exists for this account
    token_file = f'token_{account_id}.json' if account_id != "default" else 'token.json'
    
    if not os.path.exists(token_file):
        return {
            "status": "error",
            "error_message": f"Gmail authentication not set up for account {account_id}. Please run 'python gmail_tools.py auth {account_id}' to set up authentication."
        }
    
    try:
        # Load credentials from token file
        with open(token_file, 'r') as token:
            token_data = json.load(token)
            creds = Credentials.from_authorized_user_info(token_data)
        
        # If credentials expired, refresh them
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Update token file with refreshed credentials
            with open(token_file, 'w') as token:
                token_data = {
                    'token': creds.token,
                    'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri,
                    'client_id': creds.client_id,
                    'client_secret': creds.client_secret,
                    'scopes': creds.scopes,
                    'expiry': creds.expiry.isoformat() if creds.expiry else None
                }
                json.dump(token_data, token)
        
        # Build the Gmail service
        service = build('gmail', 'v1', credentials=creds)
        
        return {
            "status": "success",
            "service": service,
            "account": account_id
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error authenticating with Gmail for account {account_id}: {str(e)}"
        }

# Gmail functionality
def get_gmail_messages() -> dict:
    """Retrieves recent messages from Gmail.
        
    Returns:
        Result containing recent emails
    """
    # Set default values
    account_id = "default"
    max_results = 10
        
    # Get Gmail service for the specified account
    service_result = get_gmail_service()
    
    # Check if authentication was successful
    if service_result["status"] == "error":
        return service_result
    
    # Extract the service object
    service = service_result["service"]
    
    try:
        # Get emails
        results = service.users().messages().list(userId='me', maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return {
                "status": "success",
                "account": account_id,
                "report": f"No messages found for account {account_id}."
            }
        
        # Get details for each message
        email_data = []
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id'], format='metadata').execute()
            headers = msg['payload']['headers']
            
            # Extract subject, from, and date information
            subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No subject')
            sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'Unknown sender')
            date = next((header['value'] for header in headers if header['name'].lower() == 'date'), 'Unknown date')
            
            email_data.append({
                'id': message['id'],
                'subject': subject,
                'from': sender,
                'date': date,
                'snippet': msg.get('snippet', '')
            })
        
        return {
            "status": "success",
            "account": account_id,
            "report": f"Found {len(email_data)} emails",
            "emails": email_data
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error retrieving Gmail messages for account {account_id}: {str(e)}"
        }

# Helper to fix the parameter issue by providing an explicit parameter schema function
def search_gmail_with_query(query):
    """Searches Gmail for specific emails matching a query.
    
    Args:
        query (str): Search query (e.g. "from:example@gmail.com", "subject:meeting")
        
    Returns:
        dict: status and result containing email information or error message.
    """
    # Set defaults
    account_id = "default"
    max_results = 10
    
    # Call the implementation
    return _search_gmail_impl(query, account_id, max_results)
    
# Rename original function to implementation
def _search_gmail_impl(query, account_id, max_results):
    """Internal implementation of Gmail search.
    
    This is used by both the search_gmail and search_gmail_with_query functions.
    """
    # Get Gmail service for the specified account
    service_result = get_gmail_service()
    
    # Check if authentication was successful
    if service_result["status"] == "error":
        return service_result
    
    # Extract the service object
    service = service_result["service"]
    
    try:
        # Search for emails matching the query
        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return {
                "status": "success",
                "account": account_id,
                "report": f"No messages found matching query: '{query}'."
            }
        
        # Get details for each message
        email_data = []
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
            headers = msg['payload']['headers']
            
            # Extract subject, from, and date information
            subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No subject')
            sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'Unknown sender')
            date = next((header['value'] for header in headers if header['name'].lower() == 'date'), 'Unknown date')
            
            # Extract body content
            body = ""
            if 'parts' in msg['payload']:
                for part in msg['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        # Decode the base64 encoded message
                        body_data = part['body'].get('data', '')
                        if body_data:
                            body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                            break
            elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
                body_data = msg['payload']['body']['data']
                body = base64.urlsafe_b64decode(body_data).decode('utf-8')
            
            email_data.append({
                'id': message['id'],
                'subject': subject,
                'from': sender,
                'date': date,
                'snippet': msg.get('snippet', ''),
                'body': body[:500] + ('...' if len(body) > 500 else '')  # Truncate long messages
            })
        
        return {
            "status": "success",
            "account": account_id,
            "report": f"Found {len(email_data)} emails matching query: '{query}'",
            "emails": email_data
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error searching Gmail for account {account_id}: {str(e)}"
        }

# Replace the original search_gmail with the new clean version
search_gmail = search_gmail_with_query

def categorized_search_gmail(category: str) -> dict:
    """Searches Gmail for specific emails based on predefined categories.
    
    Args:
        category: Category to search for. Valid values: 'people', 'projects', 'tasks', 'attachments', 'meetings'
        
    Returns:
        Result containing matching emails
    """
    # Set default values
    tag = None
    max_results = 10
        
    # Define search queries based on categories and tags
    search_queries = {
        "people": {
            "client": "from:external OR \"we'd like\" OR \"can you send\"",
            "project_manager": "\"please align\" OR \"follow up with\"",
            "team_member": "sprint OR task OR technical"
        },
        "projects": {
            "project_name": "\"Project Neptune\" OR \"Website Redesign\" OR \"Campaign Q2\"",
            "project_phase": "kickoff OR discovery OR launch OR UAT OR handover"
        },
        "tasks": {
            "task_description": "\"can you update\" OR \"please revise\" OR \"we need to\"",
            "assigned_to": "\"can take care of\" OR \"let's have handle\"",
            "deadline": "by friday OR EOD OR \"by next week\"",
            "status_update": "\"just an update\" OR \"we've completed\" OR \"still pending\""
        },
        "attachments": {
            "deliverable": "has:attachment AND (attached OR \"latest draft\" OR mockup)",
            "reference_material": "has:attachment AND (brief OR scope OR requirements)"
        },
        "meetings": {
            "meeting_invite": "invite OR calendar OR meet OR zoom OR \"google meet\"",
            "schedule_change": "reschedule OR \"new time\" OR \"moved to next week\""
        }
    }
    
    # Validate category
    if category.lower() not in search_queries:
        return {
            "status": "error",
            "error_message": f"Invalid category: '{category}'. Valid categories are: {', '.join(search_queries.keys())}"
        }
    
    # Get category queries
    category_queries = search_queries[category.lower()]
    
    # Build the search query
    if tag:
        query = category_queries[tag.lower()]
    else:
        # If no specific tag, combine all queries for the category
        query = " OR ".join([f"({q})" for q in category_queries.values()])
    
    # Use the implementation directly
    results = _search_gmail_impl(query, "default", 10)
    
    # Add categorization info to the results
    if results["status"] == "success" and "emails" in results:
        if tag:
            results["category"] = category.lower()
            results["tag"] = tag.lower()
            results["search_criteria"] = query
        else:
            results["category"] = category.lower()
            results["search_criteria"] = query
    
    return results

def analyze_email_content(email_id: str) -> dict:
    """Analyzes the content of a specific email to extract relevant information.
    
    Args:
        email_id: ID of the email to analyze
        
    Returns:
        Result containing email analysis
    """
    # Set default values
    account_id = "default"
        
    # Get Gmail service for the specified account
    service_result = get_gmail_service()
    
    # Check if authentication was successful
    if service_result["status"] == "error":
        return service_result
    
    # Extract the service object
    service = service_result["service"]
    
    try:
        # Get the email
        msg = service.users().messages().get(userId='me', id=email_id, format='full').execute()
        headers = msg['payload']['headers']
        
        # Extract subject, from, and body
        subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No subject')
        sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'Unknown sender')
        
        # Extract body content
        body = ""
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body_data = part['body'].get('data', '')
                    if body_data:
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        break
        elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
            body_data = msg['payload']['body']['data']
            body = base64.urlsafe_b64decode(body_data).decode('utf-8')
        
        # Analyze the content for categories
        full_content = f"{subject} {sender} {body}"
        full_content = full_content.lower()
        
        # Define category detection patterns
        patterns = {
            "people": {
                "client": ["we'd like", "can you send", "@external.com", "@client.com"],
                "project_manager": ["please align", "follow up with", "project timeline", "project plan"],
                "team_member": ["sprint", "task", "technical", "issue", "bug"]
            },
            "projects": {
                "project_name": ["project neptune", "website redesign", "campaign q2"],
                "project_phase": ["kickoff", "discovery", "launch", "uat", "handover"]
            },
            "tasks": {
                "task_description": ["can you update", "please revise", "we need to", "action required"],
                "assigned_to": ["can take care of", "let's have", "handle", "assigned to"],
                "deadline": ["by friday", "eod", "end of day", "by next week", "due date"],
                "status_update": ["just an update", "we've completed", "still pending", "progress"]
            },
            "attachments": {
                "deliverable": ["attached", "latest draft", "mockup", "delivery"],
                "reference_material": ["brief", "scope", "requirements", "specification"]
            },
            "meetings": {
                "meeting_invite": ["invite", "calendar", "meet", "zoom", "google meet", "teams"],
                "schedule_change": ["reschedule", "new time", "moved to next week", "postponed"]
            }
        }
        
        # Identify matches
        matches = {}
        for category, tags in patterns.items():
            category_matches = []
            for tag, keywords in tags.items():
                for keyword in keywords:
                    if keyword in full_content:
                        category_matches.append(tag)
                        break
            if category_matches:
                matches[category] = list(set(category_matches))
        
        if not matches:
            return {
                "status": "success",
                "account": account_id,
                "report": "Email analyzed but no specific categories detected",
                "email_id": email_id
            }
        
        return {
            "status": "success",
            "account": account_id,
            "report": "Email successfully analyzed",
            "email_id": email_id,
            "categories": matches,
            "subject": subject,
            "from": sender
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error analyzing email for account {account_id}: {str(e)}"
        }

def extract_email_metadata(email_id: str) -> dict:
    """Extracts structured metadata from an email.
    
    Args:
        email_id: ID of the email to extract metadata from
        
    Returns:
        Result containing email metadata
    """
    # Set default values
    account_id = "default"
        
    # Get Gmail service for the specified account
    service_result = get_gmail_service()
    
    # Check if authentication was successful
    if service_result["status"] == "error":
        return service_result
    
    # Extract the service object
    service = service_result["service"]
    
    try:
        # Get the email
        msg = service.users().messages().get(userId='me', id=email_id, format='full').execute()
        headers = msg['payload']['headers']
        
        # Extract subject, from, and body
        subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No subject')
        sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'Unknown sender')
        
        # Check if the email has attachments
        has_attachment = False
        attachment_info = []
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if 'filename' in part and part['filename']:
                    has_attachment = True
                    attachment_info.append(part['filename'])
        
        # Extract body content
        body = ""
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body_data = part['body'].get('data', '')
                    if body_data:
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        break
        elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
            body_data = msg['payload']['body']['data']
            body = base64.urlsafe_b64decode(body_data).decode('utf-8')
        
        # Create the full content for analysis
        full_content = f"{subject} {sender} {body}"
        full_content = full_content.lower()
        
        # Initialize structured metadata dictionary
        metadata = {}
        
        # Extract client/sender
        if '@external.com' in sender.lower() or '@client.com' in sender.lower():
            sender_name = sender.split('<')[0].strip() if '<' in sender else sender
            metadata['client'] = sender_name
        
        # Extract project name
        project_keywords = ["project neptune", "website redesign", "campaign q2"]
        for keyword in project_keywords:
            if keyword in full_content:
                metadata['project_name'] = keyword.title()
                break
        
        # Extract task description
        task_indicators = ["update", "revise", "create", "design", "implement", "fix", "develop"]
        for indicator in task_indicators:
            if indicator in full_content.lower():
                # Try to extract a phrase around the indicator
                start_idx = full_content.lower().find(indicator)
                if start_idx >= 0:
                    # Look for a noun phrase after the indicator
                    context = full_content[start_idx:start_idx + 50]  # Get some context after the indicator
                    words = context.split()
                    task = " ".join(words[:min(5, len(words))])  # Take first 5 words max
                    metadata['task_description'] = task.capitalize()
                    break
        
        # Extract assigned to
        assignee_patterns = ["assigned to", "please have", "can you", "team should", "team will"]
        for pattern in assignee_patterns:
            if pattern in full_content:
                # Try to find who it's assigned to
                start_idx = full_content.find(pattern) + len(pattern)
                if start_idx >= 0:
                    context = full_content[start_idx:start_idx + 30]  # Get some context after the pattern
                    words = context.split()
                    assignee = " ".join(words[:min(3, len(words))])  # Take first 3 words max
                    metadata['assigned_to'] = assignee.strip()
                    break
        
        # Extract deadline
        deadline_patterns = ["by friday", "by monday", "eod", "end of day", "due by", "due date", 
                           "deadline", "by next week", "by tomorrow"]
        for pattern in deadline_patterns:
            if pattern in full_content:
                if "friday" in pattern:
                    metadata['deadline'] = "Friday"
                elif "monday" in pattern:
                    metadata['deadline'] = "Monday"
                elif "tomorrow" in pattern:
                    metadata['deadline'] = "Tomorrow"
                elif "eod" in pattern or "end of day" in pattern:
                    metadata['deadline'] = "End of Day"
                elif "next week" in pattern:
                    metadata['deadline'] = "Next Week"
                else:
                    # Try to extract the specific deadline mentioned
                    start_idx = full_content.find(pattern) + len(pattern)
                    if start_idx >= 0:
                        context = full_content[start_idx:start_idx + 20]
                        words = context.split()
                        deadline_text = " ".join(words[:min(3, len(words))])
                        metadata['deadline'] = deadline_text.strip().capitalize()
                break
        
        # Extract deliverable info
        if has_attachment:
            attachment_names = ", ".join(attachment_info)
            metadata['deliverable'] = f"Attachment: {attachment_names}"
        
        deliverable_patterns = ["latest draft", "mockup", "design", "document", "report", "presentation"]
        for pattern in deliverable_patterns:
            if pattern in full_content and 'deliverable' not in metadata:
                metadata['deliverable'] = pattern.capitalize()
                break
        
        if not metadata:
            return {
                "status": "success",
                "account": account_id,
                "report": "No specific metadata could be extracted from this email",
                "email_id": email_id,
                "subject": subject,
                "from": sender
            }
        
        return {
            "status": "success",
            "account": account_id,
            "report": "Successfully extracted email metadata",
            "email_id": email_id,
            "subject": subject,
            "from": sender,
            "metadata": metadata
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error extracting email metadata for account {account_id}: {str(e)}"
        }

# Simplest possible function with explicit parameter and type annotation
def search_by_from(sender: str) -> dict:
    """Search for emails from a specific sender.
    
    Args:
        sender: Email address to search for
        
    Returns:
        Result containing matching emails
    """
    query = f"from:{sender}"
    return _search_gmail_impl(query, "default", 10)
    
# Simplest possible function with explicit parameter and type annotation
def search_by_subject(subject_text: str) -> dict:
    """Search for emails with specific text in the subject.
    
    Args:
        subject_text: Text to search for in subject
        
    Returns:
        Result containing matching emails
    """
    query = f"subject:{subject_text}"
    return _search_gmail_impl(query, "default", 10)

# Main function to run from command line
if __name__ == "__main__":
    import sys
    
    # Check if we have command line arguments
    if len(sys.argv) < 2:
        print("Usage: python gmail_tools.py auth [account_id]")
        sys.exit(1)
    
    # Check for auth command
    if sys.argv[1] == "auth":
        # Get account ID if provided
        account_id = sys.argv[2] if len(sys.argv) > 2 else "default"
        
        # Run the authentication flow
        success = gmail_auth(account_id)
        
        if success:
            print(f"Your agent is now ready to access Gmail for account '{account_id}'!")
            print("\nYou can now ask questions like:")
            print("- 'Show me my recent emails'")
            print("- 'Find emails from john@example.com'")
            print("- 'Search for emails with subject meeting'")
            sys.exit(0)
        else:
            print("\nFailed to set up Gmail API authentication.")
            print("Please address the issues mentioned above and try again.")
            sys.exit(1)
    else:
        print("Unknown command. Available commands:")
        print("  auth [account_id] - Set up Gmail authentication for the specified account")
        sys.exit(1) 