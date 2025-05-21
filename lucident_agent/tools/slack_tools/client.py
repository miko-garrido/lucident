"""
Slack client module for the Lucident agent.

This module initializes and provides access to the Slack client.
"""

import os
import logging
import ssl
from typing import Dict, Any
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SlackClient:
    """
    Singleton class for Slack client initialization.
    """
    _instance = None
    _client = None
    _user_cache = {}  # Shared user cache
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SlackClient, cls).__new__(cls)
            cls._initialize_client()
        return cls._instance
    
    @classmethod
    def _initialize_client(cls):
        # Create a custom SSL context that doesn't verify certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Initialize Slack client with SSL verification disabled
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        if not slack_token:
            logger.error("SLACK_BOT_TOKEN environment variable not set")
            raise ValueError("SLACK_BOT_TOKEN environment variable not set")
            
        cls._client = WebClient(token=slack_token, ssl=ssl_context)
        logger.info("Slack client initialized")
    
    @property
    def client(self):
        return self._client
    
    @classmethod
    def get_user_info(cls, user_id: str) -> Dict[str, Any]:
        """
        Get user information with centralized caching to reduce API calls.
        
        Returns user information dictionary or default dict if not found.
        """
        if not user_id or user_id == "UNKNOWN":
            return {"name": "Unknown User", "real_name": "Unknown User"}
            
        # Check cache first
        if user_id in cls._user_cache:
            return cls._user_cache[user_id]
        
        # Fetch from API if not in cache
        try:
            user_info = cls._client.users_info(user=user_id)
            user_data = user_info["user"]
            cls._user_cache[user_id] = user_data
            return user_data
        except SlackApiError as e:
            logger.error(f"Error getting user info for {user_id}: {e}")
            # Store failed lookups to avoid repeated failures
            cls._user_cache[user_id] = {"name": "Unknown User", "real_name": "Unknown User"}
            return cls._user_cache[user_id]
    
    @classmethod        
    def batch_prefetch_users(cls, user_ids):
        """
        Pre-fetch user information for multiple users at once.
        """
        # Filter out already cached users
        users_to_fetch = [uid for uid in user_ids if uid not in cls._user_cache and uid != "UNKNOWN"]
        
        if not users_to_fetch:
            return
            
        logger.info(f"Prefetching information for {len(users_to_fetch)} users")
        
        # Fetch each user (Slack doesn't support batched user fetching)
        for user_id in users_to_fetch:
            try:
                user_info = cls._client.users_info(user=user_id)
                cls._user_cache[user_id] = user_info["user"]
            except SlackApiError as e:
                logger.error(f"Error batch fetching user {user_id}: {e}")
                cls._user_cache[user_id] = {"name": "Unknown User", "real_name": "Unknown User"}

# Convenience function to get the slack client
def get_slack_client():
    """
    Get the initialized Slack client instance.
    
    Returns:
        The WebClient instance for Slack API interactions
    """
    return SlackClient().client 