#!/usr/bin/env python3
"""
Gmail Tools Module

This module provides Gmail API integration tools using Google ADK.
"""

import datetime
import os
import os.path
import sys
import json
import base64
import socket
import webbrowser
import logging
import time
from typing import Optional, Dict, List, Union, Any, TypedDict, Literal
from zoneinfo import ZoneInfo
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from email.mime.text import MIMEText
from .gmail_account_manager import GmailAccountManager
from tenacity import retry, stop_after_attempt, wait_exponential
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the scopes needed for Gmail API
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose'
]

# Constants
TOKEN_FILE = 'gmail_tokens.json'
CREDENTIALS_FILE = 'credentials.json'
DEFAULT_ACCOUNT = 'default'
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 1  # seconds

# Quota constants
PROJECT_QUOTA_LIMIT = 1200000  # per minute
USER_QUOTA_LIMIT = 15000  # per minute

# Initialize account manager
account_manager = GmailAccountManager()

class QuotaManager:
    """Manages Gmail API quota usage."""
    
    def __init__(self):
        self.project_quota = 0
        self.user_quotas = {}
        self.last_reset = time.time()
        
    def check_quota(self, method: str, account_id: str) -> bool:
        """Check if operation is within quota limits.
        
        Args:
            method: API method being called
            account_id: Account identifier
            
        Returns:
            bool: True if within limits, False otherwise
        """
        # Reset quotas if minute has passed
        current_time = time.time()
        if current_time - self.last_reset >= 60:
            self.project_quota = 0
            self.user_quotas = {}
            self.last_reset = current_time
            
        # Get quota cost for method
        quota_cost = self._get_method_quota(method)
        
        # Check project quota
        if self.project_quota + quota_cost > PROJECT_QUOTA_LIMIT:
            return False
            
        # Check user quota
        user_quota = self.user_quotas.get(account_id, 0)
        if user_quota + quota_cost > USER_QUOTA_LIMIT:
            return False
            
        # Update quotas
        self.project_quota += quota_cost
        self.user_quotas[account_id] = user_quota + quota_cost
        return True
        
    def _get_method_quota(self, method: str) -> int:
        """Get quota cost for a method.
        
        Args:
            method: API method name
            
        Returns:
            int: Quota units required
        """
        quota_costs = {
            'messages.list': 5,
            'messages.get': 5,
            'messages.send': 100,
            'messages.delete': 10,
            'messages.batchDelete': 50,
            'messages.import': 25,
            'messages.insert': 25,
            'drafts.create': 10,
            'drafts.delete': 10,
            'drafts.get': 5,
            'drafts.list': 5,
            'drafts.send': 100,
            'drafts.update': 15,
            'threads.get': 10,
            'threads.list': 10,
            'threads.modify': 10,
            'threads.delete': 20,
            'threads.trash': 10,
            'threads.untrash': 10
        }
        return quota_costs.get(method, 1)  # Default to 1 if unknown

# Initialize quota manager
quota_manager = QuotaManager()

# Type definitions
class GmailMessage(TypedDict):
    id: str
    subject: str
    from_: str
    date: str
    snippet: str
    body: str

class GmailServiceResponse(TypedDict):
    status: Literal['success', 'error']
    error_message: Optional[str]
    service: Optional[Any]  # googleapiclient.discovery.Resource
    account: Optional[str]

class GmailErrorResponse(TypedDict):
    status: Literal['error']
    error_message: str

class GmailMessageResponse(TypedDict):
    status: Literal['success', 'error']
    account: str
    messages: List[GmailMessage]
    report: Optional[str]
    error_message: Optional[str]

class GmailSearchResponse(TypedDict):
    status: Literal['success', 'error']
    account: str
    report: str
    emails: List[GmailMessage]
    accounts_searched: List[str]
    accounts_with_results: List[str]
    total_accounts: int

GmailResponse = Union[GmailServiceResponse, GmailErrorResponse, GmailMessageResponse, GmailSearchResponse]

class GmailDeadlineResponse(TypedDict):
    status: Literal['success', 'error']
    report: str
    deadlines: List[Dict[str, Any]]
    error_message: Optional[str]

class GmailAccountResponse(TypedDict):
    status: Literal['success', 'error']
    message: str
    error_message: Optional[str]

class GmailAccountListResponse(TypedDict):
    status: Literal['success', 'error']
    accounts: Dict[str, Dict[str, Any]]
    error_message: Optional[str]

class GmailProjectIntentResponse(TypedDict):
    intents: Dict[str, List[Dict[str, str]]]
    confidence_scores: Dict[str, float]
    has_project_intent: bool

class GmailProjectSearchResponse(TypedDict):
    status: Literal['success', 'error']
    report: str
    emails: List[Dict[str, Any]]
    categorized_results: Dict[str, List[Dict[str, Any]]]
    accounts_searched: List[str]
    accounts_with_results: List[str]
    total_accounts: int
    search_strategies: List[str]
    time_filter: str
    error_message: Optional[str]

class GmailAnalysisResponse(TypedDict):
    status: Literal['success', 'error']
    subject: str
    sender: str
    body: str
    categories: Dict[str, List[str]]
    error_message: Optional[str]

class GmailMetadataResponse(TypedDict):
    status: Literal['success', 'error']
    subject: str
    sender: str
    date: str
    has_attachment: bool
    attachment_info: List[str]
    body: str
    error_message: Optional[str]

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

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def execute_with_retry(request):
    """Execute Gmail API request with retry logic."""
    try:
        result = request.execute()
        if result is None:
            logger.error("Gmail API request returned None")
            return None
        return result
    except HttpError as error:
        if error.resp.status in [429, 500, 503]:
            logger.warning(f"Retrying after HTTP error {error.resp.status}: {error}")
            # Add delay for rate limit errors
            if error.resp.status == 429:
                time.sleep(5)  # Wait 5 seconds before retry
            raise
        logger.error(f"Gmail API error: {error}")
        return None
    except Exception as e:
        if "Too many concurrent requests" in str(e):
            logger.warning("Concurrent request limit reached, waiting before retry")
            time.sleep(5)  # Wait 5 seconds before retry
            raise
        logger.error(f"Unexpected error in execute_with_retry: {e}")
        return None

def get_gmail_service(account_id: Optional[str] = None) -> GmailServiceResponse:
    """Get Gmail service for specified account."""
    try:
        account_id = account_id or account_manager.get_default_account()
        if not account_id:
            return GmailServiceResponse(
                status="error",
                error_message="No account ID provided and no default account found",
                service=None,
                account=None
            )
            
        credentials_dict = account_manager.get_account_credentials(account_id)
        if not credentials_dict:
            return GmailServiceResponse(
                status="error",
                error_message=f"No credentials found for account {account_id}",
                service=None,
                account=account_id
            )
            
        credentials = Credentials.from_authorized_user_info(credentials_dict)
        service = build('gmail', 'v1', credentials=credentials)
        
        return GmailServiceResponse(
            status="success",
            error_message=None,
            service=service,
            account=account_id
        )
    except Exception as e:
        logger.error(f"Error getting Gmail service: {e}")
        return GmailServiceResponse(
            status="error",
            error_message=str(e),
            service=None,
            account=account_id
        )

def get_credentials(account_id: str = DEFAULT_ACCOUNT) -> Optional[Credentials]:
    """Get valid credentials for Gmail API.
    
    Args:
        account_id: Account identifier
        
    Returns:
        Valid credentials or None if failed
    """
    try:
        # Get token data from Supabase
        token_data = account_manager.get_account_credentials(account_id)
        if not token_data:
            logger.error(f"Account {account_id} not found in Supabase")
            return None
            
        # Create credentials object
        creds = Credentials(
            token=token_data['token'],
            refresh_token=token_data['refresh_token'],
            token_uri=token_data['token_uri'],
            client_id=token_data['client_id'],
            client_secret=token_data['client_secret'],
            scopes=token_data['scopes']
        )
        
        # Check if credentials need refresh
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    # Update token in Supabase
                    token_data.update({
                        'token': creds.token,
                        'expiry': creds.expiry.isoformat() if creds.expiry else None
                    })
                    account_manager.add_account(account_id, token_data)
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    return None
            else:
                logger.error("Credentials expired and no refresh token")
                return None
                
        return creds
        
    except Exception as e:
        logger.error(f"Error getting credentials: {e}")
        return None

def gmail_auth(account_id: str = DEFAULT_ACCOUNT) -> bool:
    """Authenticate with Gmail API using InstalledAppFlow (works with Web App credentials if http://localhost is authorized redirect URI)."""
    logger.info(f"Starting InstalledAppFlow authentication for account: {account_id}")

    if not os.path.exists(CREDENTIALS_FILE):
        logger.error("Credentials file not found")
        print("\nERROR: 'credentials.json' file not found!")
        print("\nFollow these steps to get your credentials.json file:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select an existing one")
        print("3. Go to 'APIs & Services' > 'Library'")
        print("4. Search for 'Gmail API' and enable it")
        print("5. Go to 'APIs & Services' > 'Credentials'")
        print("6. Click 'Create Credentials' > 'OAuth client ID'")
        print("7. Set Application type to 'Web application'")
        print("8. Name your client and click 'Create'")
        print("9. Download the JSON file and save it as 'credentials.json'")
        print("Ensure this credentials.json is for a 'Web application' type OAuth client.")
        print("Ensure that 'http://localhost' or 'http://localhost:<port>' is added as an Authorized redirect URI in Google Cloud Console for these credentials.")
        return False

    # --- DEBUG: Load credentials and print client_id --- #
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            creds_data = json.load(f)
        # The structure might be {"installed": {...}} or {"web": {...}}
        if 'web' in creds_data:
            client_id = creds_data['web']['client_id']
        elif 'installed' in creds_data: # Should be web, but check installed just in case
             client_id = creds_data['installed']['client_id']
        else:
            client_id = '[Could not find client_id in credentials.json]'
        logger.info(f"DEBUG: Attempting to use credentials for Client ID: {client_id}")
        print(f"\nDEBUG: Using Client ID: {client_id}")
        print("DEBUG: Please verify this Client ID matches the one configured in Google Cloud Console.\n")
    except Exception as read_err:
        logger.error(f"DEBUG: Failed to read or parse {CREDENTIALS_FILE}: {read_err}")
        print(f"DEBUG: Could not read {CREDENTIALS_FILE} to verify Client ID.")
    # --- END DEBUG --- #

    creds = None
    try:
        # Use InstalledAppFlow again
        logger.info(f"Creating InstalledAppFlow for account: {account_id}")
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            SCOPES
            # Note: redirect_uri is typically managed internally by run_local_server for localhost
        )

        # Run local server for authentication - Use port 8085 to find a free port
        logger.info("Attempting to run local server for authentication via InstalledAppFlow.")
        print("\n>>> Please look for a browser window/tab opening for Google Authorization.")
        print(">>> The flow will attempt to automatically receive the redirect on localhost:8085.")

        try:
            creds = flow.run_local_server(
                port=8085,  # Use the fixed port configured in Google Cloud Console
                open_browser=True,
                access_type='offline', # Request refresh token
                prompt='consent'       # Ensure user always sees consent screen
                # success_message="Authentication successful! You can close the browser tab/window.",
                # timeout_seconds=120
            )
            logger.info("InstalledAppFlow local server flow completed.")
        except Exception as server_err:
            logger.error(f"Error during run_local_server with InstalledAppFlow: {server_err}", exc_info=True)
            print(f"\nError occurred during the authentication server step: {server_err}")
            print(f"Please ensure 'http://localhost:8085' is the authorized redirect URI in Google Cloud Console.")
            print("Also ensure no other program is blocking port 8085 and check firewall settings.")
            return False # Exit if server fails

        if not creds or not creds.refresh_token:
            logger.error("Failed to obtain valid credentials or refresh token after InstalledAppFlow.")
            print("\nWARNING: Did not receive valid credentials or refresh token!")
            print("This might happen if you denied access or closed the browser too early.")
            print("Please go to https://myaccount.google.com/permissions, revoke access for this app, then try again.")
            return False

        # Save credentials to Supabase via Account Manager
        logger.info(f"Credentials obtained. Saving for account: {account_id}")
        credentials = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes,
            'expiry': creds.expiry.isoformat() if creds.expiry else None
        }

        account_manager.add_account(account_id, credentials)

        logger.info(f"Authentication and saving successful for account: {account_id}")
        print(f"\nSuccessfully authenticated and saved credentials for {account_id}.")
        return True

    except Exception as e:
        # Catch other potential errors (e.g., reading credentials.json, creating flow)
        logger.error(f"General authentication failed for {account_id} using InstalledAppFlow: {e}", exc_info=True)
        print(f"\nAn unexpected error occurred during authentication setup: {e}")
        return False

# Gmail functionality
def get_gmail_messages(account_id: Optional[str] = None, max_results: int = 10) -> GmailMessageResponse:
    """Get Gmail messages using batch operations."""
    # Determine target account early
    target_account_id = account_id or account_manager.get_default_account()
    if not target_account_id:
        logger.error("get_gmail_messages called with no account_id and no default account.")
        return GmailMessageResponse(
            status="error",
            account=None,
            messages=[],
            report="No account specified and no default account found.",
            error_message="No account ID provided and no default account found"
        )

    try:
        # Get service for account
        service_response = get_gmail_service(target_account_id)
        if service_response.get('status') == 'error':
            logger.error(f"Failed to get Gmail service for {target_account_id} in get_gmail_messages.")
            return GmailMessageResponse(
                status="error",
                account=target_account_id,
                messages=[],
                report=f"Error accessing account {target_account_id}",
                error_message=service_response.get('error_message', 'Failed to get Gmail service')
            )
        service = service_response['service']
        actual_account_id = service_response['account'] # Use the account ID returned by get_gmail_service

        # Check quota before proceeding
        if not quota_manager.check_quota("users.messages.list", actual_account_id):
            logger.warning(f"Quota possibly exceeded for users.messages.list on account {actual_account_id}")
            return GmailMessageResponse(
                status="error",
                account=actual_account_id,
                messages=[],
                report="API quota exceeded. Please try again later.",
                error_message="API quota exceeded. Please try again later."
            )

        # Create request objects first
        list_request = service.users().messages().list(
            userId="me",
            maxResults=max_results
        )

        # Execute list request with retry
        result = execute_with_retry(list_request)
        if not result:
            logger.error(f"Failed to retrieve message list for account {actual_account_id}")
            return GmailMessageResponse(
                status="error",
                account=actual_account_id,
                messages=[],
                report="Failed to retrieve message list",
                error_message="Failed to retrieve message list after retries."
            )

        messages = result.get("messages", [])
        if not messages:
            return GmailMessageResponse(
                status="success",
                account=actual_account_id,
                messages=[],
                report=f"No messages found for account {actual_account_id}",
                error_message=None
            )

        # Create batch request
        batch = service.new_batch_http_request()
        message_details_list = [] # Renamed from message_details to avoid confusion
        batch_errors = []

        def callback(request_id, response, exception):
            nonlocal batch_errors # Allow modifying outer scope variable
            if exception:
                error_msg = f"Error in batch request {request_id}: {exception}"
                logger.error(error_msg)
                batch_errors.append(error_msg)
                # Don't raise here, just record the error
                # If needed, could try to re-raise specific retryable errors
                return
            if response:
                # Process valid response here
                try:
                    headers = {h['name']: h['value'] for h in response['payload']['headers']}
                    body = ""
                    if 'parts' in response['payload']:
                        for part in response['payload']['parts']:
                            if part['mimeType'] == 'text/plain':
                                body_data = part['body'].get('data', '')
                                if body_data:
                                    body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                                    break
                    elif 'body' in response['payload'] and 'data' in response['payload']['body']:
                        body_data = response['payload']['body']['data']
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8')

                    message_details_list.append({
                        'id': response['id'],
                        'subject': headers.get('Subject', 'No subject'),
                        'from_': headers.get('From', 'Unknown sender'),
                        'date': headers.get('Date', 'Unknown date'),
                        'snippet': response.get('snippet', ''),
                        'body': body[:500] + ('...' if len(body) > 500 else '') # Truncate body
                    })
                except Exception as proc_err:
                    error_msg = f"Error processing message {response.get('id', '[unknown ID]')} in batch callback: {proc_err}"
                    logger.error(error_msg, exc_info=True)
                    batch_errors.append(error_msg)

        # Add requests to batch (Consider smaller batch sizes if needed)
        batch_size = 10 # Increased batch size slightly
        current_batch = service.new_batch_http_request()
        request_count = 0

        for msg in messages:
            current_batch.add(
                service.users().messages().get(
                    userId="me",
                    id=msg["id"],
                    format="full" # Fetch full details
                ),
                callback=callback,
                request_id=msg["id"] # Use message ID as request ID
            )
            request_count += 1

            # Execute batch if size limit reached or it's the last message
            if request_count == batch_size or msg == messages[-1]:
                try:
                    logger.info(f"Executing batch of {request_count} requests for {actual_account_id}")
                    # execute_with_retry might be needed here too if batches fail often
                    current_batch.execute()
                    # Consider a small sleep ONLY if hitting rate limits frequently
                    # time.sleep(1)
                except Exception as batch_exec_err:
                    error_msg = f"Batch execution failed for account {actual_account_id}: {batch_exec_err}"
                    logger.error(error_msg, exc_info=True)
                    # Decide if this is fatal or if we should continue with other batches
                    # For now, return error for the whole operation if a batch fails
                    return GmailMessageResponse(
                        status="error",
                        account=actual_account_id,
                        messages=[],
                        report="Failed to execute batch request for message details.",
                        error_message=error_msg
                    )
                # Reset for next batch
                current_batch = service.new_batch_http_request()
                request_count = 0

        # After all batches
        if batch_errors:
            # Report success but mention errors
             report_msg = f"Retrieved {len(message_details_list)} messages for account {actual_account_id}, but encountered {len(batch_errors)} errors during detail fetch."
             logger.warning(report_msg + " Errors: " + "; ".join(batch_errors[:3])) # Log first few errors
             # Decide if this should be status='error' or 'success' with caveats
             # Let's keep it success, but include errors in the report
             return GmailMessageResponse(
                status="success", # Or maybe 'partial_success'? For now, 'success'.
                account=actual_account_id,
                messages=message_details_list,
                report=report_msg,
                error_message="Errors occurred during batch processing. Check logs."
             )

        return GmailMessageResponse(
            status="success",
            account=actual_account_id,
            messages=message_details_list,
            report=f"Retrieved {len(message_details_list)} messages for account {actual_account_id}",
            error_message=None
        )

    except Exception as e:
        logger.error(f"Error in get_gmail_messages for account {target_account_id}: {e}", exc_info=True)
        return GmailMessageResponse(
            status="error",
            account=target_account_id,
            messages=[],
            report=f"An unexpected error occurred while getting messages for {target_account_id}.",
            error_message=str(e)
        )

def get_gmail_messages_for_account(account_id: str, max_results: int = 10) -> Union[GmailMessageResponse, GmailErrorResponse]:
    """Get recent messages from a specific Gmail account.
    
    Args:
        account_id: The account ID to check
        max_results: Maximum number of messages to retrieve
        
    Returns:
        GmailMessageResponse: Contains messages and account information if successful
        GmailErrorResponse: Contains error status and message if failed
    """
    service_result = get_gmail_service(account_id)
    if service_result["status"] == "error":
        return service_result
        
    service = service_result["service"]
    
    try:
        # Get messages with retry logic
        for attempt in range(MAX_RETRIES):
            try:
                results = service.users().messages().list(
                    userId='me',
                    maxResults=max_results
                ).execute()
                break
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                logger.warning(f"Message list attempt {attempt + 1} failed: {e}")
                time.sleep(RATE_LIMIT_DELAY)
                
        messages = results.get('messages', [])
        
        if not messages:
            return {
                "status": "success",
                "account": account_id,
                "messages": [],
                "report": "No messages found"
            }
        
        # Get full message details for each message
        email_data = []
        for message in messages:
            try:
                # Get message with retry logic
                for attempt in range(MAX_RETRIES):
                    try:
                        msg = service.users().messages().get(
                            userId='me',
                            id=message['id'],
                            format='full'
                        ).execute()
                        break
                    except Exception as e:
                        if attempt == MAX_RETRIES - 1:
                            raise
                        logger.warning(f"Message get attempt {attempt + 1} failed: {e}")
                        time.sleep(RATE_LIMIT_DELAY)
                        
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
                    'from_': sender,
                    'date': date,
                    'snippet': msg.get('snippet', ''),
                    'body': body[:500] + ('...' if len(body) > 500 else '')
                })
            except Exception as e:
                logger.error(f"Error getting message {message['id']}: {e}")
                continue
            
        return {
            "status": "success",
            "account": account_id,
            "messages": email_data,
            "report": f"Found {len(email_data)} messages"
        }
        
    except Exception as e:
        logger.error(f"Error getting messages for account {account_id}: {e}")
        return {
            "status": "error",
            "error_message": f"Error getting messages for account {account_id}: {str(e)}"
        }

# Helper to fix the parameter issue by providing an explicit parameter schema function
def search_gmail_with_query(query: str, max_results: int = 10, account_id: Optional[str] = None) -> Union[GmailSearchResponse, GmailErrorResponse]:
    """Search Gmail messages with the given query.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        account_id: Optional account ID to search
        
    Returns:
        GmailSearchResponse: Contains matching messages and search info if successful
        GmailErrorResponse: Contains error status and message if failed
    """
    logger.info(f"Searching Gmail with query: {query} for account: {account_id}")
    
    try:
        account_manager = GmailAccountManager()
        accounts = account_manager.get_accounts()
        
        if not accounts:
            return {
                "status": "error",
                "error_message": "No Gmail accounts configured"
            }
            
        if account_id and account_id not in accounts:
            return {
                "status": "error",
                "error_message": f"Account {account_id} not found"
            }
            
        # Extract time filter from query
        time_filter = None
        if "this week" in query.lower():
            time_filter = "after:" + (datetime.now() - datetime.timedelta(days=7)).strftime("%Y/%m/%d")
        elif "this month" in query.lower():
            time_filter = "after:" + (datetime.now() - datetime.timedelta(days=30)).strftime("%Y/%m/%d")
        elif "today" in query.lower():
            time_filter = "after:" + datetime.now().strftime("%Y/%m/%d")
            
        # Build search query
        search_query = query
        if time_filter:
            search_query = f"{search_query} {time_filter}"
            
        # If query is empty, use smart project search or get recent emails
        if not search_query.strip():
            search_query = "in:inbox"
            
        # Search all accounts sequentially
        all_results = []
        for acc_id in (accounts if not account_id else [account_id]):
            result = _search_gmail_impl(acc_id, search_query, max_results)
            if result["status"] == "success":
                all_results.extend(result["messages"])
                
        # Sort by date and limit results
        all_results.sort(key=lambda x: x["date"], reverse=True)
        all_results = all_results[:max_results]
        
        return {
            "status": "success",
            "account": account_id or "all",
            "messages": all_results,
            "report": f"Found {len(all_results)} messages matching query"
        }
        
    except Exception as e:
        logger.error(f"Error searching Gmail: {e}")
        return {
            "status": "error",
            "error_message": str(e)
        }
        
def _search_gmail_impl(account_id: str, query: str, max_results: int) -> Union[GmailSearchResponse, GmailErrorResponse]:
    """Internal implementation of Gmail search.
    
    Args:
        account_id: Account ID to search
        query: Search query string
        max_results: Maximum number of results to return
        
    Returns:
        GmailSearchResponse: Contains matching messages and search info if successful
        GmailErrorResponse: Contains error status and message if failed
    """
    service_result = get_gmail_service(account_id)
    if service_result["status"] == "error":
        return service_result
        
    service = service_result["service"]
    
    try:
        # Search messages with retry logic
        for attempt in range(MAX_RETRIES):
            try:
                results = service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=max_results
                ).execute()
                break
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                logger.warning(f"Search attempt {attempt + 1} failed: {e}")
                time.sleep(RATE_LIMIT_DELAY)
                
        messages = results.get('messages', [])
        
        if not messages:
            return {
                "status": "success",
                "account": account_id,
                "messages": [],
                "report": "No messages found matching query"
            }
            
        # Get full message details
        email_data = []
        for message in messages:
            try:
                # Get message with retry logic
                for attempt in range(MAX_RETRIES):
                    try:
                        msg = service.users().messages().get(
                            userId='me',
                            id=message['id'],
                            format='full'
                        ).execute()
                        break
                    except Exception as e:
                        if attempt == MAX_RETRIES - 1:
                            raise
                        logger.warning(f"Message get attempt {attempt + 1} failed: {e}")
                        time.sleep(RATE_LIMIT_DELAY)
                        
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
                    'from_': sender,
                    'date': date,
                    'snippet': msg.get('snippet', ''),
                    'body': body[:500] + ('...' if len(body) > 500 else '')
                })
            except Exception as e:
                logger.error(f"Error getting message {message['id']}: {e}")
                continue
                
        return {
            "status": "success",
            "account": account_id,
            "messages": email_data,
            "report": f"Found {len(email_data)} messages matching query"
        }
        
    except Exception as e:
        logger.error(f"Error searching Gmail for account {account_id}: {e}")
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
        result = _search_gmail_impl(account_id, query, max_results)
    else:
        # Search across all accounts
        account_manager = GmailAccountManager()
        all_emails = []
        accounts_searched = []
        accounts_with_results = []
        accounts = list(account_manager.get_accounts().keys())
        
        for acc in accounts:
            result = _search_gmail_impl(acc, query, max_results)
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

def analyze_email_content(email_id: str) -> GmailAnalysisResponse:
    """Analyzes the content of a specific email to extract relevant information.
    
    Args:
        email_id (str): ID of the email to analyze
        
    Returns:
        GmailAnalysisResponse: Contains email analysis results
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

def extract_email_metadata(email_id: str) -> GmailMetadataResponse:
    """Extracts structured metadata from an email.
    
    Args:
        email_id: ID of the email to extract metadata from
        
    Returns:
        GmailMetadataResponse: Contains email metadata
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
def search_by_from(sender: str, account_id: str = "", max_results: int = 10) -> GmailSearchResponse:
    """Search for emails from a specific sender.
    
    Args:
        sender: Email address to search for
        account_id: Optional account ID to search in
        max_results: Maximum number of results to return
        
    Returns:
        GmailSearchResponse: Contains matching messages and search info if successful
    """
    query = f"from:{sender}"
    result = _search_gmail_impl(account_id, query, max_results)
    return GmailSearchResponse(
        status=result["status"],
        account=account_id or "default",
        report=result.get("report", ""),
        emails=result.get("messages", []),
        accounts_searched=[account_id] if account_id else [],
        accounts_with_results=[account_id] if account_id and result["status"] == "success" else [],
        total_accounts=1
    )
    
# Simplest possible function with explicit parameter and type annotation
def search_by_subject(subject_text: str) -> GmailSearchResponse:
    """Search for emails with specific text in the subject.
    
    Args:
        subject_text: Text to search for in subject
        
    Returns:
        GmailSearchResponse: Contains matching messages and search info if successful
    """
    query = f"subject:{subject_text}"
    result = _search_gmail_impl("default", query, 10)
    return GmailSearchResponse(
        status=result["status"],
        account="default",
        report=result.get("report", ""),
        emails=result.get("messages", []),
        accounts_searched=["default"],
        accounts_with_results=["default"] if result["status"] == "success" else [],
        total_accounts=1
    )

def check_upcoming_deadlines() -> GmailDeadlineResponse:
    """Searches Gmail for emails containing deadline-related keywords and promises.
    Returns structured information about upcoming deadlines and promises.
    
    Returns:
        GmailDeadlineResponse: Contains status, deadlines found, and any error messages
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
        return GmailDeadlineResponse(
            status="error",
            report="Error getting Gmail service",
            deadlines=[],
            error_message=service_result["error_message"]
        )
    
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
            return GmailDeadlineResponse(
                status="success",
                report="No upcoming deadlines found.",
                deadlines=[]
            )
        
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
        
        return GmailDeadlineResponse(
            status="success",
            report=f"Found {len(deadlines)} emails with deadline-related content",
            deadlines=deadlines
        )
        
    except Exception as e:
        return GmailDeadlineResponse(
            status="error",
            report=f"Error checking deadlines: {str(e)}",
            deadlines=[],
            error_message=str(e)
        )

def add_new_gmail_account(account_id: Optional[str] = None) -> GmailAccountResponse:
    """Add a new Gmail account by providing the Gmail address (account_id). Triggers OAuth login flow and browser redirect for authorization. If not provided, the agent should prompt the user for the email address."""
    try:
        if not account_id:
            # Return an error response instead of raising ValueError
            logger.error("Attempted to add account without providing account_id.")
            return GmailAccountResponse(
                status="error",
                message="Account ID (email address) is required.",
                error_message="Account ID (email address) is required."
            )

        # Check if credentials file exists *before* calling gmail_auth
        if not os.path.exists(CREDENTIALS_FILE):
            logger.error(f"{CREDENTIALS_FILE} not found. Cannot authenticate.")
            return GmailAccountResponse(
                status="error",
                message=f"{CREDENTIALS_FILE} not found. Please ensure it is present.",
                error_message=f"{CREDENTIALS_FILE} not found."
            )

        success = gmail_auth(account_id)
        if success:
            return GmailAccountResponse(
                status="success",
                message=f"Successfully added Gmail account: {account_id}",
                error_message=None
            )
        else:
            # gmail_auth logs the specific error, return a generic failure message
            return GmailAccountResponse(
                status="error",
                message=f"Failed to authenticate new account: {account_id}. Check logs for details.",
                error_message="Authentication failed during OAuth flow."
            )
    except Exception as e:
        logger.error(f"Unexpected error in add_new_gmail_account for {account_id}: {e}", exc_info=True)
        return GmailAccountResponse(
            status="error",
            message=f"An unexpected error occurred while adding account {account_id}.",
            error_message=str(e)
        )

def remove_gmail_account(account_id: str) -> GmailAccountResponse:
    """Remove a Gmail account by email (account_id) from Supabase and local file."""
    if not account_id:
        return GmailAccountResponse(
            status="error",
            message="No account_id provided",
            error_message="No account_id provided"
        )
    removed = account_manager.remove_account(account_id)
    if removed:
        return GmailAccountResponse(
            status="success",
            message=f"Successfully removed Gmail account: {account_id}",
            error_message=None
        )
    return GmailAccountResponse(
        status="error",
        message=f"Account {account_id} not found",
        error_message="Account not found"
    )

def list_gmail_accounts() -> GmailAccountListResponse:
    """List all configured Gmail accounts"""
    try:
        accounts = account_manager.get_accounts()
        # Ensure expiry is serializable, default to None if missing or problematic
        account_details = {}
        for account_id, account_data in accounts.items():
            expiry = account_data.get("expiry")
            # Basic check if expiry looks like an ISO format string
            if expiry and isinstance(expiry, str):
                try:
                    # Attempt parsing to validate format, but store the original string
                    datetime.datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                    serializable_expiry = expiry
                except ValueError:
                    logger.warning(f"Invalid expiry format for {account_id}: {expiry}. Setting expiry to None.")
                    serializable_expiry = None
            elif expiry is None:
                 serializable_expiry = None
            else:
                 # Handle cases where expiry might be datetime object already (though unlikely from JSON)
                 logger.warning(f"Unexpected expiry type for {account_id}: {type(expiry)}. Setting expiry to None.")
                 serializable_expiry = None

            account_details[account_id] = {
                "scopes": account_data.get("scopes", []), # Default to empty list
                "expiry": serializable_expiry
            }

        return GmailAccountListResponse(
            status="success",
            accounts=account_details,
            error_message=None
        )
    except Exception as e:
        logger.error(f"Error listing Gmail accounts: {e}", exc_info=True) # Log traceback
        return GmailAccountListResponse(
            status="error",
            accounts={},
            error_message=f"Error listing Gmail accounts: {str(e)}"
        )

def detect_project_intent(text: str) -> GmailProjectIntentResponse:
    """Analyzes text for project-related intent and patterns.
    
    Args:
        text: Text content to analyze
        
    Returns:
        GmailProjectIntentResponse: Contains detected intents and confidence scores
    """
    # Project initiation patterns
    initiation_patterns = [
        r"(?i)(new|proposed|initiated|started)\s+(project|initiative|work)",
        r"(?i)(can|could)\s+you\s+(build|develop|create|design)",
        r"(?i)(would|should)\s+like\s+to\s+(start|begin|launch)",
        r"(?i)(proposal|proposed|suggestion|suggested)\s+(for|to)",
        r"(?i)(timeline|scope|budget|deadline)\s+(for|of)",
        r"(?i)(kickoff|kick-off|start)\s+(meeting|call|discussion)"
    ]
    
    # Project status patterns
    status_patterns = [
        r"(?i)(update|status|progress)\s+(on|for)",
        r"(?i)(completed|finished|done|delivered)",
        r"(?i)(next\s+steps|next\s+phase|next\s+stage)",
        r"(?i)(review|feedback|approval)\s+(needed|required)"
    ]
    
    # Collaboration patterns
    collaboration_patterns = [
        r"(?i)(collaborate|work\s+together|team\s+up)",
        r"(?i)(partner|partnership|joint\s+effort)",
        r"(?i)(involve|include|participate)",
        r"(?i)(assign|delegate|hand\s+over)"
    ]
    
    import re
    
    # Check for patterns
    intents = {
        "project_initiation": [],
        "project_status": [],
        "collaboration": []
    }
    
    # Check initiation patterns
    for pattern in initiation_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            intents["project_initiation"].append({
                "pattern": pattern,
                "match": match.group(),
                "context": text[max(0, match.start()-50):min(len(text), match.end()+50)]
            })
    
    # Check status patterns
    for pattern in status_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            intents["project_status"].append({
                "pattern": pattern,
                "match": match.group(),
                "context": text[max(0, match.start()-50):min(len(text), match.end()+50)]
            })
    
    # Check collaboration patterns
    for pattern in collaboration_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            intents["collaboration"].append({
                "pattern": pattern,
                "match": match.group(),
                "context": text[max(0, match.start()-50):min(len(text), match.end()+50)]
            })
    
    # Calculate confidence scores
    confidence_scores = {
        "project_initiation": len(intents["project_initiation"]) * 0.3,
        "project_status": len(intents["project_status"]) * 0.2,
        "collaboration": len(intents["collaboration"]) * 0.25
    }
    
    # Cap confidence scores at 1.0
    for key in confidence_scores:
        confidence_scores[key] = min(1.0, confidence_scores[key])
    
    return {
        "intents": intents,
        "confidence_scores": confidence_scores,
        "has_project_intent": any(score > 0.3 for score in confidence_scores.values())
    }

def smart_project_search(account_id: str = "", max_results: int = 10, time_filter: str = "") -> GmailProjectSearchResponse:
    """Smart search for project-related emails using multiple strategies.
    
    Args:
        account_id: Specific account ID to search. If empty, searches all accounts.
        max_results: Maximum number of results to return.
        time_filter: Time filter for emails (e.g., "after:2024/03/01", "newer_than:7d")
        
    Returns:
        GmailProjectSearchResponse: Contains project-related emails and analysis
    """
    # Define specialized project categories and their terms
    project_categories = {
        "web_development": [
            "website", "web development", "web app", "web application",
            "landing page", "site launch", "redesign", "web redesign",
            "frontend", "backend", "fullstack", "responsive design"
        ],
        "ecommerce": [
            "e-commerce", "ecommerce", "online store", "shopify", "woocommerce",
            "wordpress", "magento", "payment gateway", "shopping cart",
            "product catalog", "inventory management"
        ],
        "automation": [
            "automation", "workflow automation", "process automation",
            "integration", "api integration", "webhook", "automated",
            "script", "bot", "automated workflow"
        ],
        "saas": [
            "saas", "software as a service", "subscription", "subscription model",
            "recurring revenue", "user management", "tenant", "multi-tenant",
            "platform", "cloud service"
        ],
        "mobile": [
            "mobile app", "ios app", "android app", "react native",
            "flutter", "mobile development", "app store", "play store",
            "mobile responsive", "mobile-first"
        ],
        "api": [
            "api", "rest api", "graphql", "endpoint", "microservice",
            "service architecture", "backend service", "api integration",
            "api documentation", "swagger"
        ]
    }
    
    # Define search strategies with weights
    search_strategies = [
        # Strategy 1: Project initiation and proposals
        {
            "query": "(\"project proposal\" OR \"project brief\" OR \"project scope\" OR \"project timeline\" OR \"project requirements\" OR \"project specification\")",
            "weight": 1.5
        },
        # Strategy 2: Project status and updates
        {
            "query": "(\"project update\" OR \"project status\" OR \"project progress\" OR \"project milestone\" OR \"project completion\" OR \"project delivery\")",
            "weight": 1.2
        },
        # Strategy 3: Project management
        {
            "query": "(\"project management\" OR \"project team\" OR \"project lead\" OR \"project manager\" OR \"project timeline\" OR \"project budget\")",
            "weight": 1.0
        }
    ]
    
    # Add category-specific strategies
    for category, terms in project_categories.items():
        # Create a query that combines category terms with project context
        category_query = " OR ".join([f'"{term}"' for term in terms])
        search_strategies.append({
            "query": f"({category_query}) AND (project OR proposal OR brief OR timeline OR scope OR launch OR development)",
            "weight": 1.3,
            "category": category
        })
    
    all_emails = []
    accounts_searched = []
    accounts_with_results = []
    
    # Get accounts to search
    account_manager = GmailAccountManager()
    accounts = [account_id] if account_id else list(account_manager.get_accounts().keys())
    
    # Search each account with each strategy
    for acc in accounts:
        for strategy in search_strategies:
            # Add time filter to query if provided
            query = strategy["query"]
            if time_filter:
                query = f"{query} {time_filter}"
            
            result = _search_gmail_impl(acc, query, max_results)
            if result["status"] == "success" and "emails" in result:
                accounts_searched.append(acc)
                if result["emails"]:
                    # Add strategy weight and category to each email
                    for email in result["emails"]:
                        email["search_weight"] = strategy["weight"]
                        email["search_strategy"] = strategy["query"]
                        if "category" in strategy:
                            email["project_category"] = strategy["category"]
                    all_emails.extend(result["emails"])
                    if acc not in accounts_with_results:
                        accounts_with_results.append(acc)
    
    # Remove duplicates while preserving order and weights
    seen_ids = set()
    unique_emails = []
    for email in all_emails:
        if email["id"] not in seen_ids:
            seen_ids.add(email["id"])
            unique_emails.append(email)
        else:
            # Update weight and category if this is a better match
            existing = next(e for e in unique_emails if e["id"] == email["id"])
            if email["search_weight"] > existing["search_weight"]:
                existing["search_weight"] = email["search_weight"]
                existing["search_strategy"] = email["search_strategy"]
                if "project_category" in email:
                    existing["project_category"] = email["project_category"]
    
    # Analyze content for project intent
    for email in unique_emails:
        # Combine subject and body for analysis
        content = f"{email.get('subject', '')} {email.get('body', '')}"
        intent_analysis = detect_project_intent(content)
        email["intent_analysis"] = intent_analysis
        
        # Adjust weight based on intent analysis
        if intent_analysis["has_project_intent"]:
            email["search_weight"] *= 1.5
        
        # Boost weight for category-specific matches
        if "project_category" in email:
            email["search_weight"] *= 1.2
    
    # Sort by date and weight
    unique_emails.sort(key=lambda x: (x.get('date', ''), x.get('search_weight', 0)), reverse=True)
    
    # Limit results
    unique_emails = unique_emails[:max_results]
    
    # Group results by category
    categorized_results = {
        "web_development": [],
        "ecommerce": [],
        "automation": [],
        "saas": [],
        "mobile": [],
        "api": [],
        "other": []
    }
    
    for email in unique_emails:
        category = email.get("project_category", "other")
        if category in categorized_results:
            categorized_results[category].append(email)
        else:
            categorized_results["other"].append(email)
    
    return {
        "status": "success",
        "report": f"Found {len(unique_emails)} project-related emails across {len(accounts_with_results)} accounts",
        "emails": unique_emails,
        "categorized_results": categorized_results,
        "accounts_searched": list(set(accounts_searched)),
        "accounts_with_results": accounts_with_results,
        "total_accounts": len(accounts),
        "search_strategies": [s["query"] for s in search_strategies],
        "time_filter": time_filter
    } 

def get_gmail_spam(account_id: Optional[str] = None, max_results: int = 100) -> GmailMessageResponse:
    """Get spam messages from Gmail account."""
    try:
        service_response = get_gmail_service(account_id)
        if service_response["status"] == "error":
            return GmailMessageResponse(
                status="error",
                error_message=service_response["error_message"],
                account=account_id,
                messages=[],
                report=None
            )

        service = service_response["service"]

        # Get message list
        request = service.users().messages().list(
            userId='me',
            labelIds=['SPAM'],
            maxResults=max_results
        )
        results = execute_with_retry(request)
        
        if not results or 'messages' not in results:
            return GmailMessageResponse(
                status="success",
                error_message=None,
                account=account_id,
                messages=[],
                report=f"No spam messages found in account {account_id}"
            )

        # Get message details in batches
        messages = results['messages']
        batch = service.new_batch_http_request()
        message_details = {}
        batch_errors = []
        
        def callback(request_id, response, exception):
            if exception:
                logger.error(f"Batch request failed for message {request_id}: {exception}")
                batch_errors.append(str(exception))
                return
            if response is None:
                logger.error(f"Batch request returned None for message {request_id}")
                return
            message_details[request_id] = response
            
        # Add requests to batch
        for msg in messages:
            request = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            )
            batch.add(request, callback=callback, request_id=msg['id'])
            
        # Execute batch with retry
        try:
            execute_with_retry(batch)
        except Exception as e:
            logger.error(f"Batch execution failed: {e}")
            return GmailMessageResponse(
                status="error",
                error_message=f"Failed to retrieve message details: {str(e)}",
                account=account_id,
                messages=[],
                report=None
            )
        
        if batch_errors:
            return GmailMessageResponse(
                status="error",
                error_message=f"Some messages failed to retrieve: {'; '.join(batch_errors)}",
                account=account_id,
                messages=[],
                report=None
            )
        
        # Process results
        gmail_messages = []
        for msg in messages:
            if msg['id'] in message_details:
                details = message_details[msg['id']]
                headers = {h['name']: h['value'] for h in details['payload']['headers']}
                
                # Extract body
                body = ""
                if 'parts' in details['payload']:
                    for part in details['payload']['parts']:
                        if part['mimeType'] == 'text/plain':
                            body_data = part['body'].get('data', '')
                            if body_data:
                                body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                                break
                elif 'body' in details['payload'] and 'data' in details['payload']['body']:
                    body_data = details['payload']['body']['data']
                    body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                
                gmail_messages.append({
                    'id': details['id'],
                    'subject': headers.get('Subject', 'No subject'),
                    'from_': headers.get('From', 'Unknown sender'),
                    'date': headers.get('Date', 'Unknown date'),
                    'snippet': details.get('snippet', ''),
                    'body': body[:500] + ('...' if len(body) > 500 else '')
                })

        return GmailMessageResponse(
            status="success",
            error_message=None,
            account=account_id,
            messages=gmail_messages,
            report=f"Found {len(gmail_messages)} spam messages in account {account_id}"
        )

    except Exception as e:
        logger.error(f"Error getting spam messages: {e}")
        return GmailMessageResponse(
            status="error",
            error_message=str(e),
            account=account_id,
            messages=[],
            report=None
        )


        