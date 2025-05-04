import os
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.sessions import InMemorySessionService
from lucident_agent.config import Config

load_dotenv()

APP_NAME = os.getenv("APP_NAME")

USER_ID = Config.USER_ID
SESSION_ID = Config.SESSION_ID
TIMEZONE = Config.TIMEZONE

session_service = InMemorySessionService()
session = session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
# SESSION_DB_URL = "sqlite:///./sessions.db"
ALLOWED_ORIGINS = ["http://localhost", "http://localhost:8080", "*"]
SERVE_WEB_INTERFACE = True

app: FastAPI = get_fast_api_app(
    agent_dir=APP_DIR,
    # session_db_url=SESSION_DB_URL,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))