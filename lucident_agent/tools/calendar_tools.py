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
from tenacity import retry, stop_after_attempt, wait_exponential
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from supabase import create_client, Client

# Import Database class
from lucident_agent.Database import Database
# Import Config class for TIMEZONE
from lucident_agent.config import Config

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the scopes needed for Calendar API
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]

# Constants
DEFAULT_ACCOUNT = 'default'
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 1  # seconds
TIMEZONE = Config.TIMEZONE  # Use timezone from Config class

# --- Use Database class for Supabase access ---
try:
    db = Database()
    supabase = db.client
    logger.info("Supabase client initialized via Database class.")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client via Database: {e}")
    supabase = None

# Hardcoded Google Credentials (using the same as Gmail)
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

# --- CalendarSupabaseManager Class ---
class CalendarSupabaseManager:
    """Manages Calendar account credentials using Supabase."""
    def __init__(self, supabase_client: Optional[Client]):
        if supabase_client is None:
            logger.error("Supabase client not provided to CalendarSupabaseManager.")
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
                'token_type': 'google_calendar',
                'token_data': token_json
            }, on_conflict='user_id, token_type').execute() # Specify conflict target if composite key

            logger.info(f"Successfully upserted Calendar credentials for {email} in Supabase.")
            # Set as default if it's the first account added in this session
            if self.default_account_id is None:
                self.default_account_id = email
                logger.info(f"Set {email} as the default Calendar account for this session.")
            return True
        except Exception as e:
            logger.error(f"Error adding Calendar account {email} to Supabase: {e}", exc_info=True)
            return False

    def get_account_credentials(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves account credentials dictionary from Supabase."""
        if not self._check_supabase(): return None
        if not account_id:
            logger.warning("No account_id provided to get_account_credentials.")
            return None
        try:
            response = self.supabase.table('tokens').select('token_data').eq('user_id', account_id).eq('token_type', 'google_calendar').limit(1).execute()
            if response.data:
                token_json = response.data[0]['token_data']
                credentials_dict = json.loads(token_json)
                # Ensure necessary keys for refresh are present
                if 'client_id' not in credentials_dict or 'client_secret' not in credentials_dict:
                     logger.warning(f"Credentials for {account_id} missing client_id or client_secret. Refresh may fail.")
                     credentials_dict.setdefault('client_id', GOOGLE_CREDENTIALS['web']['client_id'])
                     credentials_dict.setdefault('client_secret', GOOGLE_CREDENTIALS['web']['client_secret'])
                     credentials_dict.setdefault('token_uri', GOOGLE_CREDENTIALS['web']['token_uri'])

                return credentials_dict
            else:
                logger.warning(f"No Calendar credentials found in Supabase for account {account_id}.")
                return None
        except Exception as e:
            logger.error(f"Error getting Calendar credentials for {account_id} from Supabase: {e}", exc_info=True)
            return None

    def get_accounts(self) -> Dict[str, Dict[str, Any]]:
        """Lists all configured Calendar accounts from Supabase."""
        accounts_details = {}
        if not self._check_supabase(): return accounts_details
        try:
            response = self.supabase.table('tokens').select('user_id, token_data').eq('token_type', 'google_calendar').execute()
            if response.data:
                for record in response.data:
                    account_id = record['user_id']
                    try:
                        token_data = json.loads(record['token_data'])
                        # Extract expiry and scopes safely
                        expiry_str = token_data.get("expiry")
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
            return accounts_details
        except Exception as e:
            logger.error(f"Error getting Calendar accounts from Supabase: {e}", exc_info=True)
            return {}

    def remove_account(self, account_id: str) -> bool:
        """Removes an account from Supabase."""
        if not self._check_supabase(): return False
        if not account_id:
            logger.warning("No account_id provided to remove_account.")
            return False
        try:
            response = self.supabase.table('tokens').delete().eq('user_id', account_id).eq('token_type', 'google_calendar').execute()
            logger.info(f"Removed Calendar account {account_id} from Supabase.")
            # If this was the default account, clear default
            if self.default_account_id == account_id:
                self.default_account_id = None
            return True
        except Exception as e:
            logger.error(f"Error removing Calendar account {account_id} from Supabase: {e}", exc_info=True)
            return False

    def set_default_account(self, account_id: str) -> bool:
        """Sets the default account for this session."""
        if not account_id:
            logger.warning("No account_id provided to set_default_account.")
            return False
        # Check if account exists first
        if self._check_supabase():
            try:
                response = self.supabase.table('tokens').select('user_id').eq('user_id', account_id).eq('token_type', 'google_calendar').limit(1).execute()
                if not response.data:
                    logger.warning(f"Cannot set {account_id} as default: account not found.")
                    return False
            except Exception as e:
                logger.error(f"Error checking if account {account_id} exists: {e}", exc_info=True)
                return False
        
        self.default_account_id = account_id
        logger.info(f"Set {account_id} as the default Calendar account for this session.")
        return True

    def get_default_account(self) -> Optional[str]:
        """Returns the current default account ID."""
        return self.default_account_id

# Initialize calendar account manager
account_manager = CalendarSupabaseManager(supabase)

# --- Helper Functions ---
def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_free_port() -> int:
    """Find a free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def get_credentials(account_id: str) -> Optional[Credentials]:
    """Get valid credentials for Calendar API from Supabase. Handles refresh."""
    logger.debug(f"Attempting to get Calendar credentials for account_id: {account_id}")
    try:
        # Get credentials dictionary from Supabase via manager
        credentials_dict = account_manager.get_account_credentials(account_id)
        if not credentials_dict:
            logger.error(f"Calendar account {account_id} credentials not found in Supabase.")
            return None

        # Create credentials object from dictionary
        creds = Credentials.from_authorized_user_info(credentials_dict)

        # Check if credentials need refresh
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                logger.info(f"Calendar credentials for {account_id} expired. Attempting refresh.")
                try:
                    creds.refresh(Request())
                    logger.info(f"Calendar credentials for {account_id} refreshed successfully.")
                    # Update token in Supabase
                    account_manager.add_account(account_id, creds)
                except Exception as e:
                    logger.error(f"Failed to refresh Calendar credentials for {account_id}: {e}", exc_info=True)
                    return None
            else:
                logger.error(f"Calendar credentials for {account_id} are invalid or expired, and no refresh token is available.")
                return None

        logger.debug(f"Valid Calendar credentials obtained for {account_id}.")
        return creds

    except Exception as e:
        logger.error(f"Error getting or refreshing Calendar credentials for {account_id}: {e}", exc_info=True)
        return None

def build_calendar_service(account_id: str) -> Optional[Any]:
    """Build a Calendar API service using credentials for the given account."""
    try:
        creds = get_credentials(account_id)
        if not creds:
            logger.error(f"Could not get valid credentials for Calendar account {account_id}.")
            return None
        
        service = build("calendar", "v3", credentials=creds)
        logger.info(f"Successfully built Calendar service for account {account_id}.")
        return service
    except Exception as e:
        logger.error(f"Error building Calendar service for account {account_id}: {e}", exc_info=True)
        return None

@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=2, max=10))
def execute_with_retry(request_fn):
    """Execute an API request with retry and rate limit handling."""
    try:
        response = request_fn.execute()
        time.sleep(RATE_LIMIT_DELAY)  # Basic rate limiting
        return response
    except HttpError as e:
        if e.resp.status in [403, 429]:  # Rate limit errors
            logger.warning(f"Rate limit hit: {e}, retrying with exponential backoff...")
            time.sleep(RATE_LIMIT_DELAY * 2)  # Additional delay on rate limit
            raise  # Let retry handle it
        elif e.resp.status in [401, 400]:  # Auth errors
            logger.error(f"Authentication error: {e}")
            raise  # Don't retry auth errors
        else:
            logger.error(f"HTTP Error during Calendar API call: {e}")
            raise  # Let retry handle it
    except Exception as e:
        logger.error(f"Unexpected error during Calendar API call: {e}")
        raise  # Let retry handle it

# --- Type Definitions ---
class CalendarAccountResponse(TypedDict):
    status: Literal["success", "error"]
    message: str
    error_message: Optional[str]
    data: Optional[Dict[str, Any]]

class CalendarEvent(TypedDict):
    id: str
    summary: str
    description: Optional[str]
    location: Optional[str]
    start: Dict[str, Any]
    end: Dict[str, Any]
    attendees: Optional[List[Dict[str, Any]]]
    reminders: Optional[Dict[str, Any]]
    recurrence: Optional[List[str]]

# --- Main Calendar Functions ---
def list_calendar_accounts() -> CalendarAccountResponse:
    """List all configured Google Calendar accounts."""
    logger.info("Listing all Calendar accounts")
    try:
        accounts = account_manager.get_accounts()
        default_account = account_manager.get_default_account()
        
        accounts_info = {}
        for account_id, details in accounts.items():
            accounts_info[account_id] = {
                "scopes": details.get("scopes", []),
                "expiry": details.get("expiry"),
                "is_default": account_id == default_account
            }
        
        return CalendarAccountResponse(
            status="success",
            message=f"Found {len(accounts)} Calendar accounts.",
            error_message=None,
            data={"accounts": accounts_info}
        )
    except Exception as e:
        logger.error(f"Error listing Calendar accounts: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message="Failed to list Calendar accounts.",
            error_message=str(e),
            data=None
        )

def add_new_calendar_account() -> CalendarAccountResponse:
    """Add a new Google Calendar account. Triggers OAuth login flow via browser. Stores credentials in Supabase."""
    logger.info("Initiating add new Calendar account process.")
    if supabase is None:
         logger.error("Supabase client is not available. Cannot add new account.")
         return CalendarAccountResponse(
             status="error",
             message="Backend storage (Supabase) is not configured or available.",
             error_message="Supabase client not initialized.",
             data=None
         )

    # Check if standard OAuth ports are available before attempting authentication
    ports_to_check = [8080, 8085]  # Default OAuth redirect ports
    busy_ports = []
    
    for port in ports_to_check:
        if is_port_in_use(port):
            busy_ports.append(port)
    
    if len(busy_ports) == len(ports_to_check):
        # All standard ports are busy, show a warning but proceed anyway
        warning_msg = f"All standard OAuth ports {ports_to_check} are in use. Will attempt to find an alternative port."
        logger.warning(warning_msg)
        print(f"\n⚠️ {warning_msg}")
        print("If authentication fails, try these commands to free up the ports:")
        for port in busy_ports:
            print(f"lsof -i :{port} | grep LISTEN")
            print(f"kill -9 <PID>  # Replace <PID> with the process ID from the previous command")

    # Call the internal function that handles the flow and storage
    success, email_added, error_msg = _authenticate_and_store_new_account(account_manager)

    if success and email_added:
        return CalendarAccountResponse(
            status="success",
            message=f"Successfully authenticated and added Calendar account: {email_added}",
            error_message=None,
            data={"account_id": email_added}
        )
    else:
        if "address already in use" in error_msg.lower():
            recovery_steps = (
                "To resolve the 'Address already in use' error:\n"
                "1. Close any other applications that might be using Google authentication\n"
                "2. Restart your browser\n"
                "3. Check and terminate processes using these ports:\n"
                f"   - For port 8080: lsof -i :8080 | grep LISTEN\n"
                f"   - For port 8085: lsof -i :8085 | grep LISTEN\n"
                "4. Kill the processes: kill -9 <PID>\n"
                "5. If all else fails, restart your computer"
            )
            return CalendarAccountResponse(
                status="error",
                message=f"Failed to add new Calendar account due to port conflict. {error_msg}",
                error_message=f"{error_msg}\n\n{recovery_steps}",
                data=None
            )
        else:
            return CalendarAccountResponse(
                status="error",
                message=f"Failed to add new Calendar account. Reason: {error_msg or 'Unknown error during authentication/storage.'}",
                error_message=error_msg or "Authentication or storage failed.",
                data=None
            )

def _authenticate_and_store_new_account(manager: CalendarSupabaseManager) -> Tuple[bool, Optional[str], Optional[str]]:
    """Runs the OAuth flow, gets email, and stores credentials in Supabase."""
    logger.info("Starting new Calendar account authentication flow using client config.")
    credentials = None
    
    # First check if the port is already in use
    auth_port = 8080  # Default port
    if is_port_in_use(auth_port):
        try:
            auth_port = find_free_port()
            logger.info(f"Port 8080 is in use, using alternative port: {auth_port}")
            
            # Look for a matching port in the redirect URIs
            redirect_uris = GOOGLE_CREDENTIALS['web']['redirect_uris']
            valid_port = False
            
            # Check if we have a direct match in the allowed redirect URIs
            for uri in redirect_uris:
                if f":{auth_port}" in uri:
                    valid_port = True
                    break
            
            # Try the alternate port 8085 which is also included in default redirect URIs
            if not valid_port and not is_port_in_use(8085):
                auth_port = 8085
                logger.info(f"Using alternate port from redirect URIs: {auth_port}")
                valid_port = True
            
            # If no valid port is found, inform the user and fallback to another option
            if not valid_port:
                alt_port_msg = f"Port {auth_port} is not in the allowed redirect URIs. Trying to find another available port from the allowed list."
                logger.warning(alt_port_msg)
                print(f"\n⚠️ {alt_port_msg}")
                
                # Try each redirect URI port in sequence
                for uri in redirect_uris:
                    try:
                        uri_parts = uri.split(':')
                        if len(uri_parts) > 2:
                            port_str = uri_parts[2].strip('/')
                            port = int(port_str)
                            if not is_port_in_use(port):
                                auth_port = port
                                valid_port = True
                                logger.info(f"Found available port from redirect URIs: {auth_port}")
                                break
                    except (ValueError, IndexError):
                        continue
                
                if not valid_port:
                    error_msg = "Could not find an available port from the allowed redirect URIs."
                    logger.error(error_msg)
                    print(f"\n❌ {error_msg}")
                    print("Please try again later or restart your computer to free up ports.")
                    return False, None, "No available ports found for OAuth server"
        except Exception as port_err:
            logger.error(f"Error finding free port: {port_err}")
            auth_port = 8080  # Fallback to default
            print("\n⚠️ Could not find a free port. Authentication may fail if port 8080 is already in use.")
    
    try:
        flow = InstalledAppFlow.from_client_config(
            GOOGLE_CREDENTIALS,
            SCOPES
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

        # If credentials were obtained, get the user's email
        if credentials:
            try:
                service = build('calendar', 'v3', credentials=credentials)
                calendar_list = service.calendarList().list().execute()
                primary_calendar = None
                for calendar in calendar_list.get('items', []):
                    if calendar.get('primary', False):
                        primary_calendar = calendar
                        break
                
                if primary_calendar and 'id' in primary_calendar:
                    email = primary_calendar['id']  # ID of primary calendar is user's email
                    logger.info(f"Successfully identified Calendar account email: {email}")
                    
                    # Store credentials in Supabase
                    if manager.add_account(email, credentials):
                        logger.info(f"Successfully stored Calendar credentials for {email} in Supabase.")
                        # Set as default account if none is set
                        if not manager.get_default_account():
                            manager.set_default_account(email)
                        return True, email, None
                    else:
                        logger.error(f"Failed to store Calendar credentials for {email} in Supabase.")
                        return False, email, "Failed to store credentials in backend."
                else:
                    logger.error("Could not identify primary calendar/email from Calendar API.")
                    return False, None, "Could not identify user's primary calendar."
            except Exception as api_err:
                logger.error(f"Error calling Calendar API to get user email: {api_err}", exc_info=True)
                return False, None, f"Error identifying user email: {api_err}"

    except Exception as server_err:
        logger.error(f"Error during OAuth local server: {server_err}", exc_info=True)
        print(f"\n⚠️ Error during authentication: {server_err}")
        
        # Provide helpful suggestions based on error type
        if "failed to start" in str(server_err).lower() or "address already in use" in str(server_err).lower():
            print(f"\nThis may be because port {auth_port} is already in use.")
            print("Try these steps to resolve the issue:")
            print("1. Close any other applications or browser tabs that might be performing Google authentication")
            print("2. Restart your browser")
            print("3. Try terminating processes using these ports with the following command in terminal:")
            print(f"   lsof -i :{auth_port} | grep LISTEN")
            print(f"   kill -9 <PID>  # Replace <PID> with the process ID from the previous command")
            print("4. If the issue persists, restart your computer")
        elif "timeout" in str(server_err).lower() or "timed out" in str(server_err).lower():
            print("\nThe authorization process timed out because it wasn't completed in time.")
            print("Please try again and be sure to complete the Google authorization steps.")
        elif "cancelled" in str(server_err).lower() or "denied" in str(server_err).lower():
            print("\nIt appears you cancelled or denied the authorization request.")
            print("You need to approve the request to grant access to your Google Calendar account.")
        
        return False, None, f"OAuth local server failed: {server_err}"

    return False, None, "Failed to obtain valid credentials or complete authentication."

# --- Calendar Event Operations ---
def list_calendar_events(account_id: str, timeMin: Optional[str] = None, timeMax: Optional[str] = None, maxResults: int = 10) -> CalendarAccountResponse:
    """List events from the user's primary calendar."""
    logger.info(f"Listing calendar events for account {account_id}")
    
    try:
        service = build_calendar_service(account_id)
        if not service:
            return CalendarAccountResponse(
                status="error",
                message=f"Failed to build Calendar service for account {account_id}.",
                error_message="Could not authenticate with Calendar API.",
                data=None
            )
        
        # Set default time range if not provided (today to next 7 days)
        now = datetime.datetime.utcnow()
        if not timeMin:
            timeMin = now.isoformat() + 'Z'  # 'Z' indicates UTC time
        if not timeMax:
            timeMax = (now + datetime.timedelta(days=7)).isoformat() + 'Z'
        
        # Execute the API call with retry logic
        events_result = execute_with_retry(service.events().list(
            calendarId='primary',
            timeMin=timeMin,
            timeMax=timeMax,
            maxResults=maxResults,
            singleEvents=True,
            orderBy='startTime'
        ))
        
        events = events_result.get('items', [])
        return CalendarAccountResponse(
            status="success",
            message=f"Found {len(events)} events for account {account_id}.",
            error_message=None,
            data={"events": events}
        )
    except HttpError as e:
        logger.error(f"HTTP error listing Calendar events for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Error accessing Calendar API for account {account_id}.",
            error_message=str(e),
            data=None
        )
    except Exception as e:
        logger.error(f"Unexpected error listing Calendar events for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Unexpected error listing Calendar events for account {account_id}.",
            error_message=str(e),
            data=None
        )

def create_calendar_event(account_id: str, summary: str, description: Optional[str] = None, 
                         location: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None,
                         attendees: Optional[List[Dict[str, str]]] = None, 
                         reminders: Optional[Dict[str, Any]] = None,
                         recurrence: Optional[List[str]] = None) -> CalendarAccountResponse:
    """Create a new event in the user's primary calendar."""
    logger.info(f"Creating calendar event for account {account_id}")
    
    try:
        service = build_calendar_service(account_id)
        if not service:
            return CalendarAccountResponse(
                status="error",
                message=f"Failed to build Calendar service for account {account_id}.",
                error_message="Could not authenticate with Calendar API.",
                data=None
            )
        
        # Validate required parameters
        if not summary or not start_time or not end_time:
            return CalendarAccountResponse(
                status="error",
                message="Missing required event parameters.",
                error_message="Summary, start time, and end time are required.",
                data=None
            )
        
        # Build the event object
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',  # Default to UTC, user can override
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',  # Default to UTC, user can override
            },
        }
        
        # Add optional fields if provided
        if description:
            event['description'] = description
        if location:
            event['location'] = location
        if attendees:
            event['attendees'] = attendees
        if recurrence:
            event['recurrence'] = recurrence
        if reminders:
            event['reminders'] = reminders
        
        # Execute the API call with retry logic
        created_event = execute_with_retry(service.events().insert(
            calendarId='primary',
            body=event,
            sendUpdates='all'  # Send notifications to attendees
        ))
        
        return CalendarAccountResponse(
            status="success",
            message=f"Event '{summary}' created successfully.",
            error_message=None,
            data={"event": created_event}
        )
    except HttpError as e:
        logger.error(f"HTTP error creating Calendar event for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Error accessing Calendar API for account {account_id}.",
            error_message=str(e),
            data=None
        )
    except Exception as e:
        logger.error(f"Unexpected error creating Calendar event for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Unexpected error creating Calendar event for account {account_id}.",
            error_message=str(e),
            data=None
        )

def create_and_send_calendar_event(account_id: str, summary: str, description: Optional[str] = None, 
                         location: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None,
                         attendees: Optional[List[Dict[str, str]]] = None, 
                         reminders: Optional[Dict[str, Any]] = None,
                         recurrence: Optional[List[str]] = None) -> CalendarAccountResponse:
    """Create a new event in the user's primary calendar and automatically send invites to attendees.
    This combines event creation and invitation in one operation."""
    logger.info(f"Creating calendar event with automatic invite sending for account {account_id}")
    
    try:
        service = build_calendar_service(account_id)
        if not service:
            return CalendarAccountResponse(
                status="error",
                message=f"Failed to build Calendar service for account {account_id}.",
                error_message="Could not authenticate with Calendar API.",
                data=None
            )
        
        # Validate required parameters
        if not summary or not start_time or not end_time:
            return CalendarAccountResponse(
                status="error",
                message="Missing required event parameters.",
                error_message="Summary, start time, and end time are required.",
                data=None
            )
        
        # Build the event object
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',  # Default to UTC, user can override
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',  # Default to UTC, user can override
            },
        }
        
        # Add optional fields if provided
        if description:
            event['description'] = description
        if location:
            event['location'] = location
        if attendees:
            event['attendees'] = attendees
        if recurrence:
            event['recurrence'] = recurrence
        if reminders:
            event['reminders'] = reminders
        
        # Execute the API call with retry logic - explicitly setting sendUpdates to 'all' to send invites
        created_event = execute_with_retry(service.events().insert(
            calendarId='primary',
            body=event,
            sendUpdates='all'  # Always send notifications to attendees
        ))
        
        return CalendarAccountResponse(
            status="success",
            message=f"Event '{summary}' created and invites sent successfully.",
            error_message=None,
            data={"event": created_event}
        )
    except HttpError as e:
        logger.error(f"HTTP error creating Calendar event for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Error accessing Calendar API for account {account_id}.",
            error_message=str(e),
            data=None
        )
    except Exception as e:
        logger.error(f"Unexpected error creating Calendar event for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Unexpected error creating Calendar event for account {account_id}.",
            error_message=str(e),
            data=None
        )

def update_calendar_event(account_id: str, event_id: str, updates: Dict[str, Any]) -> CalendarAccountResponse:
    """Update an existing event in the user's primary calendar."""
    logger.info(f"Updating calendar event {event_id} for account {account_id}")
    
    try:
        service = build_calendar_service(account_id)
        if not service:
            return CalendarAccountResponse(
                status="error",
                message=f"Failed to build Calendar service for account {account_id}.",
                error_message="Could not authenticate with Calendar API.",
                data=None
            )
        
        # First get the existing event
        try:
            event = execute_with_retry(service.events().get(
                calendarId='primary',
                eventId=event_id
            ))
        except HttpError as e:
            if e.resp.status == 404:
                return CalendarAccountResponse(
                    status="error",
                    message=f"Event {event_id} not found.",
                    error_message="The specified event does not exist.",
                    data=None
                )
            raise
        
        # Update the event with the provided updates
        for key, value in updates.items():
            if key in ['start', 'end'] and 'dateTime' in value:
                # Handle special case for start/end time
                event[key] = value
            elif key not in ['id', 'iCalUID', 'etag', 'htmlLink', 'created', 'updated']:
                # Skip immutable fields
                event[key] = value
        
        # Execute the API call with retry logic
        updated_event = execute_with_retry(service.events().update(
            calendarId='primary',
            eventId=event_id,
            body=event,
            sendUpdates='all'  # Send notifications to attendees
        ))
        
        return CalendarAccountResponse(
            status="success",
            message=f"Event {event_id} updated successfully.",
            error_message=None,
            data={"event": updated_event}
        )
    except HttpError as e:
        logger.error(f"HTTP error updating Calendar event for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Error accessing Calendar API for account {account_id}.",
            error_message=str(e),
            data=None
        )
    except Exception as e:
        logger.error(f"Unexpected error updating Calendar event for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Unexpected error updating Calendar event for account {account_id}.",
            error_message=str(e),
            data=None
        )

def delete_calendar_event(account_id: str, event_id: str) -> CalendarAccountResponse:
    """Delete an event from the user's primary calendar."""
    logger.info(f"Deleting calendar event {event_id} for account {account_id}")
    
    try:
        service = build_calendar_service(account_id)
        if not service:
            return CalendarAccountResponse(
                status="error",
                message=f"Failed to build Calendar service for account {account_id}.",
                error_message="Could not authenticate with Calendar API.",
                data=None
            )
        
        # Execute the API call with retry logic
        execute_with_retry(service.events().delete(
            calendarId='primary',
            eventId=event_id,
            sendUpdates='all'  # Send notifications to attendees
        ))
        
        return CalendarAccountResponse(
            status="success",
            message=f"Event {event_id} deleted successfully.",
            error_message=None,
            data=None
        )
    except HttpError as e:
        if e.resp.status == 404:
            return CalendarAccountResponse(
                status="error",
                message=f"Event {event_id} not found.",
                error_message="The specified event does not exist.",
                data=None
            )
        logger.error(f"HTTP error deleting Calendar event for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Error accessing Calendar API for account {account_id}.",
            error_message=str(e),
            data=None
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting Calendar event for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Unexpected error deleting Calendar event for account {account_id}.",
            error_message=str(e),
            data=None
        )

def format_event_with_link(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats a calendar event to include a clickable hyperlink.
    
    Args:
        event (Dict[str, Any]): The calendar event data.
        
    Returns:
        Dict[str, Any]: The event data with a formatted link added.
    """
    formatted_event = event.copy()
    
    # Extract the htmlLink if it exists
    if 'htmlLink' in event:
        formatted_event['link'] = event['htmlLink']
    
    return formatted_event

def get_calendar_event(account_id: str, event_id: str) -> CalendarAccountResponse:
    """Get details of a specific event from the user's primary calendar."""
    logger.info(f"Getting calendar event {event_id} for account {account_id}")
    
    try:
        service = build_calendar_service(account_id)
        if not service:
            return CalendarAccountResponse(
                status="error",
                message=f"Failed to build Calendar service for account {account_id}.",
                error_message="Could not authenticate with Calendar API.",
                data=None
            )
        
        # Execute the API call with retry logic
        try:
            event = execute_with_retry(service.events().get(
                calendarId='primary',
                eventId=event_id
            ))
            
            # Format the event to include the link
            formatted_event = format_event_with_link(event)
            
            return CalendarAccountResponse(
                status="success",
                message=f"Event {event_id} retrieved successfully.",
                error_message=None,
                data={"event": formatted_event}
            )
        except HttpError as e:
            if e.resp.status == 404:
                return CalendarAccountResponse(
                    status="error",
                    message=f"Event {event_id} not found.",
                    error_message="The specified event does not exist.",
                    data=None
                )
            raise
    except HttpError as e:
        logger.error(f"HTTP error getting Calendar event for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Error accessing Calendar API for account {account_id}.",
            error_message=str(e),
            data=None
        )
    except Exception as e:
        logger.error(f"Unexpected error getting Calendar event for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Unexpected error getting Calendar event for account {account_id}.",
            error_message=str(e),
            data=None
        )

def quick_add_calendar_event(account_id: str, text: str) -> CalendarAccountResponse:
    """Quickly add an event to the user's primary calendar using natural language text."""
    logger.info(f"Quick adding calendar event '{text}' for account {account_id}")
    
    try:
        service = build_calendar_service(account_id)
        if not service:
            return CalendarAccountResponse(
                status="error",
                message=f"Failed to build Calendar service for account {account_id}.",
                error_message="Could not authenticate with Calendar API.",
                data=None
            )
        
        # Execute the API call with retry logic
        created_event = execute_with_retry(service.events().quickAdd(
            calendarId='primary',
            text=text,
            sendUpdates='all'  # Send notifications to attendees
        ))
        
        return CalendarAccountResponse(
            status="success",
            message=f"Event '{text}' quick-added successfully.",
            error_message=None,
            data={"event": created_event}
        )
    except HttpError as e:
        logger.error(f"HTTP error quick-adding Calendar event for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Error accessing Calendar API for account {account_id}.",
            error_message=str(e),
            data=None
        )
    except Exception as e:
        logger.error(f"Unexpected error quick-adding Calendar event for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Unexpected error quick-adding Calendar event for account {account_id}.",
            error_message=str(e),
            data=None
        )

def add_event_with_recurrence(account_id: str, summary: str, description: Optional[str] = None,
                            location: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None,
                            attendees: Optional[List[Dict[str, str]]] = None,
                            recurrence_pattern: str = "RRULE:FREQ=DAILY;COUNT=5") -> CalendarAccountResponse:
    """Add a recurring event to the user's primary calendar."""
    logger.info(f"Adding recurring calendar event for account {account_id}")
    
    try:
        service = build_calendar_service(account_id)
        if not service:
            return CalendarAccountResponse(
                status="error",
                message=f"Failed to build Calendar service for account {account_id}.",
                error_message="Could not authenticate with Calendar API.",
                data=None
            )
        
        # Validate required parameters
        if not summary or not start_time or not end_time:
            return CalendarAccountResponse(
                status="error",
                message="Missing required event parameters.",
                error_message="Summary, start time, and end time are required.",
                data=None
            )
        
        # Build the event object
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',  # Default to UTC, user can override
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',  # Default to UTC, user can override
            },
            'recurrence': [recurrence_pattern],
        }
        
        # Add optional fields if provided
        if description:
            event['description'] = description
        if location:
            event['location'] = location
        if attendees:
            event['attendees'] = attendees
        
        # Execute the API call with retry logic
        created_event = execute_with_retry(service.events().insert(
            calendarId='primary',
            body=event,
            sendUpdates='all'  # Send notifications to attendees
        ))
        
        return CalendarAccountResponse(
            status="success",
            message=f"Recurring event '{summary}' created successfully.",
            error_message=None,
            data={"event": created_event}
        )
    except HttpError as e:
        logger.error(f"HTTP error creating recurring Calendar event for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Error accessing Calendar API for account {account_id}.",
            error_message=str(e),
            data=None
        )
    except Exception as e:
        logger.error(f"Unexpected error creating recurring Calendar event for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Unexpected error creating recurring Calendar event for account {account_id}.",
            error_message=str(e),
            data=None
        )

def add_event_with_reminders(account_id: str, summary: str, description: Optional[str] = None,
                           location: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None,
                           attendees: Optional[List[Dict[str, str]]] = None,
                           reminder_minutes: List[int] = [10, 30]) -> CalendarAccountResponse:
    """Add an event with custom reminders to the user's primary calendar."""
    logger.info(f"Adding calendar event with reminders for account {account_id}")
    
    try:
        service = build_calendar_service(account_id)
        if not service:
            return CalendarAccountResponse(
                status="error",
                message=f"Failed to build Calendar service for account {account_id}.",
                error_message="Could not authenticate with Calendar API.",
                data=None
            )
        
        # Validate required parameters
        if not summary or not start_time or not end_time:
            return CalendarAccountResponse(
                status="error",
                message="Missing required event parameters.",
                error_message="Summary, start time, and end time are required.",
                data=None
            )
        
        # Build the reminders
        reminders = {
            'useDefault': False,
            'overrides': [{'method': 'popup', 'minutes': minute} for minute in reminder_minutes]
        }
        
        # Build the event object
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',  # Default to UTC, user can override
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',  # Default to UTC, user can override
            },
            'reminders': reminders,
        }
        
        # Add optional fields if provided
        if description:
            event['description'] = description
        if location:
            event['location'] = location
        if attendees:
            event['attendees'] = attendees
        
        # Execute the API call with retry logic
        created_event = execute_with_retry(service.events().insert(
            calendarId='primary',
            body=event,
            sendUpdates='all'  # Send notifications to attendees
        ))
        
        return CalendarAccountResponse(
            status="success",
            message=f"Event '{summary}' with reminders created successfully.",
            error_message=None,
            data={"event": created_event}
        )
    except HttpError as e:
        logger.error(f"HTTP error creating Calendar event with reminders for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Error accessing Calendar API for account {account_id}.",
            error_message=str(e),
            data=None
        )
    except Exception as e:
        logger.error(f"Unexpected error creating Calendar event with reminders for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Unexpected error creating Calendar event with reminders for account {account_id}.",
            error_message=str(e),
            data=None
        )

def check_free_busy(account_id: str, time_min: str, time_max: str, 
                   calendar_ids: Optional[List[str]] = None) -> CalendarAccountResponse:
    """Check free/busy status for one or more calendars."""
    logger.info(f"Checking free/busy status for account {account_id}")
    
    try:
        # Validate and format date inputs
        try:
            # Ensure time_min and time_max are in RFC3339 format
            time_min_dt = datetime.datetime.fromisoformat(time_min.replace('Z', '+00:00'))
            time_max_dt = datetime.datetime.fromisoformat(time_max.replace('Z', '+00:00'))
            
            # Convert to RFC3339 format with 'Z' for UTC
            time_min = time_min_dt.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+0000', 'Z')
            time_max = time_max_dt.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+0000', 'Z')
            
            logger.info(f"Using time range: {time_min} to {time_max}")
        except ValueError as e:
            logger.error(f"Date format validation error: {e}")
            return CalendarAccountResponse(
                status="error",
                message="Invalid date format provided.",
                error_message=f"Dates must be in ISO format (YYYY-MM-DDTHH:MM:SS[.mmmmmm][+HH:MM]): {e}",
                data=None
            )
        
        service = build_calendar_service(account_id)
        if not service:
            return CalendarAccountResponse(
                status="error",
                message=f"Failed to build Calendar service for account {account_id}.",
                error_message="Could not authenticate with Calendar API.",
                data=None
            )
        
        # If no calendar IDs provided, use the primary calendar
        if not calendar_ids:
            calendar_ids = ['primary']
            logger.info(f"No calendar IDs provided, using primary calendar")
        else:
            logger.info(f"Checking free/busy status for calendars: {calendar_ids}")
        
        # Build the freebusy query
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": calendar_id} for calendar_id in calendar_ids]
        }
        
        # Execute the API call with retry logic
        try:
            freebusy = execute_with_retry(service.freebusy().query(body=body))
            logger.info(f"Successfully retrieved free/busy data")
            
            # Check if the expected response format is received
            if 'calendars' not in freebusy:
                logger.warning(f"Unexpected freebusy response format - 'calendars' key missing: {freebusy}")
                return CalendarAccountResponse(
                    status="error",
                    message="Unexpected API response format",
                    error_message="The API response did not contain the expected 'calendars' data",
                    data={"raw_response": freebusy}
                )
            
            # Look for errors in the response
            has_errors = False
            error_messages = []
            
            for cal_id, cal_data in freebusy.get('calendars', {}).items():
                if 'errors' in cal_data:
                    has_errors = True
                    for error in cal_data['errors']:
                        err_msg = f"Calendar {cal_id}: {error.get('reason', 'Unknown error')}"
                        error_messages.append(err_msg)
                        logger.error(err_msg)
            
            if has_errors:
                return CalendarAccountResponse(
                    status="error",
                    message="Errors occurred when retrieving free/busy information",
                    error_message="; ".join(error_messages),
                    data={"partial_data": freebusy}
                )
            
            # Process response for better LLM consumption
            processed_data = {
                "queried_time_range": {
                    "start": time_min,
                    "end": time_max
                },
                "calendars": {}
            }
            
            for cal_id, cal_data in freebusy.get('calendars', {}).items():
                busy_periods = cal_data.get('busy', [])
                
                # Format the busy periods with more human-readable timestamps
                formatted_busy = []
                for period in busy_periods:
                    start = period.get('start', '')
                    end = period.get('end', '')
                    
                    try:
                        start_dt = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                        end_dt = datetime.datetime.fromisoformat(end.replace('Z', '+00:00'))
                        
                        formatted_start = start_dt.strftime('%Y-%m-%d %H:%M')
                        formatted_end = end_dt.strftime('%Y-%m-%d %H:%M')
                        duration_mins = int((end_dt - start_dt).total_seconds() / 60)
                        
                        formatted_busy.append({
                            "start": start,
                            "end": end,
                            "formatted_start": formatted_start,
                            "formatted_end": formatted_end,
                            "duration_minutes": duration_mins
                        })
                    except ValueError:
                        # If we can't parse the date, just use the original
                        formatted_busy.append({
                            "start": start,
                            "end": end
                        })
                
                processed_data['calendars'][cal_id] = {
                    "busy_periods": formatted_busy,
                    "total_busy_periods": len(busy_periods)
                }
            
            return CalendarAccountResponse(
                status="success",
                message="Free/busy information retrieved successfully.",
                error_message=None,
                data={"free_busy": processed_data}
            )
        except HttpError as api_err:
            logger.error(f"API error during freebusy query: {api_err}", exc_info=True)
            return CalendarAccountResponse(
                status="error",
                message=f"Error querying free/busy information: {api_err.reason if hasattr(api_err, 'reason') else str(api_err)}",
                error_message=str(api_err),
                data=None
            )
    except HttpError as e:
        logger.error(f"HTTP error checking free/busy status for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Error accessing Calendar API for account {account_id}.",
            error_message=str(e),
            data=None
        )
    except Exception as e:
        logger.error(f"Unexpected error checking free/busy status for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Unexpected error checking free/busy status for account {account_id}.",
            error_message=str(e),
            data=None
        )

def find_free_slots(account_id: str, date: str, min_duration_minutes: int = 30) -> CalendarAccountResponse:
    """Find free time slots in the user's calendar for a given date."""
    logger.info(f"Finding free slots for account {account_id} on {date}")
    
    try:
        # Handle "today" specially
        if date.lower() == "today":
            try:
                # Use the user's timezone from config
                user_tz = ZoneInfo(TIMEZONE)
                date_obj = datetime.datetime.now(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)
                logger.info(f"Using today's date in timezone {TIMEZONE}: {date_obj.isoformat()}")
            except Exception as e:
                logger.error(f"Error getting today's date with timezone {TIMEZONE}: {e}")
                return CalendarAccountResponse(
                    status="error",
                    message="Error determining today's date with your timezone.",
                    error_message=f"Failed to use timezone {TIMEZONE}: {e}",
                    data=None
                )
        else:
            # Parse the date string into datetime
            try:
                # Handle different date formats
                # Try ISO format first (YYYY-MM-DD)
                if 'T' in date:
                    # Full datetime provided
                    date_obj = datetime.datetime.fromisoformat(date.replace('Z', '+00:00'))
                else:
                    # Just date provided
                    date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
                
                # Set time to 00:00:00 and make timezone-aware
                try:
                    user_tz = ZoneInfo(TIMEZONE)
                    # First make naive by removing tzinfo if present
                    naive_date = date_obj.replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)
                    # Then add proper timezone
                    date_obj = naive_date.replace(tzinfo=user_tz)
                    logger.info(f"Made date timezone-aware with {TIMEZONE}: {date_obj.isoformat()}")
                except Exception as tz_err:
                    logger.warning(f"Could not apply timezone {TIMEZONE} to date: {tz_err}. Using UTC.")
                    date_obj = date_obj.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=datetime.timezone.utc)
                
                logger.info(f"Parsed date input '{date}' as {date_obj.isoformat()}")
            except ValueError:
                # Try other common formats if ISO format fails
                try:
                    for fmt in ['%m/%d/%Y', '%d/%m/%Y', '%b %d %Y', '%d %b %Y']:
                        try:
                            date_obj = datetime.datetime.strptime(date, fmt)
                            # Make timezone-aware
                            try:
                                user_tz = ZoneInfo(TIMEZONE)
                                date_obj = date_obj.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=user_tz)
                            except Exception:
                                date_obj = date_obj.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=datetime.timezone.utc)
                                
                            logger.info(f"Parsed date input '{date}' using format {fmt} as {date_obj.isoformat()}")
                            break
                        except ValueError:
                            continue
                    else:  # No break, all formats failed
                        raise ValueError(f"Could not parse date '{date}' with any known format")
                except Exception as parse_err:
                    logger.error(f"Failed to parse date: {parse_err}")
                    return CalendarAccountResponse(
                        status="error",
                        message="Invalid date format.",
                        error_message=f"Date must be in ISO format (YYYY-MM-DD) or another common format: {parse_err}",
                        data=None
                    )
        
        # Set time range for the given date (from 00:00 to 23:59)
        # Ensure UTC format with Z suffix for the Google Calendar API
        # First convert to UTC for the API
        utc_date_obj = date_obj.astimezone(datetime.timezone.utc)
        time_min = utc_date_obj.isoformat().replace('+00:00', 'Z')
        time_max = (utc_date_obj + datetime.timedelta(days=1, seconds=-1)).isoformat().replace('+00:00', 'Z')
        
        logger.info(f"Using time range: {time_min} to {time_max}")
        
        # Get the free/busy information
        free_busy_result = check_free_busy(account_id, time_min, time_max)
        if free_busy_result['status'] != 'success':
            logger.error(f"Failed to get free/busy information: {free_busy_result['error_message']}")
            return free_busy_result
        
        # Extract the busy periods with better error handling
        try:
            free_busy = free_busy_result['data']['free_busy']
            calendars = free_busy.get('calendars', {})
            primary_calendar = calendars.get('primary', {})
            
            if not primary_calendar:
                logger.warning("Primary calendar data not found in free/busy result")
                return CalendarAccountResponse(
                    status="error",
                    message="Could not find primary calendar data",
                    error_message="The API response did not contain information for the primary calendar",
                    data={"raw_response": free_busy}
                )
            
            busy_periods = []
            for period in primary_calendar.get('busy_periods', []):
                if 'start' in period and 'end' in period:
                    busy_periods.append({
                        'start': period['start'],
                        'end': period['end']
                    })
            
            logger.info(f"Found {len(busy_periods)} busy periods on {date}")
        except (KeyError, TypeError) as e:
            logger.error(f"Error processing free/busy result: {e}", exc_info=True)
            logger.error(f"Free/busy result structure: {free_busy_result}")
            return CalendarAccountResponse(
                status="error",
                message="Error processing free/busy information",
                error_message=f"Failed to extract busy periods from API response: {e}",
                data={"raw_response": free_busy_result}
            )
        
        # Define working hours (9 AM to 5 PM by default) in user's timezone
        working_hours_start = date_obj.replace(hour=9, minute=0, second=0)
        working_hours_end = date_obj.replace(hour=17, minute=0, second=0)
        
        # Find free slots within working hours, considering busy periods
        free_slots = []
        current_time = working_hours_start
        
        # Sort busy periods by start time
        busy_periods.sort(key=lambda x: x['start'])
        
        # Iterate through busy periods to find gaps
        for busy in busy_periods:
            try:
                # Parse the UTC times from API and convert to user's timezone for proper merging
                busy_start = datetime.datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
                busy_end = datetime.datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
                
                # Convert to the user's timezone for proper display and calculations
                try:
                    user_tz = ZoneInfo(TIMEZONE)
                    busy_start = busy_start.astimezone(user_tz)
                    busy_end = busy_end.astimezone(user_tz)
                except Exception as tz_err:
                    logger.warning(f"Could not convert time to timezone {TIMEZONE}: {tz_err}. Using UTC.")
                
                # Check if there's a free slot before this busy period
                if current_time < busy_start:
                    duration = int((busy_start - current_time).total_seconds() / 60)
                    if duration >= min_duration_minutes:
                        free_slots.append({
                            'start': current_time.isoformat(),
                            'end': busy_start.isoformat(),
                            'formatted_start': current_time.strftime('%H:%M'),
                            'formatted_end': busy_start.strftime('%H:%M'),
                            'duration_minutes': duration,
                            'timezone': TIMEZONE
                        })
                
                # Move current time to the end of this busy period
                current_time = max(current_time, busy_end)
            except ValueError as e:
                logger.warning(f"Error parsing busy period dates: {e}, skipping period: {busy}")
                continue
        
        # Check if there's a free slot after the last busy period until end of working hours
        if current_time < working_hours_end:
            duration = int((working_hours_end - current_time).total_seconds() / 60)
            if duration >= min_duration_minutes:
                free_slots.append({
                    'start': current_time.isoformat(),
                    'end': working_hours_end.isoformat(),
                    'formatted_start': current_time.strftime('%H:%M'),
                    'formatted_end': working_hours_end.strftime('%H:%M'),
                    'duration_minutes': duration,
                    'timezone': TIMEZONE
                })
        
        # Add formatted date to each slot for clearer output
        date_str = date_obj.strftime('%Y-%m-%d')
        for slot in free_slots:
            slot['date'] = date_str
            # Add a user-friendly description
            slot['description'] = f"{date_str} from {slot['formatted_start']} to {slot['formatted_end']} ({slot['duration_minutes']} minutes) {TIMEZONE}"
        
        return CalendarAccountResponse(
            status="success",
            message=f"Found {len(free_slots)} free slots of at least {min_duration_minutes} minutes on {date}.",
            error_message=None,
            data={
                "date": date_str,
                "free_slots": free_slots,
                "min_duration_minutes": min_duration_minutes,
                "working_hours": {
                    "start": working_hours_start.strftime('%H:%M'),
                    "end": working_hours_end.strftime('%H:%M')
                },
                "timezone": TIMEZONE
            }
        )
    except Exception as e:
        # Improved error handling
        import traceback
        tb_str = traceback.format_exc()
        logger.error(f"Unexpected error finding free slots for {account_id}: {e}\n{tb_str}")
        
        # Create a more descriptive error message
        error_details = f"Time zone issue: {e}" if "zone" in str(e).lower() else f"Error: {e}"
        
        return CalendarAccountResponse(
            status="error",
            message=f"Unexpected error finding free slots for account {account_id}.",
            error_message=error_details,
            data=None
        )

def send_calendar_invite(account_id: str, event_id: str) -> CalendarAccountResponse:
    """Send invites for an existing calendar event."""
    logger.info(f"Sending invites for calendar event {event_id} for account {account_id}")
    
    # This is a wrapper around update_calendar_event that ensures the updates parameter is properly provided
    updates = {
        'sendNotifications': True  # Ensure notifications are sent
    }
    
    return update_calendar_event(account_id, event_id, updates)

def create_event_with_attendees(account_id: str, summary: str, attendee_emails: List[str], 
                             start_time: str, end_time: str, description: Optional[str] = None,
                             location: Optional[str] = None) -> CalendarAccountResponse:
    """Create a new event with attendees and automatically send invites.
    This function properly formats the attendee emails and ensures invites are sent."""
    logger.info(f"Creating calendar event with attendees for account {account_id}")
    
    # Properly format the attendees list - this is critical for invites to work
    formatted_attendees = [{'email': email.strip()} for email in attendee_emails]
    logger.info(f"Formatted attendees: {formatted_attendees}")
    
    try:
        service = build_calendar_service(account_id)
        if not service:
            return CalendarAccountResponse(
                status="error",
                message=f"Failed to build Calendar service for account {account_id}.",
                error_message="Could not authenticate with Calendar API.",
                data=None
            )
        
        # Validate required parameters
        if not summary or not start_time or not end_time:
            return CalendarAccountResponse(
                status="error",
                message="Missing required event parameters.",
                error_message="Summary, start time, and end time are required.",
                data=None
            )
        
        # Build the event object
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',  # Default to UTC, user can override
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',  # Default to UTC, user can override
            },
            'attendees': formatted_attendees,  # Properly formatted attendees list
        }
        
        # Add optional fields if provided
        if description:
            event['description'] = description
        if location:
            event['location'] = location
        
        # Execute the API call with retry logic - explicitly setting sendUpdates to 'all' to send invites
        created_event = execute_with_retry(service.events().insert(
            calendarId='primary',
            body=event,
            sendUpdates='all'  # Always send notifications to attendees
        ))
        
        # Verify attendees were properly included
        if 'attendees' in created_event:
            attendee_count = len(created_event['attendees'])
            logger.info(f"Event created with {attendee_count} attendees")
            return CalendarAccountResponse(
                status="success",
                message=f"Event '{summary}' created and invites sent to {attendee_count} attendees.",
                error_message=None,
                data={"event": created_event}
            )
        else:
            logger.warning("Event created but no attendees found in the response. Invites may not have been sent.")
            return CalendarAccountResponse(
                status="success",
                message=f"Event '{summary}' created, but no attendees confirmed. Please check if invites were sent.",
                error_message=None,
                data={"event": created_event}
            )
    except HttpError as e:
        logger.error(f"HTTP error creating Calendar event with attendees for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Error accessing Calendar API for account {account_id}.",
            error_message=str(e),
            data=None
        )
    except Exception as e:
        logger.error(f"Unexpected error creating Calendar event with attendees for {account_id}: {e}", exc_info=True)
        return CalendarAccountResponse(
            status="error",
            message=f"Unexpected error creating Calendar event with attendees for account {account_id}.",
            error_message=str(e),
            data=None
        )

def find_mutual_free_slots(primary_account_id: str, other_account_ids: List[str], 
                          date: str, min_duration_minutes: int = 120,
                          max_slots: int = 3) -> CalendarAccountResponse:
    """Find mutually free time slots across multiple users' calendars.
    
    Args:
        primary_account_id: The account ID of the primary user
        other_account_ids: List of other users' account IDs to compare with
        date: The date to check in YYYY-MM-DD format
        min_duration_minutes: Minimum duration required for free slots (default: 120 minutes/2 hours)
        max_slots: Maximum number of slot options to return (default: 3)
        
    Returns:
        CalendarAccountResponse with mutual free slots
    """
    logger.info(f"Finding mutual free slots for {primary_account_id} and {other_account_ids} on {date}")
    
    try:
        # Handle "today" specially
        if date.lower() == "today":
            try:
                # Use the user's timezone from config
                user_tz = ZoneInfo(TIMEZONE)
                date_obj = datetime.datetime.now(user_tz).replace(hour=0, minute=0, second=0, microsecond=0)
                logger.info(f"Using today's date in timezone {TIMEZONE}: {date_obj.isoformat()}")
            except Exception as e:
                logger.error(f"Error getting today's date with timezone {TIMEZONE}: {e}")
                return CalendarAccountResponse(
                    status="error",
                    message="Error determining today's date with your timezone.",
                    error_message=f"Failed to use timezone {TIMEZONE}: {e}",
                    data=None
                )
        else:
            # Parse the date string into datetime
            try:
                # Handle different date formats
                if 'T' in date:
                    # Full datetime provided
                    date_obj = datetime.datetime.fromisoformat(date.replace('Z', '+00:00'))
                else:
                    # Just date provided
                    date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
                
                # Set time to 00:00:00 and make timezone-aware
                try:
                    user_tz = ZoneInfo(TIMEZONE)
                    # First make naive by removing tzinfo if present
                    naive_date = date_obj.replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)
                    # Then add proper timezone
                    date_obj = naive_date.replace(tzinfo=user_tz)
                    logger.info(f"Made date timezone-aware with {TIMEZONE}: {date_obj.isoformat()}")
                except Exception as tz_err:
                    logger.warning(f"Could not apply timezone {TIMEZONE} to date: {tz_err}. Using UTC.")
                    date_obj = date_obj.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=datetime.timezone.utc)
                
                logger.info(f"Parsed date input '{date}' as {date_obj.isoformat()}")
            except ValueError:
                # Try other common formats if ISO format fails
                try:
                    for fmt in ['%m/%d/%Y', '%d/%m/%Y', '%b %d %Y', '%d %b %Y']:
                        try:
                            date_obj = datetime.datetime.strptime(date, fmt)
                            # Make timezone-aware
                            try:
                                user_tz = ZoneInfo(TIMEZONE)
                                date_obj = date_obj.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=user_tz)
                            except Exception:
                                date_obj = date_obj.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=datetime.timezone.utc)
                                
                            logger.info(f"Parsed date input '{date}' using format {fmt} as {date_obj.isoformat()}")
                            break
                        except ValueError:
                            continue
                    else:  # No break, all formats failed
                        raise ValueError(f"Could not parse date '{date}' with any known format")
                except Exception as parse_err:
                    logger.error(f"Failed to parse date: {parse_err}")
                    return CalendarAccountResponse(
                        status="error",
                        message="Invalid date format.",
                        error_message=f"Date must be in ISO format (YYYY-MM-DD) or another common format: {parse_err}",
                        data=None
                    )
        
        # Set time range for the given date (from 00:00 to 23:59)
        # Ensure UTC format with Z suffix for the Google Calendar API
        # First convert to UTC for the API
        utc_date_obj = date_obj.astimezone(datetime.timezone.utc)
        time_min = utc_date_obj.isoformat().replace('+00:00', 'Z')
        time_max = (utc_date_obj + datetime.timedelta(days=1, seconds=-1)).isoformat().replace('+00:00', 'Z')
        
        logger.info(f"Using time range: {time_min} to {time_max}")
        
        # Get all account IDs to check
        all_account_ids = [primary_account_id] + other_account_ids
        
        # Define working hours (9 AM to 5 PM by default) in user's timezone
        working_hours_start = date_obj.replace(hour=9, minute=0, second=0)
        working_hours_end = date_obj.replace(hour=17, minute=0, second=0)
        
        # Collect busy periods for all accounts
        all_busy_periods = {}
        
        for account_id in all_account_ids:
            # Get the free/busy information
            free_busy_result = check_free_busy(account_id, time_min, time_max)
            if free_busy_result['status'] != 'success':
                logger.error(f"Failed to get free/busy information for {account_id}: {free_busy_result.get('error_message')}")
                return CalendarAccountResponse(
                    status="error",
                    message=f"Couldn't retrieve calendar data for {account_id}",
                    error_message=free_busy_result.get('error_message'),
                    data=None
                )
            
            # Extract the busy periods
            try:
                free_busy = free_busy_result['data']['free_busy']
                calendars = free_busy.get('calendars', {})
                primary_calendar = calendars.get('primary', {})
                
                if not primary_calendar:
                    logger.warning(f"Primary calendar data not found for {account_id}")
                    return CalendarAccountResponse(
                        status="error",
                        message=f"Could not find calendar data for {account_id}",
                        error_message="The API response did not contain calendar information",
                        data=None
                    )
                
                busy_periods = []
                for period in primary_calendar.get('busy_periods', []):
                    if 'start' in period and 'end' in period:
                        busy_periods.append({
                            'start': period['start'],
                            'end': period['end']
                        })
                
                all_busy_periods[account_id] = busy_periods
                logger.info(f"Found {len(busy_periods)} busy periods for {account_id} on {date}")
            except (KeyError, TypeError) as e:
                logger.error(f"Error processing free/busy result for {account_id}: {e}", exc_info=True)
                return CalendarAccountResponse(
                    status="error",
                    message=f"Error processing calendar data for {account_id}",
                    error_message=str(e),
                    data=None
                )
        
        # Create a combined list of all busy periods
        combined_busy_periods = []
        
        for account_id, busy_periods in all_busy_periods.items():
            for period in busy_periods:
                try:
                    # Parse the UTC times from API and convert to user's timezone for proper merging
                    start_dt = datetime.datetime.fromisoformat(period['start'].replace('Z', '+00:00'))
                    end_dt = datetime.datetime.fromisoformat(period['end'].replace('Z', '+00:00'))
                    
                    # Convert to the user's timezone for proper display and calculations
                    try:
                        user_tz = ZoneInfo(TIMEZONE)
                        start_dt = start_dt.astimezone(user_tz)
                        end_dt = end_dt.astimezone(user_tz)
                    except Exception as tz_err:
                        logger.warning(f"Could not convert time to timezone {TIMEZONE}: {tz_err}. Using UTC.")
                    
                    combined_busy_periods.append((start_dt, end_dt))
                except ValueError as e:
                    logger.warning(f"Error parsing busy period dates for {account_id}: {e}")
                    continue
        
        # Sort combined busy periods by start time
        combined_busy_periods.sort(key=lambda x: x[0])
        
        # Merge overlapping busy periods
        if combined_busy_periods:
            merged_busy_periods = [combined_busy_periods[0]]
            
            for current_start, current_end in combined_busy_periods[1:]:
                prev_start, prev_end = merged_busy_periods[-1]
                
                # If current period overlaps with previous period
                if current_start <= prev_end:
                    # Merge by updating end time of previous period if needed
                    merged_busy_periods[-1] = (prev_start, max(prev_end, current_end))
                else:
                    # No overlap, add as a new period
                    merged_busy_periods.append((current_start, current_end))
        else:
            merged_busy_periods = []
        
        # Find free slots between busy periods, within working hours
        free_slots = []
        current_time = working_hours_start
        
        # Add working_hours_start as current_time
        for busy_start, busy_end in merged_busy_periods:
            # Only consider busy periods that overlap with working hours
            if busy_end > working_hours_start and busy_start < working_hours_end:
                # Adjust busy_start and busy_end to be within working hours
                busy_start = max(busy_start, working_hours_start)
                busy_end = min(busy_end, working_hours_end)
                
                # Check if there's a free slot before this busy period
                if current_time < busy_start:
                    duration_minutes = int((busy_start - current_time).total_seconds() / 60)
                    
                    if duration_minutes >= min_duration_minutes:
                        # Use user's timezone for display
                        free_slots.append({
                            'start': current_time.isoformat(),
                            'end': busy_start.isoformat(),
                            'formatted_start': current_time.strftime('%H:%M'),
                            'formatted_end': busy_start.strftime('%H:%M'),
                            'duration_minutes': duration_minutes,
                            'date': date_obj.strftime('%Y-%m-%d'),
                            'timezone': TIMEZONE
                        })
                
                # Move current time to the end of this busy period
                current_time = max(current_time, busy_end)
        
        # Check for a final free slot after the last busy period
        if current_time < working_hours_end:
            duration_minutes = int((working_hours_end - current_time).total_seconds() / 60)
            
            if duration_minutes >= min_duration_minutes:
                free_slots.append({
                    'start': current_time.isoformat(),
                    'end': working_hours_end.isoformat(),
                    'formatted_start': current_time.strftime('%H:%M'),
                    'formatted_end': working_hours_end.strftime('%H:%M'),
                    'duration_minutes': duration_minutes,
                    'date': date_obj.strftime('%Y-%m-%d'),
                    'timezone': TIMEZONE
                })
        
        # If no merged busy periods within working hours, the entire working day is free
        if not merged_busy_periods:
            duration_minutes = int((working_hours_end - working_hours_start).total_seconds() / 60)
            if duration_minutes >= min_duration_minutes:
                free_slots.append({
                    'start': working_hours_start.isoformat(),
                    'end': working_hours_end.isoformat(),
                    'formatted_start': working_hours_start.strftime('%H:%M'),
                    'formatted_end': working_hours_end.strftime('%H:%M'),
                    'duration_minutes': duration_minutes,
                    'date': date_obj.strftime('%Y-%m-%d'),
                    'timezone': TIMEZONE
                })
        
        # Sort free slots by start time and limit to requested number
        free_slots.sort(key=lambda x: x['start'])
        limited_slots = free_slots[:max_slots]
        
        # Create user-friendly description of each slot
        for slot in limited_slots:
            start_time = slot['formatted_start']
            end_time = slot['formatted_end']
            slot['description'] = f"{slot['date']} from {start_time} to {end_time} ({slot['duration_minutes']} minutes) {TIMEZONE}"
        
        return CalendarAccountResponse(
            status="success",
            message=f"Found {len(limited_slots)} mutual free slots of at least {min_duration_minutes} minutes on {date}.",
            error_message=None,
            data={
                "date": date_obj.strftime('%Y-%m-%d'),
                "mutual_free_slots": limited_slots,
                "min_duration_minutes": min_duration_minutes,
                "accounts_checked": all_account_ids,
                "working_hours": {
                    "start": working_hours_start.strftime('%H:%M'),
                    "end": working_hours_end.strftime('%H:%M')
                },
                "timezone": TIMEZONE
            }
        )
    except Exception as e:
        # Improved error handling
        import traceback
        tb_str = traceback.format_exc()
        logger.error(f"Unexpected error finding mutual free slots: {e}\n{tb_str}")
        
        # Create a more descriptive error message
        error_details = f"Time zone issue: {e}" if "zone" in str(e).lower() else f"Error: {e}"
        
        return CalendarAccountResponse(
            status="error",
            message=f"Unexpected error finding mutual free slots.",
            error_message=error_details,
            data=None
        )
