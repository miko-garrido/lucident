import os
import json

class GmailAccountManager:
    def __init__(self):
        self.accounts = self._load_accounts()
    
    def _load_accounts(self):
        accounts = {}
        token_file = 'gmail_tokens.json'
        
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                all_tokens = json.load(f)
                for account_id in all_tokens:
                    accounts[account_id] = account_id  # Use account_id as email since it's the same
        return accounts
    
    def add_account(self, account_id, email):
        self.accounts[account_id] = email
        
    def get_accounts(self):
        return self.accounts
        
    def get_default_account(self):
        return self.accounts.get('default') 