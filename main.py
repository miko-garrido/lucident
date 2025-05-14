import os
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI, Body
from google.adk.cli.fast_api import get_fast_api_app
from litellm import completion
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

@app.post("/name_session")
async def name_session(first_message: str = Body(...)) -> str:
    prompt = f"""
        You are a helpful assistant that can help with naming sessions.
        Return ONLY the name of the session.
        Session names should be concise and descriptive.
        Session names should be no more than 4 words.
        Session names should include ONLY alphanumeric characters.
        Examples:
        - Project progress questions
        - Common calendar availability
        - Client email summaries
        - Slack channel history
        """
    user_message = f"First message: {first_message}"
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_message},
    ]
    response = completion(model="gpt-4.1-mini", messages=messages)
    return response.choices[0].message.content.strip()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))