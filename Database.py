 from dotenv import load_dotenv, find_dotenv
from supabase import create_client, Client
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        dotenv_path = find_dotenv()
        load_dotenv(dotenv_path)
        
        self._url = os.getenv("SUPABASE_URL")
        self._key = os.getenv("SUPABASE_KEY")
        
        if not self._url or not self._key:
            logger.error("Missing Supabase environment variables. Please set SUPABASE_URL and SUPABASE_KEY")
            raise ValueError("Missing Supabase environment variables")
            
        # Initialize without proxy for v2.3.5
        self._client = create_client(
            supabase_url=self._url,
            supabase_key=self._key
        )
    
    @property
    def client(self) -> Client:
        return self._client