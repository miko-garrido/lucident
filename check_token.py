import os
import ssl
from slack_sdk import WebClient

# Create a custom SSL context that doesn't verify certificates (same as in your existing code)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Get the token from environment variable
token = os.environ.get("SLACK_BOT_TOKEN")
if not token:
    print("SLACK_BOT_TOKEN environment variable is not set")
    exit(1)

# Initialize Slack client with SSL verification disabled
client = WebClient(token=token, ssl=ssl_context)

# Test the connection and print the bot info
try:
    auth_info = client.auth_test()
    print(f"Connected as: {auth_info['user']} (ID: {auth_info['user_id']})")
    print(f"Team: {auth_info['team']}")
    
    # Try to list users to test if we have users:read permission
    try:
        users = client.users_list(limit=1)
        print("\nSUCCESS: Token has users:read permission!")
        print(f"Found {len(users['members'])} users (limited to 1 for test)")
    except Exception as e:
        print(f"\nERROR: Cannot list users. Missing users:read permission.")
        print(f"Error details: {str(e)}")
        
except Exception as e:
    print(f"Error connecting to Slack: {str(e)}") 