import os
import json

class GmailAccountManager:
    def __init__(self):
        self.accounts = self._load_accounts()
    
    def _load_accounts(self):
        accounts = {}
        for file in os.listdir():
            if file.startswith('token_') and file.endswith('.json'):
                account_id = file.replace('token_', '').replace('.json', '')
                accounts[account_id] = self._get_email_from_token(file)
        if os.path.exists('token.json'):
            accounts['default'] = self._get_email_from_token('token.json')
        return accounts
    
    def _get_email_from_token(self, token_file):
        with open(token_file, 'r') as f:
            data = json.load(f)
            return data.get('email', 'Unknown')
    
    def add_account(self, account_id, email):
        self.accounts[account_id] = email
        
    def get_accounts(self):
        return self.accounts
        
    def get_default_account(self):
        return self.accounts.get('default') 