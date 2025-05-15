import os
import json
import logging
import time
from typing import Dict, Optional, List, Any, Union, Tuple
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from lucident_agent.Database import Database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TOKEN_FILE = 'gmail_tokens.json'
TOKEN_TABLE = 'tokens'  # Using the table name from gmail_tools.py

class GmailAccountManager:
    """Unified manager for Gmail account credentials using Supabase with file fallback."""
    
    def __init__(self):
        self.use_supabase = True
        self.supabase = None
        self._init_supabase()
        self.accounts = {}
        self.default_account_id = None
        self._load_accounts()
        
    def _init_supabase(self) -> None:
        """Initialize Supabase connection."""
        try:
            self.supabase = Database().client
            # Test connection
            self.supabase.table(TOKEN_TABLE).select('*').limit(1).execute()
            logger.info("Supabase client initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing Supabase: {e}")
            self.use_supabase = False
            logger.warning("Falling back to local file storage for Gmail tokens.")

    def _check_supabase(self) -> bool:
        """Check if Supabase client is available."""
        if self.supabase is None or not self.use_supabase:
            logger.warning("Supabase client is not initialized. Cannot perform operation.")
            return False
        return True
    
    def _load_accounts(self) -> Dict[str, Dict]:
        """Load accounts from Supabase or file."""
        if self.use_supabase:
            accounts = self._load_from_supabase()
            if accounts:
                self.accounts = accounts
                # Set default account if not already set
                if self.default_account_id is None and self.accounts:
                    self.default_account_id = next(iter(self.accounts))
                    logger.info(f"Set {self.default_account_id} as the default account.")
                return accounts
        
        # Fallback to file if Supabase failed or returned no accounts
        accounts = self._load_from_file()
        self.accounts = accounts
        if self.accounts and self.default_account_id is None:
            self.default_account_id = next(iter(self.accounts))
        return accounts
    
    def _load_from_supabase(self) -> Dict[str, Dict]:
        """Load accounts from Supabase."""
        accounts = {}
        if not self._check_supabase():
            return accounts
            
        try:
            response = self.supabase.table(TOKEN_TABLE).select('user_id, token_data').eq('token_type', 'google').execute()
            
            if response.data:
                for record in response.data:
                    account_id = record['user_id']
                    try:
                        token_data = json.loads(record['token_data'])
                        accounts[account_id] = token_data
                    except json.JSONDecodeError:
                        logger.error(f"Could not parse token data for account {account_id}. Skipping.")
                    except Exception as parse_err:
                        logger.error(f"Error processing account details for {account_id}: {parse_err}")
            
            logger.info(f"Loaded {len(accounts)} accounts from Supabase.")
            return accounts
            
        except Exception as e:
            logger.error(f"Error loading accounts from Supabase: {e}")
            self.use_supabase = False
            return {}
    
    def _load_from_file(self) -> Dict[str, Dict]:
        """Load accounts from local file."""
        accounts = {}
        try:
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'r') as f:
                    accounts = json.load(f)
                logger.info(f"Loaded {len(accounts)} accounts from local file.")
            else:
                logger.info(f"Token file {TOKEN_FILE} does not exist. Starting with empty accounts.")
        except Exception as e:
            logger.error(f"Error loading accounts from file: {e}")
            
        return accounts
    
    def _save_to_file(self) -> None:
        """Save accounts to local file."""
        try:
            with open(TOKEN_FILE, 'w') as f:
                json.dump(self.accounts, f)
            logger.info(f"Saved {len(self.accounts)} accounts to local file.")
        except Exception as e:
            logger.error(f"Error saving accounts to file: {e}")
    
    def add_account(self, email: str, credentials_obj: Union[Credentials, Dict]) -> bool:
        """Add or update account credentials.
        
        Args:
            email: Account email/identifier
            credentials_obj: Either a Credentials object or credentials dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not email:
            logger.error("Email is required to add account.")
            return False
            
        try:
            # Convert Credentials object to JSON if needed
            if isinstance(credentials_obj, Credentials):
                token_json = credentials_obj.to_json()
                credentials_dict = json.loads(token_json)
            else:
                credentials_dict = credentials_obj
                token_json = json.dumps(credentials_dict)
            
            # Update in-memory cache
            self.accounts[email] = credentials_dict
            
            # Set as default if it's the first account added in this session
            if self.default_account_id is None:
                self.default_account_id = email
                logger.info(f"Set {email} as the default account.")
            
            # Save to Supabase if available
            if self._check_supabase():
                try:
                    # Use email as the user_id (primary key combined with token_type)
                    data, count = self.supabase.table(TOKEN_TABLE).upsert({
                        'user_id': email,
                        'token_type': 'google',
                        'token_data': token_json
                    }, on_conflict='user_id, token_type').execute()
                    
                    logger.info(f"Successfully upserted credentials for {email} in Supabase.")
                except Exception as e:
                    logger.error(f"Error adding account {email} to Supabase: {e}", exc_info=True)
                    logger.warning(f"Falling back to saving account {email} to local file.")
                    self._save_to_file()
                    return False
            else:
                # If Supabase is not available, save to file
                self._save_to_file()
                
            return True
            
        except Exception as e:
            logger.error(f"Unexpected error adding account {email}: {e}", exc_info=True)
            return False

    def get_accounts(self) -> Dict[str, Dict[str, Any]]:
        """Get all configured accounts with their credentials."""
        return self.accounts
        
    def get_default_account(self) -> Optional[str]:
        """Get the default account ID."""
        return self.default_account_id

    def get_account_credentials(self, account_id: str) -> Optional[Dict]:
        """Get credentials for a specific account.
        
        Args:
            account_id: Email/ID of the account
            
        Returns:
            Dict or None: Credentials dictionary or None if not found
        """
        if not account_id:
            logger.warning("No account_id provided to get_account_credentials.")
            return None
            
        return self.accounts.get(account_id)

    def get_all_account_ids(self) -> List[str]:
        """Get list of all account IDs."""
        return list(self.accounts.keys())

    def remove_account(self, account_id: str) -> bool:
        """Remove an account.
        
        Args:
            account_id: Email/ID of the account to remove
            
        Returns:
            bool: True if removed, False otherwise
        """
        if not account_id:
            logger.warning("No account_id provided to remove_account.")
            return False
            
        removed_from_memory = False
        if account_id in self.accounts:
            del self.accounts[account_id]
            removed_from_memory = True
            
            # If removing the default, reset default
            if self.default_account_id == account_id:
                self.default_account_id = next(iter(self.accounts)) if self.accounts else None
                logger.info("Reset default account assignment.")
                
            logger.info(f"Removed account {account_id} from in-memory cache.")

        # Remove from Supabase if available
        if self._check_supabase():
            try:
                data, count = self.supabase.table(TOKEN_TABLE).delete().eq('user_id', account_id).eq('token_type', 'google').execute()
                if count > 0:
                    logger.info(f"Successfully removed account {account_id} from Supabase.")
                else:
                    logger.warning(f"Account {account_id} not found in Supabase for removal or delete failed.")
            except Exception as e:
                logger.error(f"Error removing account {account_id} from Supabase: {e}", exc_info=True)

        # Update the local file
        self._save_to_file()
        
        return removed_from_memory
        
    def get_credentials(self, account_id: str) -> Optional[Credentials]:
        """Get valid Credentials object for Gmail API from storage. Handles refresh.
        
        Args:
            account_id: Email/ID of the account
            
        Returns:
            Credentials or None: Valid credentials object or None if not found/invalid
        """
        logger.debug(f"Attempting to get credentials for account_id: {account_id}")
        try:
            # Get credentials dictionary from storage
            credentials_dict = self.get_account_credentials(account_id)
            if not credentials_dict:
                logger.error(f"Account {account_id} credentials not found.")
                return None

            # Create credentials object from dictionary
            creds = Credentials.from_authorized_user_info(credentials_dict)

            # Check if credentials need refresh
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    logger.info(f"Credentials for {account_id} expired. Attempting refresh.")
                    try:
                        creds.refresh(Request())
                        logger.info(f"Credentials for {account_id} refreshed successfully.")
                        # Update token in storage
                        self.add_account(account_id, creds)
                    except Exception as e:
                        logger.error(f"Failed to refresh credentials for {account_id}: {e}", exc_info=True)
                        return None
                else:
                    logger.error(f"Credentials for {account_id} are invalid or expired, and no refresh token is available.")
                    return None

            logger.debug(f"Valid credentials obtained for {account_id}.")
            return creds

        except Exception as e:
            logger.error(f"Error getting or refreshing credentials for {account_id}: {e}", exc_info=True)
            return None 