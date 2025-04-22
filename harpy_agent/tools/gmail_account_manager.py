"""Gmail Account Manager Module

This module manages Gmail account configurations and credentials.
"""

import os
import json
import logging
from typing import Dict, Optional

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
    
    def _load_accounts(self) -> Dict[str, str]:
        """Load account configurations from token file.
        
        Returns:
            Dict mapping account IDs to email addresses
        """
        accounts = {}
        try:
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'r') as f:
                    all_tokens = json.load(f)
                    for account_id in all_tokens:
                        accounts[account_id] = account_id  # Use account_id as email since it's the same
        except Exception as e:
            logger.error(f"Error loading accounts: {e}")
            
        return accounts
    
    def add_account(self, account_id: str, email: str) -> None:
        """Add a new Gmail account.
        
        Args:
            account_id: Account identifier
            email: Email address
        """
        logger.info(f"Adding account: {account_id} ({email})")
        self.accounts[account_id] = email
        
    def get_accounts(self) -> Dict[str, str]:
        """Get all configured accounts.
        
        Returns:
            Dict mapping account IDs to email addresses
        """
        return self.accounts
        
    def get_default_account(self) -> Optional[str]:
        """Get the default account email.
        
        Returns:
            Default account email if configured, None otherwise
        """
        return self.accounts.get('default') 