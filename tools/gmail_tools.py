import os
import json
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def search_gmail(query: str, max_results: int = 10) -> dict:
    """Searches Gmail for specific emails matching a query.
    
    Args:
        query (str): Search query (e.g. "from:example@gmail.com", "subject:meeting")
        max_results (int, optional): Maximum number of emails to retrieve. Defaults to 10.
        
    Returns:
        dict: status and result containing email information or error message.
    """
    # Check if token.json exists
    if not os.path.exists('token.json'):
        return {
            "status": "error",
            "error_message": "Gmail authentication not set up. Please run setup_gmail_auth.py first."
        }
    
    try:
        # Load credentials from token.json
        with open('token.json', 'r') as token_file:
            token_data = json.load(token_file)
            creds = Credentials.from_authorized_user_info(token_data)
        
        # If credentials expired, refresh them
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Update token.json with refreshed credentials
            with open('token.json', 'w') as token:
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
        
        # Search for emails matching the query
        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return {
                "status": "success",
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
            "report": f"Found {len(email_data)} emails matching query: '{query}'",
            "emails": email_data
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error searching Gmail: {str(e)}"
        }