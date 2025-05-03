import os
import logging
import requests
import json
from typing import Dict, Any, Optional
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai.api_key = os.environ.get("OPENAI_API_KEY")

# MCP Server configuration
MCP_SERVER_URL = "http://localhost:3000/slack"
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")

# Load context from file
CONTEXT_FILE = os.path.join(os.path.dirname(__file__), "context.txt")
context_data = ""

def check_slack_token():
    """Check if Slack token is available."""
    if not SLACK_BOT_TOKEN:
        raise ValueError("SLACK_BOT_TOKEN environment variable is not set")
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

def load_context():
    """Load context data from the context.txt file."""
    global context_data
    try:
        with open(CONTEXT_FILE, 'r') as f:
            context_data = f.read().strip()
        logger.info("Context data loaded successfully")
        return context_data
    except Exception as e:
        logger.error(f"Error loading context data: {str(e)}")
        return ""

def reload_context() -> Dict[str, Any]:
    """Reload the context data from the file.
    
    Returns:
        dict: status and context data or error message.
    """
    try:
        global context_data
        context_data = load_context()
        return {
            "status": "success",
            "context_data": context_data
        }
    except Exception as e:
        logger.error(f"Error reloading context data: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e)
        }

# Load context on startup
load_context()

# Check required environment variables
if not SLACK_BOT_TOKEN:
    raise ValueError("SLACK_BOT_TOKEN environment variable is not set")
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

def process_with_gpt4(query: str) -> Dict[str, Any]:
    """Process a query using OpenAI's GPT-4 model.

    Args:
        query (str): The query to process.

    Returns:
        dict: status and response or error message.
    """
    check_slack_token()  # Only check when function is called
    try:
        # Include context in the system message
        system_message = f"""You are a helpful assistant integrated with Slack.
        
Context information:
{context_data}

Use this context to inform your responses when relevant."""
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": query}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        return {
            "status": "success",
            "response": response.choices[0].message.content
        }
    except Exception as e:
        logger.error(f"Error processing with GPT-4: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e)
        }

def send_via_mcp(channel_id: str, message: str) -> Dict[str, Any]:
    """Send a message through the MCP server.

    Args:
        channel_id (str): The channel ID to send the message to.
        message (str): The message to send.

    Returns:
        dict: status and message_id or error message.
    """
    check_slack_token()  # Only check when function is called
    try:
        payload = {
            "channel_id": channel_id,
            "text": message
        }
        
        response = requests.post(
            f"{MCP_SERVER_URL}/send_message",
            json=payload,
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "status": "error",
                "error_message": f"Failed to send message: {response.text}"
            }
    except Exception as e:
        logger.error(f"Error sending message via MCP: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e)
        }

def get_channel_messages(channel: str, limit: int = 1) -> Dict[str, Any]:
    """Get messages from a Slack channel through the MCP server.

    Args:
        channel (str): The name of the channel to get messages from (with or without #).
        limit (int, optional): Number of messages to retrieve. Defaults to 1.

    Returns:
        dict: status and messages or error message.
    """
    check_slack_token()  # Only check when function is called
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

def list_users() -> Dict[str, Any]:
    """List all users in the Slack workspace through the MCP server.

    Returns:
        dict: status and users or error message.
    """
    check_slack_token()  # Only check when function is called
    try:
        response = requests.get(
            f"{MCP_SERVER_URL}/list_users",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "status": "error",
                "error_message": f"Failed to list users: {response.text}"
            }
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e)
        }

def list_channels() -> Dict[str, Any]:
    """List all channels in the Slack workspace through the MCP server.

    Returns:
        dict: status and channels or error message.
    """
    try:
        response = requests.get(
            f"{MCP_SERVER_URL}/list_channels",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "status": "error",
                "error_message": f"Failed to list channels: {response.text}"
            }
    except Exception as e:
        logger.error(f"Error listing channels: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e)
        }

def process_query(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Process a user query through the MCP server.

    Args:
        query (str): The query to process.
        context (Optional[Dict[str, Any]], optional): Additional context for the query. Defaults to None.

    Returns:
        dict: status and response or error message.
    """
    try:
        # Include the loaded context data
        payload = {
            "query": query,
            "context_data": context_data
        }
        
        if context:
            payload["context"] = context
        
        response = requests.post(
            f"{MCP_SERVER_URL}/process_query",
            json=payload,
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
        )
        
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            return {
                "status": "error",
                "error_message": f"Failed to process query: {response.text}"
            }
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e)
        }

def get_mcp_response(endpoint: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get a direct response from the MCP server.

    Args:
        endpoint (str): The MCP server endpoint to call.
        method (str, optional): HTTP method to use. Defaults to "GET".
        payload (Optional[Dict[str, Any]], optional): Payload to send with the request. Defaults to None.

    Returns:
        dict: The raw response from the MCP server.
    """
    try:
        headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
        
        if method.upper() == "GET":
            response = requests.get(
                f"{MCP_SERVER_URL}/{endpoint}",
                headers=headers
            )
        elif method.upper() == "POST":
            response = requests.post(
                f"{MCP_SERVER_URL}/{endpoint}",
                json=payload,
                headers=headers
            )
        else:
            return {
                "status": "error",
                "error_message": f"Unsupported HTTP method: {method}"
            }
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "status": "error",
                "error_message": f"Failed to get response from MCP server: {response.text}"
            }
    except Exception as e:
        logger.error(f"Error getting MCP response: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e)
        }

def handle_message(message_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming messages and process them with GPT-4 and MCP server.

    Args:
        message_data (dict): The message data containing channel_id and text.

    Returns:
        dict: status and response or error message.
    """
    try:
        channel_id = message_data.get("channel_id")
        text = message_data.get("text", "")

        logger.info(f"Handling message: {text}")

        # Check if this is a request to get messages from a channel
        if text.lower().startswith("get me") and "#" in text:
            logger.info("Processing channel message request")
            # Extract the channel name
            channel = text[text.index("#"):]
            channel = channel.split()[0]  # Get just the channel part
            
            logger.info(f"Extracted channel name: {channel}")
            
            # Get the messages
            result = get_channel_messages(channel)
            logger.info(f"Got channel messages result: {result}")
            
            if result["status"] == "success":
                messages = result["messages"]
                response = "Here are the messages:\n"
                for msg in messages:
                    response += f"User {msg['user']} said: {msg['text']}\n"
                
                # Send the response through MCP server
                if channel_id:
                    mcp_response = send_via_mcp(channel_id, response)
                    return {
                        "status": "success",
                        "response": response,
                        "mcp_response": mcp_response
                    }
                else:
                    return {
                        "status": "success",
                        "response": response
                    }
            else:
                error_msg = result.get("error_message", "Unknown error getting messages")
                logger.error(f"Error getting messages: {error_msg}")
                return result
        
        # Check if this is a request to list users
        elif text.lower().startswith("list users"):
            logger.info("Processing list users request")
            result = list_users()
            
            if result["status"] == "success":
                users = result["users"]
                response = "Here are the users in the workspace:\n"
                for user in users:
                    response += f"• {user['real_name']} (@{user['name']})\n"
                
                # Send the response through MCP server
                if channel_id:
                    mcp_response = send_via_mcp(channel_id, response)
                    return {
                        "status": "success",
                        "response": response,
                        "mcp_response": mcp_response
                    }
                else:
                    return {
                        "status": "success",
                        "response": response
                    }
            else:
                error_msg = result.get("error_message", "Unknown error listing users")
                logger.error(f"Error listing users: {error_msg}")
                return result
        
        # Check if this is a request to list channels
        elif text.lower().startswith("list channels"):
            logger.info("Processing list channels request")
            result = list_channels()
            
            if result["status"] == "success":
                channels = result["channels"]
                response = "Here are the channels in the workspace:\n"
                for channel in channels:
                    response += f"• #{channel['name']}\n"
                
                # Send the response through MCP server
                if channel_id:
                    mcp_response = send_via_mcp(channel_id, response)
                    return {
                        "status": "success",
                        "response": response,
                        "mcp_response": mcp_response
                    }
                else:
                    return {
                        "status": "success",
                        "response": response
                    }
            else:
                error_msg = result.get("error_message", "Unknown error listing channels")
                logger.error(f"Error listing channels: {error_msg}")
                return result
        
        # Check if this is a request to get raw MCP response
        elif text.lower().startswith("get mcp response"):
            logger.info("Processing raw MCP response request")
            # Extract the endpoint and method
            parts = text.split()
            if len(parts) < 4:
                return {
                    "status": "error",
                    "error_message": "Invalid format. Use: get mcp response [endpoint] [method] [payload]"
                }
            
            endpoint = parts[3]
            method = parts[4] if len(parts) > 4 else "GET"
            payload = None
            
            # Try to parse payload if provided
            if len(parts) > 5:
                try:
                    payload_str = " ".join(parts[5:])
                    payload = json.loads(payload_str)
                except json.JSONDecodeError:
                    return {
                        "status": "error",
                        "error_message": "Invalid JSON payload"
                    }
            
            # Get the raw response from MCP server
            result = get_mcp_response(endpoint, method, payload)
            
            # Return the raw response
            return {
                "status": "success",
                "raw_mcp_response": result
            }
        
        # Otherwise, process with GPT-4
        logger.info("Processing with GPT-4")
        gpt_response = process_with_gpt4(text)
        
        if gpt_response["status"] == "success":
            # Send response through MCP server if we have a channel_id
            if channel_id:
                mcp_response = send_via_mcp(channel_id, gpt_response["response"])
                return {
                    "status": "success",
                    "response": gpt_response["response"],
                    "mcp_response": mcp_response
                }
            else:
                return {
                    "status": "success",
                    "response": gpt_response["response"]
                }
        else:
            return gpt_response
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e)
        }

# Export all tools
__all__ = [
    'process_with_gpt4',
    'send_via_mcp',
    'handle_message',
    'get_channel_messages',
    'list_users',
    'list_channels',
    'process_query',
    'get_mcp_response',
    'reload_context',
    'load_context'
] 