"""Gmail Account Manager Module

This module manages Gmail account configurations and credentials.
"""

import os
import json
import logging
from typing import Dict, Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TOKEN_FILE = 'gmail_tokens.json'

class GmailAccountManager:
    """Manages Gmail account configurations and credentials."""
    
    def __init__(self):
        """Initialize the account manager."""
        self.accounts = self._load_accounts()
    
    def _load_accounts(self) -> Dict[str, Dict]:
        """Load account configurations from token file.
        
        Returns:
            Dict mapping account IDs to account details
        """
        accounts = {}
        try:
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'r') as f:
                    accounts = json.load(f)
        except Exception as e:
            logger.error(f"Error loading accounts: {e}")
            
        return accounts
    
    def add_account(self, account_id: str, credentials: Dict) -> None:
        """Add a new Gmail account.
        
        Args:
            account_id: Account identifier
            credentials: Account credentials
        """
        logger.info(f"Adding account: {account_id}")
        self.accounts[account_id] = credentials
        
    def get_accounts(self) -> Dict[str, Dict]:
        """Get all configured accounts.
        
        Returns:
            Dict mapping account IDs to account details
        """
        return self.accounts
        
    def get_default_account(self) -> Optional[str]:
        """Get the default account ID.
        
        Returns:
            Default account ID if configured, None otherwise
        """
        return 'default' if 'default' in self.accounts else None

    def get_account_credentials(self, account_id: str) -> Optional[Dict]:
        """Get credentials for a specific account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            Account credentials if found, None otherwise
        """
        return self.accounts.get(account_id)

    def get_all_account_ids(self) -> List[str]:
        """Get all account IDs.
        
        Returns:
            List of account IDs
        """
        return list(self.accounts.keys()) 