"""
Slack client module for the Lucident agent.

This module initializes and provides access to the Slack client.
"""

import os
import logging
import ssl
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

# Convenience function to get the slack client
def get_slack_client():
    """
    Get the initialized Slack client instance.
    
    Returns:
        The WebClient instance for Slack API interactions
    """
    return SlackClient().client 