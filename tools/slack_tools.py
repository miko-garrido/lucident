import requests
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def get_channel_messages(channel: str, limit: int = 1) -> Dict[str, Any]:
    """Get messages from a Slack channel through the MCP server.

    Args:
        channel (str): The name of the channel to get messages from (with or without #).
        limit (int, optional): Number of messages to retrieve. Defaults to 1.

    Returns:
        dict: status and messages or error message.
    """
    try:
        payload = {
            "channel": channel,
            "limit": limit
        }
        
        response = requests.post(
            f"{MCP_SERVER_URL}/get_messages",
            json=payload,
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "status": "error",
                "error_message": f"Failed to get messages: {response.text}"
            }
    except Exception as e:
        logger.error(f"Error getting messages from channel: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e)
        }