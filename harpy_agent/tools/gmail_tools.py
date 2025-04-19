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
from .gmail_account_manager import GmailAccountManager

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

def get_gmail_service(account_id=None):
    """Get Gmail service for specified account"""
    if not account_id:
        account_id = "default"
        
    token_file = 'gmail_tokens.json'
    
    try:
        # Load all credentials from consolidated token file
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                all_tokens = json.load(f)
        else:
            all_tokens = {}
            
        if account_id not in all_tokens:
            return {
                "status": "error",
                "error_message": f"Gmail authentication not set up for account {account_id}. Please run 'python gmail_tools.py auth {account_id}' to set up authentication."
            }
            
        # Load credentials for specific account
        creds = Credentials.from_authorized_user_info(all_tokens[account_id])
        
        # If credentials expired, refresh them
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Update token file with refreshed credentials
            all_tokens[account_id] = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes,
                'expiry': creds.expiry.isoformat() if creds.expiry else None
            }
            with open(token_file, 'w') as f:
                json.dump(all_tokens, f, indent=2)
        
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

def gmail_auth(account_id="default"):
    """Authenticates with Gmail API and sets up credentials.
    
    Args:
        account_id (str, optional): ID of the Gmail account to use. Defaults to "default".
        
    Returns:
        bool: True if authentication was successful, False otherwise.
    """
    print(f"\n=== Gmail API Authentication Setup for {account_id} ===\n")
    
    token_file = 'gmail_tokens.json'
    
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
    
    # Load existing tokens if any
    if os.path.exists(token_file):
        with open(token_file, 'r') as f:
            all_tokens = json.load(f)
    else:
        all_tokens = {}
    
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
                continue
        
        if not success:
            print("All ports failed. Trying a random free port...")
            port = find_free_port()
            print(f"Using random free port: {port}")
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json',
                    SCOPES
                )
                
                print(f"Starting OAuth authentication flow on port {port}...")
                print("This will open a browser window for you to sign in to your Google account.")
                
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
        
        # Save the credentials for this account
        all_tokens[account_id] = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes,
            'expiry': creds.expiry.isoformat() if creds.expiry else None
        }
        
        # Save all tokens to file
        with open(token_file, 'w') as f:
            json.dump(all_tokens, f, indent=2)
        
        print("\nAuthentication successful!")
        print(f"Refresh token obtained: {bool(creds.refresh_token)}")
        print(f"Credentials saved to '{token_file}' for account '{account_id}'\n")
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

# Gmail functionality
def get_gmail_messages(max_results: int = 10, account_id: str = "") -> dict:
    """Retrieves recent messages from Gmail.
    
    Args:
        max_results (int, optional): Maximum number of emails to retrieve. Defaults to 10.
        account_id (str, optional): Specific account to retrieve from. If empty, retrieves from all accounts.
        
    Returns:
        Result containing recent emails
    """
    account_manager = GmailAccountManager()
    
    # If account_id is specified, get messages only from that account
    if account_id:
        service_result = get_gmail_service(account_id)
        if service_result["status"] == "error":
            return service_result
            
        service = service_result["service"]
        try:
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
    
    # Otherwise get messages from all accounts
    all_results = []
    accounts = list(account_manager.get_accounts().keys())
    
    for acc in accounts:
        result = get_gmail_messages(max_results, acc)
        if result["status"] == "success":
            all_results.append(result)
    
    return {
        "status": "success",
        "results": all_results,
        "accounts_searched": accounts
    }

# Helper to fix the parameter issue by providing an explicit parameter schema function
def search_gmail_with_query(query: str = "", account_id: str = "", max_results: int = 10):
    """Search Gmail across specified or all accounts.
    
    Args:
        query: Gmail search query string. If empty, returns most recent emails.
        account_id: Specific account ID to search. If empty, searches all accounts.
        max_results: Maximum number of results to return.
    """
    if not query:
        return get_gmail_messages(max_results, account_id)
    
    account_manager = GmailAccountManager()
    
    # If account_id is specified, search only that account
    if account_id:
        result = _search_gmail_impl(query, account_id, max_results)
        return {
            "status": "success", 
            "results": [result] if result["status"] == "success" else [],
            "accounts_searched": [account_id]
        }
    
    # Otherwise search all accounts sequentially and combine results
    all_emails = []
    accounts_searched = []
    accounts_with_results = []
    accounts = list(account_manager.get_accounts().keys())
    
    for acc in accounts:
        result = _search_gmail_impl(query, acc, max_results)
        if result["status"] == "success":
            accounts_searched.append(acc)
            if "emails" in result and result["emails"]:
                all_emails.extend(result["emails"])
                accounts_with_results.append(acc)
    
    # Sort emails by date (most recent first)
    all_emails.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    # Limit total results to max_results
    all_emails = all_emails[:max_results]
    
    return {
        "status": "success",
        "report": f"Found {len(all_emails)} emails matching query: '{query}' across {len(accounts_with_results)} accounts",
        "emails": all_emails,
        "accounts_searched": accounts_searched,
        "accounts_with_results": accounts_with_results,
        "total_accounts": len(accounts)
    }

# Rename original function to implementation
def _search_gmail_impl(query, account_id, max_results):
    """Internal implementation of Gmail search with smart fallback strategies.
    
    This is used by both the search_gmail and search_gmail_with_query functions.
    """
    # Get Gmail service for the specified account
    service_result = get_gmail_service(account_id)
    
    # Check if authentication was successful
    if service_result["status"] == "error":
        return service_result
    
    # Extract the service object
    service = service_result["service"]
    
    try:
        # Try different search strategies in order of specificity
        search_strategies = [
            # Strategy 1: Exact match in all fields
            f"(subject:{query} OR from:{query} OR {query})",
            
            # Strategy 2: Split into words and search each
            " OR ".join([f'"{word}"' for word in query.split()]),
            
            # Strategy 3: Try email-like patterns
            f"(from:*{query}* OR {query}@*)",
            
            # Strategy 4: Try name variations (first name, last name)
            " OR ".join([
                f'"{word}"' for word in query.split()
                if len(word) > 2  # Only use words longer than 2 chars
            ])
        ]
        
        all_messages = []
        tried_strategies = []
        
        for search_query in search_strategies:
            try:
                results = service.users().messages().list(
                    userId='me', 
                    q=search_query, 
                    maxResults=max_results
                ).execute()
                
                messages = results.get('messages', [])
                if messages:
                    all_messages.extend(messages)
                    tried_strategies.append(search_query)
                    
                    # If we found enough results, stop trying more strategies
                    if len(all_messages) >= max_results:
                        break
                        
            except Exception:
                continue
        
        # Remove duplicates while preserving order
        seen_ids = set()
        unique_messages = []
        for msg in all_messages:
            if msg['id'] not in seen_ids:
                seen_ids.add(msg['id'])
                unique_messages.append(msg)
        
        if not unique_messages:
            return {
                "status": "success",
                "account": account_id,
                "report": f"No messages found matching query: '{query}' after trying multiple search strategies.",
                "tried_strategies": tried_strategies
            }
        
        # Get details for each message
        email_data = []
        for message in unique_messages[:max_results]:
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
                'body': body[:500] + ('...' if len(body) > 500 else '')
            })
        
        return {
            "status": "success",
            "account": account_id,
            "report": f"Found {len(email_data)} emails matching query: '{query}' using strategies: {', '.join(tried_strategies)}",
            "emails": email_data,
            "search_strategies_used": tried_strategies
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error searching Gmail for account {account_id}: {str(e)}"
        }

# Replace the original search_gmail with the new clean version
search_gmail = search_gmail_with_query

def categorized_search_gmail(category: str, account_id: str = "", max_results: int = 10) -> dict:
    """Searches Gmail for specific emails based on predefined categories.
    
    Args:
        category: Category to search for. Valid values: 'people', 'projects', 'tasks', 'attachments', 'meetings'
        account_id: Specific account ID to search. If empty, searches all accounts.
        max_results: Maximum number of results to return.
        
    Returns:
        Result containing matching emails
    """
    # Set default values
    tag = None
        
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
    
    # Use the implementation directly with account_id support
    if account_id:
        result = _search_gmail_impl(query, account_id, max_results)
    else:
        # Search across all accounts
        account_manager = GmailAccountManager()
        all_emails = []
        accounts_searched = []
        accounts_with_results = []
        accounts = list(account_manager.get_accounts().keys())
        
        for acc in accounts:
            result = _search_gmail_impl(query, acc, max_results)
            if result["status"] == "success":
                accounts_searched.append(acc)
                if "emails" in result and result["emails"]:
                    all_emails.extend(result["emails"])
                    accounts_with_results.append(acc)
        
        # Sort emails by date (most recent first)
        all_emails.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        # Limit total results to max_results
        all_emails = all_emails[:max_results]
        
        result = {
            "status": "success",
            "report": f"Found {len(all_emails)} emails in category '{category}' across {len(accounts_with_results)} accounts",
            "emails": all_emails,
            "accounts_searched": accounts_searched,
            "accounts_with_results": accounts_with_results,
            "total_accounts": len(accounts)
        }
    
    # Add categorization info to the results
    if result["status"] == "success" and "emails" in result:
        if tag:
            result["category"] = category.lower()
            result["tag"] = tag.lower()
            result["search_criteria"] = query
        else:
            result["category"] = category.lower()
            result["search_criteria"] = query
    
    return result

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
def search_by_from(sender: str, account_id: str = "", max_results: int = 10) -> dict:
    """Search for emails from a specific sender.
    
    Args:
        sender: Email address to search for
        account_id: Optional account ID to search in
        max_results: Maximum number of results to return
        
    Returns:
        Result containing matching emails
    """
    query = f"from:{sender}"
    return _search_gmail_impl(query, account_id, max_results)
    
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

def check_upcoming_deadlines() -> dict:
    """Searches Gmail for emails containing deadline-related keywords and promises.
    Returns structured information about upcoming deadlines and promises.
    
    Returns:
        dict: Contains status, deadlines found, and any error messages
    """
    # Define deadline-related search patterns
    formal_deadlines = [
        "deadline", "due", "due on", "submit by", "submission date",
        "expected by", "target date", "expected delivery date",
        "need this by", "deliver by"
    ]
    
    promise_phrases = [
        "i'll update you on", "i will update you on",
        "i'll submit this on", "i will submit this on",
        "i'll send it by", "i will send it by",
        "i'll deliver this by", "i will deliver this by",
        "you'll get it by", "you will get it by",
        "should be ready by", "expected to be done by",
        "hoping to send this by", "i'll get this to you by",
        "this should be done by", "planning to send this by",
        "deliver this on"
    ]
    
    # Combine into one search query
    search_terms = " OR ".join([f'"{term}"' for term in formal_deadlines + promise_phrases])
    
    # Get Gmail service
    service_result = get_gmail_service()
    if service_result["status"] == "error":
        return service_result
    
    service = service_result["service"]
    
    try:
        # Search for emails with deadline-related content
        results = service.users().messages().list(
            userId='me',
            q=search_terms,
            maxResults=20  # Increase if needed
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            return {
                "status": "success",
                "report": "No upcoming deadlines found.",
                "deadlines": []
            }
        
        # Process each email
        deadlines = []
        for message in messages:
            msg = service.users().messages().get(
                userId='me',
                id=message['id'],
                format='full'
            ).execute()
            
            # Extract email details
            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown sender')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown date')
            
            # Extract body
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
            
            # Find deadline-related content in the email
            content = f"{subject} {body}".lower()
            found_deadlines = []
            
            # Look for formal deadlines
            for term in formal_deadlines:
                idx = content.find(term)
                if idx != -1:
                    # Get context around the deadline (up to 100 chars)
                    start = max(0, idx - 50)
                    end = min(len(content), idx + 50)
                    context = content[start:end].strip()
                    found_deadlines.append({
                        "type": "formal",
                        "keyword": term,
                        "context": context
                    })
            
            # Look for promises
            for term in promise_phrases:
                idx = content.find(term)
                if idx != -1:
                    start = max(0, idx - 50)
                    end = min(len(content), idx + 50)
                    context = content[start:end].strip()
                    found_deadlines.append({
                        "type": "promise",
                        "keyword": term,
                        "context": context
                    })
            
            if found_deadlines:
                deadlines.append({
                    "email_id": message['id'],
                    "subject": subject,
                    "from": sender,
                    "date": date,
                    "deadlines_found": found_deadlines
                })
        
        return {
            "status": "success",
            "report": f"Found {len(deadlines)} emails with deadline-related content",
            "deadlines": deadlines
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error checking deadlines: {str(e)}"
        }

def add_gmail_account(account_id: str):
    """Add new Gmail account"""
    success = gmail_auth(account_id)
    if success:
        return {
            "status": "success",
            "message": f"Successfully added Gmail account: {account_id}"
        }
    return {
        "status": "error",
        "message": "Failed to authenticate new account"
    }

def list_gmail_accounts():
    """List all configured Gmail accounts"""
    token_file = 'gmail_tokens.json'
    
    if not os.path.exists(token_file):
        return {
            "status": "success",
            "accounts": {}
        }
        
    try:
        with open(token_file, 'r') as f:
            all_tokens = json.load(f)
            
        accounts = {
            account_id: {
                "scopes": token_data["scopes"],
                "expiry": token_data["expiry"]
            } for account_id, token_data in all_tokens.items()
        }
        
        return {
            "status": "success",
            "accounts": accounts
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error listing Gmail accounts: {str(e)}"
        }

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


        