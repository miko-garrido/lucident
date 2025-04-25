"""Gmail Account Manager Module

This module manages Gmail account configurations and credentials using Supabase with file-based fallback.
"""

import os
import pickle
import base64
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime
from supabase import Client
from Database import Database
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TOKEN_FILE = 'gmail_tokens.json'

# Load environment variables
load_dotenv()

class GmailAccountManager:
    """Manages Gmail account configurations and credentials."""
    
    def __init__(self):
        """Initialize the GmailAccountManager."""
        self.use_supabase = True
        self._init_supabase()
        
    def _init_supabase(self) -> None:
        """Initialize Supabase client."""
        try:
            db = Database()
            self.supabase = db.client
            # Test connection
            self.supabase.table('gmail_tokens').select('*').limit(1).execute()
        except Exception as e:
            logger.error(f"Error initializing Supabase: {e}")
            self.use_supabase = False
    
    def _load_accounts(self) -> Dict[str, Dict]:
        """Load account configurations from storage.
        
        Returns:
            Dict mapping account IDs to account details
        """
        if self.use_supabase:
            return self._load_from_supabase()
        return self._load_from_file()
    
    def _load_from_supabase(self) -> Dict[str, Dict]:
        """Load accounts from Supabase."""
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
        """Load accounts from file."""
        accounts = {}
        try:
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'r') as f:
                    accounts = json.load(f)
        except Exception as e:
            logger.error(f"Error loading accounts from file: {e}")
            
        return accounts
    
    def _save_to_file(self) -> None:
        """Save accounts to file."""
        try:
            with open(TOKEN_FILE, 'w') as f:
                json.dump(self.accounts, f)
        except Exception as e:
            logger.error(f"Error saving accounts to file: {e}")
    
    def add_account(self, account_id: str, credentials: Dict) -> None:
        """Add a new Gmail account or update existing one.
        
        Args:
            account_id: Account identifier (email)
            credentials: Account credentials
        """
        logger.info(f"Adding/updating account: {account_id}")
        self.accounts[account_id] = credentials
        
        if self.use_supabase:
            try:
                self.supabase.table('gmail_tokens').upsert({
                    'email': account_id,
                    **credentials
                }).execute()
            except Exception as e:
                logger.error(f"Error saving to Supabase: {e}")
                self._save_to_file()
        else:
            self._save_to_file()
        
    def get_accounts(self) -> Dict[str, Dict]:
        """Get all configured accounts."""
        return self.accounts
        
    def get_default_account(self) -> Optional[str]:
        """Get the default account ID."""
        return 'default' if 'default' in self.accounts else None

    def get_account_credentials(self, account_id: str) -> Optional[Dict]:
        """Get credentials for a specific account."""
        return self.accounts.get(account_id)

    def get_all_account_ids(self) -> List[str]:
        """Get all account IDs."""
        return list(self.accounts.keys()) 