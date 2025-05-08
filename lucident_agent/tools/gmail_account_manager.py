import os
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime
from lucident_agent.Database import Database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TOKEN_FILE = 'gmail_tokens.json'

class GmailAccountManager:
    
    def __init__(self):
        self.use_supabase = True
        self._init_supabase()
        self.accounts = self._load_accounts()
        
    def _init_supabase(self) -> None:
        try:
            self.supabase = Database().client
            # Test connection
            self.supabase.table('gmail_tokens').select('*').limit(1).execute()
        except Exception as e:
            logger.error(f"Error initializing Supabase: {e}")
            self.use_supabase = False
    
    def _load_accounts(self) -> Dict[str, Dict]:
        if self.use_supabase:
            return self._load_from_supabase()
        return self._load_from_file()
    
    def _load_from_supabase(self) -> Dict[str, Dict]:
        accounts = {}
        try:
            response = self.supabase.table('gmail_tokens').select('*').execute()
            for record in response.data:
                expiry = record['expiry']
                if isinstance(expiry, str):
                    try:
                        expiry = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                    except ValueError:
                        logger.error(f"Invalid expiry date format: {expiry}")
                        expiry = None
                
                accounts[record['email']] = {
                    'token': record['token'],
                    'refresh_token': record['refresh_token'],
                    'token_uri': record['token_uri'],
                    'client_id': record['client_id'],
                    'client_secret': record['client_secret'],
                    'scopes': record['scopes'],
                    'expiry': expiry.isoformat() if expiry else None
                }
        except Exception as e:
            logger.error(f"Error loading accounts from Supabase: {e}")
            self.use_supabase = False
            return self._load_from_file()
            
        return accounts
    
    def _load_from_file(self) -> Dict[str, Dict]:
        accounts = {}
        try:
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'r') as f:
                    accounts = json.load(f)
        except Exception as e:
            logger.error(f"Error loading accounts from file: {e}")
            
        return accounts
    
    def _save_to_file(self) -> None:
        try:
            with open(TOKEN_FILE, 'w') as f:
                json.dump(self.accounts, f)
        except Exception as e:
            logger.error(f"Error saving accounts to file: {e}")
    
    def add_account(self, account_id: str, credentials: Dict) -> None:
        logger.info(f"Adding/updating account: {account_id}")
        # Update in-memory cache first
        self.accounts[account_id] = credentials

        if self.use_supabase:
            try:
                logger.info(f"Attempting to upsert account {account_id} to Supabase.")
                self.supabase.table('gmail_tokens').upsert({
                    'email': account_id,
                    **credentials
                }).execute()
                logger.info(f"Successfully upserted account {account_id} to Supabase.")
                # If Supabase succeeds, maybe sync the file? Or rely on loading from Supabase next time?
                # Let's remove explicit file save here if Supabase works.
                # self._save_to_file() # Optional: keep file in sync?
            except Exception as e:
                # Log Supabase error clearly, then fallback to file
                logger.error(f"Error saving account {account_id} to Supabase: {e}", exc_info=True)
                logger.warning(f"Falling back to saving account {account_id} to local file {TOKEN_FILE}.")
                self._save_to_file()
        else:
            # If Supabase is not configured/failed init, save to file
            logger.info(f"Supabase not in use. Saving account {account_id} to local file {TOKEN_FILE}.")
            self._save_to_file()

    def get_accounts(self) -> Dict[str, Dict]:
        return self.accounts
        
    def get_default_account(self) -> Optional[str]:
        return 'default' if 'default' in self.accounts else None

    def get_account_credentials(self, account_id: str) -> Optional[Dict]:
        return self.accounts.get(account_id)

    def get_all_account_ids(self) -> List[str]:
        return list(self.accounts.keys())

    def remove_account(self, account_id: str) -> bool:
        removed_from_memory = False
        if account_id in self.accounts:
            del self.accounts[account_id]
            removed_from_memory = True
            logger.info(f"Removed account {account_id} from in-memory cache.")

        removed_from_supabase = False
        if self.use_supabase:
            try:
                logger.info(f"Attempting to delete account {account_id} from Supabase.")
                # Check how many rows were affected (PostgREST might return empty data on success)
                response = self.supabase.table('gmail_tokens').delete().eq('email', account_id).execute()
                # Simple check: if no exception, assume delete worked or row didn't exist.
                removed_from_supabase = True
                logger.info(f"Delete operation for account {account_id} executed on Supabase.")
            except Exception as e:
                logger.error(f"Error deleting account {account_id} from Supabase: {e}", exc_info=True)
                # If Supabase delete fails, should we still modify the file?
                # Let's log the error and continue to update the file based on memory state.

        # Update the local file only if Supabase is not the primary or if we want it as a backup
        # reflecting the in-memory state.
        if not self.use_supabase or removed_from_memory: # Update file if Supabase isn't used OR if memory changed
             logger.info(f"Updating local file {TOKEN_FILE} after removal attempt for {account_id}.")
             self._save_to_file()

        # Return true if it was removed from memory (main indicator of existence)
        return removed_from_memory 