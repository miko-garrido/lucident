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
from typing import Optional, Dict, List, Union, Any, TypedDict, Literal, Tuple
from zoneinfo import ZoneInfo
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from email.mime.text import MIMEText
from tenacity import retry, stop_after_attempt, wait_exponential
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from supabase import create_client, Client

# Import Database class
from lucident_agent.Database import Database

# Load environment variables from .env file
load_dotenv()

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
DEFAULT_ACCOUNT = 'default'
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 1  # seconds

# --- Use Database class for Supabase access ---
try:
    db = Database()
    supabase = db.client
    logger.info("Supabase client initialized via Database class.")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client via Database: {e}")
    supabase = None

# Hardcoded Google Credentials (as requested in the example)
# Consider moving sensitive parts like client_secret to env variables for better security
GOOGLE_CREDENTIALS = {
  "web": {
    "client_id": os.getenv("GOOGLE_CLIENT_ID", "YOUR_DEFAULT_CLIENT_ID"),
    "project_id": os.getenv("GOOGLE_PROJECT_ID", "YOUR_DEFAULT_PROJECT_ID"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", "YOUR_DEFAULT_CLIENT_SECRET"),
    "redirect_uris": [
      "http://localhost:8080/",
      "http://localhost:8085/"
    ]
  }
}

# --- Refactored GmailAccountManager into a class using Supabase ---
class GmailSupabaseManager:
    """Manages Gmail account credentials using Supabase."""
    def __init__(self, supabase_client: Optional[Client]):
        if supabase_client is None:
            logger.error("Supabase client not provided to GmailSupabaseManager.")
            # Depending on requirements, could raise error or operate in a disabled state
        self.supabase = supabase_client
        self.default_account_id = None # Track default account in memory

    def _check_supabase(self) -> bool:
        """Check if Supabase client is available."""
        if self.supabase is None:
            logger.warning("Supabase client is not initialized. Cannot perform operation.")
            return False
        return True

    def add_account(self, email: str, credentials_obj: Credentials) -> bool:
        """Adds or updates account credentials in Supabase."""
        if not self._check_supabase(): return False
        if not email or not credentials_obj:
            logger.error("Email and credentials object are required to add account.")
            return False

        try:
            token_json = credentials_obj.to_json()
            # Use email as the user_id (primary key combined with token_type)
            data, count = self.supabase.table('tokens').upsert({
                'user_id': email,
                'token_type': 'google',
                'token_data': token_json
            }, on_conflict='user_id, token_type').execute() # Specify conflict target if composite key

            logger.info(f"Successfully upserted credentials for {email} in Supabase.")
            # Set as default if it's the first account added in this session
            if self.default_account_id is None:
                self.default_account_id = email
                logger.info(f"Set {email} as the default account for this session.")
            return True
        except Exception as e:
            # Log the specific Supabase-related error message if possible, or just the general error
            logger.error(f"Error adding account {email} to Supabase: {e}", exc_info=True) # Use exc_info for full traceback
            return False

    def get_account_credentials(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves account credentials dictionary from Supabase."""
        if not self._check_supabase(): return None
        if not account_id:
            logger.warning("No account_id provided to get_account_credentials.")
            return None
        try:
            response = self.supabase.table('tokens').select('token_data').eq('user_id', account_id).eq('token_type', 'google').limit(1).execute()
            if response.data:
                token_json = response.data[0]['token_data']
                credentials_dict = json.loads(token_json)
                # Ensure necessary keys for refresh are present (they should be from to_json)
                if 'client_id' not in credentials_dict or 'client_secret' not in credentials_dict:
                     logger.warning(f"Credentials for {account_id} missing client_id or client_secret. Refresh may fail.")
                     # Augment with config if missing, though they *should* be in the stored JSON
                     credentials_dict.setdefault('client_id', GOOGLE_CREDENTIALS['web']['client_id'])
                     credentials_dict.setdefault('client_secret', GOOGLE_CREDENTIALS['web']['client_secret'])
                     credentials_dict.setdefault('token_uri', GOOGLE_CREDENTIALS['web']['token_uri'])

                return credentials_dict
            else:
                logger.warning(f"No credentials found in Supabase for account {account_id}.")
                return None
        except Exception as e:
            logger.error(f"Error getting credentials for {account_id} from Supabase: {e}", exc_info=True)
            return None

    def remove_account(self, account_id: str) -> bool:
        """Removes an account from Supabase."""
        if not self._check_supabase(): return False
        if not account_id:
            logger.warning("No account_id provided to remove_account.")
            return False
        try:
            data, count = self.supabase.table('tokens').delete().eq('user_id', account_id).eq('token_type', 'google').execute()
            if count > 0: # Check if deletion happened
                 logger.info(f"Successfully removed account {account_id} from Supabase.")
                 # If removing the default, reset default
                 if self.default_account_id == account_id:
                     self.default_account_id = None
                     logger.info("Removed default account assignment.")
                 return True
            else:
                 logger.warning(f"Account {account_id} not found in Supabase for removal or delete failed.")
                 return False # Account might not have existed
        except Exception as e:
            logger.error(f"Error removing account {account_id} from Supabase: {e}", exc_info=True)
            return False

    def get_accounts(self) -> Dict[str, Dict[str, Any]]:
        """Lists all configured Gmail accounts from Supabase."""
        accounts_details = {}
        if not self._check_supabase(): return accounts_details
        try:
            response = self.supabase.table('tokens').select('user_id, token_data').eq('token_type', 'google').execute()
            if response.data:
                for record in response.data:
                    account_id = record['user_id']
                    try:
                        token_data = json.loads(record['token_data'])
                        # Extract expiry and scopes safely
                        expiry_str = token_data.get("expiry") # Google creds use 'expiry' key from `to_json`
                        scopes = token_data.get("scopes", [])

                        serializable_expiry = None
                        if expiry_str and isinstance(expiry_str, str):
                             try:
                                 # Validate format but keep the string
                                 datetime.datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                                 serializable_expiry = expiry_str
                             except ValueError:
                                 logger.warning(f"Invalid expiry format for {account_id}: {expiry_str}. Setting expiry to None.")
                                 serializable_expiry = None

                        accounts_details[account_id] = {
                            "scopes": scopes,
                            "expiry": serializable_expiry
                        }
                    except json.JSONDecodeError:
                        logger.error(f"Could not parse token data for account {account_id}. Skipping.")
                    except Exception as parse_err:
                         logger.error(f"Error processing account details for {account_id}: {parse_err}")

            # Set default if not already set and accounts exist
            if self.default_account_id is None and accounts_details:
                 self.default_account_id = next(iter(accounts_details))
                 logger.info(f"Set {self.default_account_id} as the default account for this session.")

            return accounts_details

        except Exception as e:
            logger.error(f"Unexpected error listing accounts from Supabase: {e}", exc_info=True)
            return {}

    def get_default_account(self) -> Optional[str]:
        """Gets the default account ID determined during the session."""
        # Ensure accounts are loaded if default isn't set yet
        if self.default_account_id is None:
             self.get_accounts() # Attempt to load accounts and set default
        return self.default_account_id

# Initialize the account manager with the Supabase client
account_manager = GmailSupabaseManager(supabase)
# --- End Refactored Manager ---

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

def get_credentials(account_id: str) -> Optional[Credentials]:
    """Get valid credentials for Gmail API from Supabase. Handles refresh."""
    logger.debug(f"Attempting to get credentials for account_id: {account_id}")
    try:
        # Get credentials dictionary from Supabase via manager
        credentials_dict = account_manager.get_account_credentials(account_id)
        if not credentials_dict:
            logger.error(f"Account {account_id} credentials not found in Supabase.")
            return None

        # Create credentials object from dictionary
        # This dictionary should contain token, refresh_token, token_uri, client_id, client_secret, scopes
        creds = Credentials.from_authorized_user_info(credentials_dict)

        # Check if credentials need refresh
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                logger.info(f"Credentials for {account_id} expired. Attempting refresh.")
                try:
                    # The required info (client_id, client_secret, token_uri) should be in 'creds'
                    # derived from credentials_dict loaded by from_authorized_user_info
                    creds.refresh(Request())
                    logger.info(f"Credentials for {account_id} refreshed successfully.")
                    # Update token in Supabase
                    account_manager.add_account(account_id, creds) # Use add_account which upserts
                except Exception as e:
                    logger.error(f"Failed to refresh credentials for {account_id}: {e}", exc_info=True)
                    # Optionally: remove broken credentials?
                    # account_manager.remove_account(account_id)
                    return None
            else:
                logger.error(f"Credentials for {account_id} are invalid or expired, and no refresh token is available.")
                # Optionally remove invalid creds
                # account_manager.remove_account(account_id)
                return None

        logger.debug(f"Valid credentials obtained for {account_id}.")
        return creds

    except Exception as e:
        logger.error(f"Error getting or refreshing credentials for {account_id}: {e}", exc_info=True)
        return None

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

        # Get message list
        request = service.users().messages().list(userId='me', maxResults=max_results)
        results = execute_with_retry(request)

        if not results or 'messages' not in results:
            logger.info(f"No messages found for account {actual_account_id}")
            return GmailMessageResponse(
                status="success",
                account=actual_account_id,
                messages=[],
                report="No messages found",
                error_message=None
            )

        messages = results['messages']
        message_details_list = []
        batch_errors = []

        # Define batch callback function
        def callback(request_id, response, exception):
            nonlocal batch_errors # Allow modifying outer scope variable
            if exception:
                error_msg = f"Error fetching message {request_id}: {exception}"
                logger.error(error_msg)
                batch_errors.append(error_msg)
                # Optionally check if exception is retryable HttpError and handle if needed
                return
            if response:
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

        # Add requests to batch (Consider smaller batch sizes if needed, e.g., 50 or 100)
        batch = service.new_batch_http_request()
        for msg in messages:
            # Check quota per message get (Consider removing if relying solely on retry)
            # if not quota_manager.check_quota("users.messages.get", actual_account_id):
            #     logger.warning(f"Quota possibly exceeded for users.messages.get on account {actual_account_id}, skipping message {msg['id']}")
            #     batch_errors.append(f"Quota likely exceeded before fetching message {msg['id']}")
            #     continue # Skip adding this request if quota might be hit

            get_request = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="full" # Fetch full details
            )
            batch.add(get_request, callback=callback, request_id=msg["id"])

        # Execute batch request with retry
        if batch._order: # Check if batch has requests before executing
            try:
                 execute_with_retry(batch)
            except Exception as batch_exec_err:
                logger.error(f"Batch execution failed for account {actual_account_id}: {batch_exec_err}", exc_info=True)
                # Decide if this is a fatal error for the whole function
                return GmailMessageResponse(
                    status="error",
                    account=actual_account_id,
                    messages=[],
                    report="Failed to retrieve message details due to batch execution error.",
                    error_message=f"Batch execution failed: {str(batch_exec_err)}"
                )

        # Report results and errors
        report_message = f"Retrieved {len(message_details_list)} messages for account {actual_account_id}."
        if batch_errors:
            report_message += f" Encountered {len(batch_errors)} errors during fetch: {'; '.join(batch_errors[:3])}{'...' if len(batch_errors) > 3 else ''}"
            logger.warning(f"Batch errors for account {actual_account_id}: {batch_errors}")

        # Sort messages by date (optional, requires parsing date strings)
        try:
            # Example sorting - requires robust date parsing, omitted for brevity
            # message_details_list.sort(key=lambda x: parse_date(x['date']), reverse=True)
            pass
        except Exception as sort_err:
            logger.warning(f"Could not sort messages by date: {sort_err}")


        return GmailMessageResponse(
            status="success", # Report success even if some messages failed
            account=actual_account_id,
            messages=message_details_list,
            report=report_message,
            error_message=f"{len(batch_errors)} errors fetching details." if batch_errors else None
        )

    except HttpError as error:
        logger.error(f"An API error occurred in get_gmail_messages for {target_account_id}: {error}", exc_info=True)
        return GmailMessageResponse(
            status="error",
            account=target_account_id,
            messages=[],
            report=f"API error accessing account {target_account_id}",
            error_message=f"Gmail API error: {error}"
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred in get_gmail_messages for {target_account_id}: {e}", exc_info=True)
        return GmailMessageResponse(
            status="error",
            account=target_account_id,
            messages=[],
            report=f"Unexpected error accessing account {target_account_id}",
            error_message=f"Unexpected error: {str(e)}"
        )


def get_gmail_messages_for_account(account_id: str, max_results: int = 10) -> Union[GmailMessageResponse, GmailErrorResponse]:
    """Get recent messages from a specific Gmail account using batch operations."""
    logger.info(f"Fetching messages for account {account_id} with max_results={max_results}")
    # This function now essentially wraps get_gmail_messages
    # We pass the specific account_id directly
    response = get_gmail_messages(account_id=account_id, max_results=max_results)

    # Convert the response format if necessary or return directly
    if response['status'] == 'success':
        # The return type of get_gmail_messages matches GmailMessageResponse
        return response
    else:
        # Return as GmailErrorResponse if it was an error
        return GmailErrorResponse(
            status="error",
            error_message=response.get('error_message', 'Unknown error occurred')
        )


def search_gmail_with_query(query: str, max_results: int = 10, account_id: Optional[str] = None) -> Union[GmailSearchResponse, GmailErrorResponse]:
    """Search Gmail messages with the given query, using batch operations for details."""
    try:
        search_query = query # Use provided query directly
        logger.info(f"Searching Gmail with query='{search_query}', max_results={max_results}, account_id='{account_id or 'all'}'")

        accounts_to_search = []
        if account_id:
            # Verify the single account exists
            if account_manager.get_account_credentials(account_id):
                accounts_to_search.append(account_id)
            else:
                logger.warning(f"Specified account_id '{account_id}' not found for search.")
                return GmailErrorResponse(status="error", error_message=f"Account '{account_id}' not found.")
        else:
            # Get all configured accounts
            all_accounts = account_manager.get_accounts()
            if not all_accounts:
                logger.warning("No Gmail accounts configured for search.")
                return GmailSearchResponse(
                    status="success", # Or maybe error? debatable. Success=search ran, no accounts.
                    account="none",
                    report="No Gmail accounts configured.",
                    emails=[],
                    accounts_searched=[],
                    accounts_with_results=[],
                    total_accounts=0
                )
            accounts_to_search = list(all_accounts.keys())

        logger.info(f"Accounts to search: {accounts_to_search}")
        all_results = []
        accounts_with_data = []
        total_accounts_searched = len(accounts_to_search)

        # Search each account sequentially, but use batching within each account search
        for acc_id in accounts_to_search:
            logger.debug(f"Searching account: {acc_id}")
            # Use the internal implementation which now uses batching
            result = _search_gmail_impl(acc_id, search_query, max_results)

            if result["status"] == "success":
                account_messages = result.get("messages", [])
                if account_messages:
                    # Add account_id to each message for traceability if needed later
                    # for msg in account_messages:
                    #     msg['account_id'] = acc_id
                    all_results.extend(account_messages)
                    accounts_with_data.append(acc_id)
                    logger.debug(f"Found {len(account_messages)} messages in account {acc_id}")
                else:
                     logger.debug(f"No messages found matching query in account {acc_id}")
            else:
                # Log the error for this specific account but continue searching others
                logger.error(f"Error searching account {acc_id}: {result.get('error_message', 'Unknown error')}")


        # Combine and sort results (optional, consider date parsing complexity)
        # Example: all_results.sort(key=lambda x: parse_date(x['date']), reverse=True)
        # Limit total results across all accounts
        final_results = all_results[:max_results]
        logger.info(f"Total messages found across searched accounts: {len(all_results)}. Returning top {len(final_results)}.")


        return GmailSearchResponse(
            status="success",
            account=account_id or "all",
            report=f"Found {len(final_results)} messages matching query across {len(accounts_with_data)}/{total_accounts_searched} accounts.",
            # Renamed 'emails' to 'messages' to align with other responses
            emails=final_results, # Keep 'emails' for consistency with original type hint? Let's keep it.
            accounts_searched=accounts_to_search,
            accounts_with_results=accounts_with_data,
            total_accounts=total_accounts_searched
        )

    except Exception as e:
        logger.error(f"Unexpected error during Gmail search: {e}", exc_info=True)
        return GmailErrorResponse(
            status="error",
            error_message=f"Unexpected error during search: {str(e)}"
        )


def _search_gmail_impl(account_id: str, query: str, max_results: int) -> Union[GmailMessageResponse, GmailErrorResponse]:
    """Internal implementation of Gmail search using batch requests for message details."""
    logger.debug(f"Executing search query '{query}' for account {account_id}, max_results={max_results}")
    service_result = get_gmail_service(account_id)
    if service_result["status"] == "error":
        # Propagate the error from get_gmail_service
        return GmailErrorResponse(
            status="error",
            error_message=service_result.get("error_message", f"Failed to get service for {account_id}")
        )

    service = service_result["service"]

    try:
        # 1. Search for message IDs
        list_request = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results # Limit the number of IDs returned initially
        )
        results = execute_with_retry(list_request)

        if not results or 'messages' not in results:
            logger.debug(f"No messages found matching query '{query}' in account {account_id}")
            return GmailMessageResponse(
                status="success",
                account=account_id,
                messages=[],
                report="No messages found matching query",
                error_message=None
            )

        messages_ids = results['messages']
        logger.debug(f"Found {len(messages_ids)} message IDs matching query in {account_id}.")

        # 2. Fetch full message details using batch request
        message_details_list = []
        batch_errors = []

        # Define batch callback function (similar to get_gmail_messages)
        def callback(request_id, response, exception):
            nonlocal batch_errors
            if exception:
                error_msg = f"Error fetching message {request_id} during search: {exception}"
                logger.error(error_msg)
                batch_errors.append(error_msg)
                return
            if response:
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
                    error_msg = f"Error processing message {response.get('id', '[unknown ID]')} in search batch callback: {proc_err}"
                    logger.error(error_msg, exc_info=True)
                    batch_errors.append(error_msg)

        # Add requests to batch
        batch = service.new_batch_http_request()
        for msg in messages_ids:
            get_request = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="full"
            )
            batch.add(get_request, callback=callback, request_id=msg["id"])

        # Execute batch request with retry
        if batch._order:
             try:
                 execute_with_retry(batch)
             except Exception as batch_exec_err:
                logger.error(f"Batch execution failed during search for account {account_id}: {batch_exec_err}", exc_info=True)
                # Return partial results or error? Let's return error for the impl function.
                return GmailErrorResponse(
                    status="error",
                    error_message=f"Batch execution failed while fetching details: {str(batch_exec_err)}"
                )

        report_message = f"Successfully searched account {account_id}. Fetched details for {len(message_details_list)}/{len(messages_ids)} messages."
        if batch_errors:
            report_message += f" Encountered {len(batch_errors)} errors during detail fetch."
            logger.warning(f"Search batch errors for account {account_id}: {batch_errors}")

        # Return results matching GmailMessageResponse format
        return GmailMessageResponse(
            status="success", # Success in searching, even if some details failed
            account=account_id,
            messages=message_details_list,
            report=report_message,
            error_message=f"{len(batch_errors)} errors fetching details." if batch_errors else None
        )

    except HttpError as error:
        logger.error(f"An API error occurred in _search_gmail_impl for {account_id}: {error}", exc_info=True)
        return GmailErrorResponse(
            status="error",
            error_message=f"Gmail API error during search: {error}"
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred in _search_gmail_impl for {account_id}: {e}", exc_info=True)
        return GmailErrorResponse(
            status="error",
            error_message=f"Unexpected error during search implementation: {str(e)}"
        )

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
        # Search across all accounts - use the existing account_manager
        # account_manager = GmailSupabaseManager(supabase)
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

def add_new_gmail_account() -> GmailAccountResponse:
    """Add a new Gmail account. Triggers OAuth login flow via browser. Stores credentials in Supabase, identified by the email address obtained during auth."""
    logger.info("Initiating add new Gmail account process.")
    if supabase is None:
         logger.error("Supabase client is not available. Cannot add new account.")
         return GmailAccountResponse(
             status="error",
             message="Backend storage (Supabase) is not configured or available.",
             error_message="Supabase client not initialized."
         )

    # Call the internal function that handles the flow and storage
    success, email_added, error_msg = _authenticate_and_store_new_account(account_manager)

    if success and email_added:
        return GmailAccountResponse(
            status="success",
            message=f"Successfully authenticated and added Gmail account: {email_added}",
            error_message=None
        )
    else:
        # _authenticate_and_store_new_account logs specifics
        return GmailAccountResponse(
            status="error",
            message=f"Failed to add new Gmail account. Reason: {error_msg or 'Unknown error during authentication/storage.'}",
            error_message=error_msg or "Authentication or storage failed."
        )

def remove_gmail_account(account_id: str) -> GmailAccountResponse:
    """Remove a Gmail account by email (account_id) from Supabase."""
    if not account_id:
        return GmailAccountResponse(
            status="error",
            message="No account_id provided",
            error_message="No account_id provided"
        )
    # Use the manager method
    removed = account_manager.remove_account(account_id)
    if removed:
        return GmailAccountResponse(
            status="success",
            message=f"Successfully removed Gmail account: {account_id}",
            error_message=None
        )
    # Manager logs if not found, return generic error here
    return GmailAccountResponse(
        status="error",
        message=f"Failed to remove account {account_id}. It might not exist or an error occurred.",
        error_message="Account removal failed or account not found."
    )

def list_gmail_accounts() -> GmailAccountListResponse:
    """List all configured Gmail accounts stored in Supabase"""
    try:
        # Use the manager method
        accounts = account_manager.get_accounts()
        return GmailAccountListResponse(
            status="success",
            accounts=accounts,
            error_message=None
        )
    except Exception as e:
        logger.error(f"Error listing Gmail accounts: {e}", exc_info=True)
        return GmailAccountListResponse(
            status="error",
            accounts={},
            error_message=f"Error listing Gmail accounts: {str(e)}"
        )

# --- New Authentication Flow Function ---
def _authenticate_and_store_new_account(manager: GmailSupabaseManager) -> Tuple[bool, Optional[str], Optional[str]]:
    """Runs the OAuth flow, gets email, and stores credentials in Supabase."""
    logger.info("Starting new account authentication flow using client config.")
    credentials = None
    
    # First check if the port is already in use
    auth_port = 8080  # Default port
    if is_port_in_use(auth_port):
        # Try to find an alternative port that's available
        try:
            auth_port = find_free_port()
            logger.info(f"Port 8080 is in use, using alternative port: {auth_port}")
            # Check if this port is in the allowed redirect URIs
            valid_port = False
            for uri in GOOGLE_CREDENTIALS['web']['redirect_uris']:
                if f":{auth_port}" in uri:
                    valid_port = True
                    break
            
            if not valid_port:
                error_msg = f"Port {auth_port} is not in the allowed redirect URIs. Please add http://localhost:{auth_port}/ to your Google Cloud Console."
                logger.error(error_msg)
                print(f"\n⚠️ {error_msg}")
                print("Using port 8080 anyway, but authentication may fail.")
                auth_port = 8080
        except Exception as port_err:
            logger.error(f"Error finding free port: {port_err}")
            auth_port = 8080  # Fallback to default
            print("\n⚠️ Could not find a free port. Authentication may fail if port 8080 is already in use.")
    
    try:
        flow = InstalledAppFlow.from_client_config(
            GOOGLE_CREDENTIALS,
            SCOPES,
            # redirect_uri='http://localhost:8080/' # Usually inferred for loopback
        )

        # Run local server with clear instructions
        logger.info(f"Attempting to run local server on port {auth_port} for authentication.")
        print(f"\n>>> Please look for a browser window/tab opening for Google Authorization.")
        print(f">>> If no browser window opens automatically, open this URL manually: http://localhost:{auth_port}")
        print(f">>> YOU MUST COMPLETE THE AUTHORIZATION PROCESS by clicking 'Continue' and granting access.")
        print(f">>> The app will wait for up to 5 minutes for you to complete this process.")

        # Add timeout to detect when user doesn't complete the flow
        import threading
        oauth_completed = threading.Event()
        oauth_error = [None]  # Using list as mutable container

        def oauth_timeout_handler():
            if not oauth_completed.is_set():
                oauth_error[0] = "OAuth flow timed out. You may need to manually close the browser window."
                logger.error("OAuth flow timed out after waiting period.")
                # Can't really cancel the flow, but at least we can inform the user

        # Set a 5-minute timeout
        timer = threading.Timer(300, oauth_timeout_handler)
        timer.daemon = True
        timer.start()

        try:
            # Run the OAuth flow with the server
            credentials = flow.run_local_server(
                port=auth_port,
                access_type='offline',  # Request refresh token
                prompt='consent',       # Ensure user always sees consent screen
                timeout_seconds=300     # 5-minute timeout
            )
            oauth_completed.set()  # Mark flow as completed
            logger.info("InstalledAppFlow local server completed successfully.")
        except Exception as flow_err:
            oauth_error[0] = str(flow_err)
            raise

        # Cancel the timer if not expired yet
        timer.cancel()

        # Check if there was a timeout
        if oauth_error[0] is not None:
            print(f"\n⚠️ {oauth_error[0]}")
            return False, None, f"Authorization process not completed: {oauth_error[0]}"

    except FileNotFoundError:
        # This shouldn't happen with from_client_config unless GOOGLE_CREDENTIALS is bad
        logger.error("Error during authentication flow setup (invalid config?)", exc_info=True)
        return False, None, "Authentication flow setup failed (invalid config?)."
    except Exception as server_err:
        logger.error(f"Error during OAuth local server: {server_err}", exc_info=True)
        print(f"\n⚠️ Error during authentication: {server_err}")
        
        # Provide helpful suggestions based on error type
        if "failed to start" in str(server_err).lower() or "address already in use" in str(server_err).lower():
            print(f"\nThis may be because port {auth_port} is already in use.")
            print("Try closing other applications that might be using this port or restart your computer.")
        elif "timeout" in str(server_err).lower() or "timed out" in str(server_err).lower():
            print("\nThe authorization process timed out because it wasn't completed in time.")
            print("Please try again and be sure to complete the Google authorization steps.")
        elif "cancelled" in str(server_err).lower() or "denied" in str(server_err).lower():
            print("\nIt appears you cancelled or denied the authorization request.")
            print("You need to approve the request to grant access to your Gmail account.")
        
        return False, None, f"OAuth local server failed: {server_err}"

    if not credentials or not credentials.refresh_token:
        logger.error("Failed to obtain valid credentials or refresh token.")
        print("\n⚠️ Did not receive valid credentials or refresh token!")
        print("This might happen if you denied access or closed the browser too early.")
        print("Next steps to try:")
        print("1. Revoke app access in your Google Account settings: https://myaccount.google.com/permissions")
        print("2. Clear your browser cookies for Google accounts")
        print("3. Try again and make sure to complete all authorization steps")
        return False, None, "Failed to obtain valid credentials or refresh token."

    # Credentials obtained, now get email and store
    try:
        logger.info("Credentials obtained. Getting user profile email.")
        temp_service = build('gmail', 'v1', credentials=credentials)
        profile = temp_service.users().getProfile(userId='me').execute()
        email = profile.get('emailAddress')

        if not email:
            logger.error("Could not retrieve email address from profile.")
            return False, None, "Failed to retrieve email address after authentication."

        logger.info(f"Successfully authenticated as: {email}. Storing credentials.")
        # Store using the manager
        success = manager.add_account(email, credentials)

        if success:
            logger.info(f"Credentials for {email} stored successfully in Supabase.")
            print(f"\n✅ Successfully authenticated {email} and stored credentials!")
            return True, email, None
        else:
            logger.error(f"Failed to store credentials for {email} in Supabase.")
            print(f"\n⚠️ Authentication succeeded for {email}, but failed to store credentials.")
            return False, email, "Failed to store credentials in backend."

    except HttpError as api_err:
        logger.error(f"API error getting profile for new account: {api_err}", exc_info=True)
        return False, None, f"API error getting profile: {api_err}"
    except Exception as e:
        logger.error(f"Error getting profile or storing credentials: {e}", exc_info=True)
        return False, None, f"Error processing credentials: {e}"
# --- End New Auth Flow ---


# Gmail functionality (modified get_gmail_service)
def get_gmail_service(account_id: Optional[str] = None) -> GmailServiceResponse:
    """Get Gmail service for specified account using credentials from Supabase."""
    try:
        # Determine the target account ID
        target_account_id = account_id or account_manager.get_default_account()
        if not target_account_id:
            # Try loading accounts again if default is None
            if account_id is None:
                 all_accounts = account_manager.get_accounts()
                 if all_accounts:
                     target_account_id = next(iter(all_accounts)) # Get first available
                     logger.info(f"No default account set, using first available: {target_account_id}")
                 else:
                     logger.error("No account ID provided and no accounts found in Supabase.")
                     return GmailServiceResponse(
                         status="error",
                         error_message="No account ID specified and no accounts configured.",
                         service=None,
                         account=None
                     )
            else: # account_id was specified but not found previously as default
                 # We'll let get_credentials handle the "not found" case for a specific ID
                 target_account_id = account_id


        logger.info(f"Getting Gmail service for account: {target_account_id}")
        # Get credentials using the refreshed function
        credentials = get_credentials(target_account_id)

        if not credentials:
            # get_credentials logs the specific error
            return GmailServiceResponse(
                status="error",
                error_message=f"Failed to get valid credentials for account {target_account_id}",
                service=None,
                account=target_account_id
            )

        # Build the service
        service = build('gmail', 'v1', credentials=credentials)
        logger.info(f"Successfully built Gmail service for {target_account_id}")
        return GmailServiceResponse(
            status="success",
            error_message=None,
            service=service,
            account=target_account_id # Return the account ID used
        )
    except Exception as e:
        # Catch-all for unexpected errors during service acquisition
        logger.error(f"Unexpected error getting Gmail service for account '{account_id}': {e}", exc_info=True)
        return GmailServiceResponse(
            status="error",
            error_message=f"Unexpected error building service: {str(e)}",
            service=None,
            account=account_id # Return the requested ID even on failure
        )


        