import os
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from lucident_agent.config import Config # Triggers context loading, not sure why it does that

load_dotenv()

db_url = os.getenv("SUPABASE_DB_URL")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_DB_URL = db_url
ALLOWED_ORIGINS = ["http://localhost", "http://localhost:8080", "*"]
SERVE_WEB_INTERFACE = True

app: FastAPI = get_fast_api_app(
    agent_dir=APP_DIR,
    session_db_url=SESSION_DB_URL,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))