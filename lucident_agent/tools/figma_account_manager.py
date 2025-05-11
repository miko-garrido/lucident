import os
import json
import logging
from typing import Dict, Optional, List
from lucident_agent.Database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN_FILE = 'figma_tokens.json'

class FigmaAccountManager:
    def __init__(self):
        self.use_supabase = True
        self._init_supabase()
        self.accounts = self._load_accounts()

    def _init_supabase(self) -> None:
        try:
            self.supabase = Database().client
            self.supabase.table('tokens').select('*').limit(1).execute()
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
            response = self.supabase.table('tokens').select('*').eq('token_type', 'figma').execute()
            for record in response.data:
                user_id = record['user_id']
                token_data = record.get('token_data')
                if token_data:
                    try:
                        token_dict = json.loads(token_data) if isinstance(token_data, str) else token_data
                    except Exception as e:
                        logger.error(f"Invalid token_data for {user_id}: {e}")
                        token_dict = {}
                    accounts[user_id] = token_dict
        except Exception as e:
            logger.error(f"Error loading Figma accounts from Supabase: {e}")
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
            logger.error(f"Error loading Figma accounts from file: {e}")
        return accounts

    def _save_to_file(self) -> None:
        try:
            with open(TOKEN_FILE, 'w') as f:
                json.dump(self.accounts, f)
        except Exception as e:
            logger.error(f"Error saving Figma accounts to file: {e}")

    def add_account(self, user_id: str, token_dict: Dict) -> None:
        logger.info(f"Adding/updating Figma account: {user_id}")
        self.accounts[user_id] = token_dict
        if self.use_supabase:
            try:
                logger.info(f"Upserting Figma account {user_id} to Supabase.")
                self.supabase.table('tokens').upsert({
                    'user_id': user_id,
                    'token_type': 'figma',
                    'token_data': json.dumps(token_dict)
                }, on_conflict='user_id, token_type').execute()
                logger.info(f"Successfully upserted Figma account {user_id} to Supabase.")
            except Exception as e:
                logger.error(f"Error saving Figma account {user_id} to Supabase: {e}", exc_info=True)
                logger.warning(f"Falling back to saving Figma account {user_id} to local file {TOKEN_FILE}.")
                self._save_to_file()
        else:
            logger.info(f"Supabase not in use. Saving Figma account {user_id} to local file {TOKEN_FILE}.")
            self._save_to_file()

    def get_accounts(self) -> Dict[str, Dict]:
        return self.accounts

    def get_account_credentials(self, user_id: str) -> Optional[Dict]:
        return self.accounts.get(user_id)

    def get_all_account_ids(self) -> List[str]:
        return list(self.accounts.keys())

    def remove_account(self, user_id: str) -> bool:
        removed_from_memory = False
        if user_id in self.accounts:
            del self.accounts[user_id]
            removed_from_memory = True
            logger.info(f"Removed Figma account {user_id} from in-memory cache.")
        if self.use_supabase:
            try:
                logger.info(f"Deleting Figma account {user_id} from Supabase.")
                self.supabase.table('tokens').delete().eq('user_id', user_id).eq('token_type', 'figma').execute()
                logger.info(f"Delete operation for Figma account {user_id} executed on Supabase.")
            except Exception as e:
                logger.error(f"Error deleting Figma account {user_id} from Supabase: {e}", exc_info=True)
        if not self.use_supabase or removed_from_memory:
            logger.info(f"Updating local file {TOKEN_FILE} after removal attempt for {user_id}.")
            self._save_to_file()
        return removed_from_memory

    def create_auth_link_and_save_token(self, user_id: str, client_id: str, client_secret: str, redirect_uri: str, scopes: str, code: str = None):
        """
        If code is None, returns the Figma OAuth URL for user authorization.
        If code is provided, exchanges it for tokens, saves them, and returns success info.
        """
        import time
        import requests
        def start_oauth_flow():
            params = {
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'scope': scopes,
                'response_type': 'code',
                'state': str(int(time.time()))
            }
            base_url = 'https://www.figma.com/oauth'
            return f"{base_url}?" + "&".join(f"{k}={v}" for k, v in params.items())
        def exchange_code_for_token():
            url = 'https://www.figma.com/api/oauth/token'
            data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'code': code,
                'grant_type': 'authorization_code'
            }
            resp = requests.post(url, data=data)
            resp.raise_for_status()
            return resp.json()
        if code is None:
            url = start_oauth_flow()
            return {"auth_url": url}
        # Exchange code for token
        token_data = exchange_code_for_token()
        expires_at = str(time.time() + int(token_data['expires_in']))
        token_dict = {
            'access_token': token_data['access_token'],
            'refresh_token': token_data.get('refresh_token'),
            'expires_at': expires_at,
            'client_id': client_id,
            'client_secret': client_secret,
            'scopes': scopes,
            'token_type': 'figma',
            'token_uri': 'https://www.figma.com/api/oauth/token',
            'redirect_uri': redirect_uri
        }
        self.add_account(user_id, token_dict)
        return {"success": True, "user_id": user_id, "token_saved": True}

    def get_oauth_url(self, client_id: str, redirect_uri: str, scope: str, state: str) -> str:
        """
        Returns the Figma OAuth URL for user authentication.
        """
        base_url = "https://www.figma.com/oauth"
        params = [
            f"client_id={client_id}",
            f"redirect_uri={redirect_uri}",
            f"scope={scope}",
            f"state={state}",
            "response_type=code"
        ]
        return f"{base_url}?{'&'.join(params)}" 