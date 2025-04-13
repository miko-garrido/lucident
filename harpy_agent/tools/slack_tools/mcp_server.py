from flask import Flask, request, jsonify
import os
import logging
import uuid
import sys
import os
from dotenv import load_dotenv
from flask_cors import CORS
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import ssl
from typing import Dict, Any

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import root_agent from the parent directory
from harpy_agent.agent import root_agent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create SSL context that doesn't verify certificates
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize Slack client with SSL context
slack_client = WebClient(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    ssl=ssl_context
)

# Store registered agents
registered_agents = {}

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "message": "MCP server is running"
    })

@app.route('/register', methods=['POST'])
def register_agent():
    """Register a new agent with the MCP server."""
    try:
        # Get the registration data
        registration_data = request.json
        if not registration_data:
            return jsonify({
                "status": "error",
                "error_message": "No registration data provided"
            }), 400
        
        # Generate a unique agent ID
        agent_id = str(uuid.uuid4())
        
        # Store the agent information
        registered_agents[agent_id] = {
            "name": registration_data.get("name"),
            "description": registration_data.get("description"),
            "capabilities": registration_data.get("capabilities", [])
        }
        
        logger.info(f"Registered new agent: {registration_data.get('name')} (ID: {agent_id})")
        
        return jsonify({
            "status": "success",
            "agent_id": agent_id,
            "message": "Agent registered successfully"
        })
    except Exception as e:
        logger.error(f"Error registering agent: {str(e)}")
        return jsonify({
            "status": "error",
            "error_message": str(e)
        }), 500

@app.route('/handle_message', methods=['POST'])
def handle_message():
    """Handle incoming messages using the Slack agent."""
    try:
        message_data = request.json
        if not message_data:
            return jsonify({
                "status": "error",
                "error_message": "No message data provided"
            }), 400
        
        # Process the message using the Slack agent
        result = root_agent.handle_message(message_data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        return jsonify({
            "status": "error",
            "error_message": str(e)
        }), 500

@app.route('/send_message', methods=['POST'])
def send_message():
    """Send a message through the MCP server."""
    try:
        message_data = request.json
        if not message_data:
            return jsonify({
                "status": "error",
                "error_message": "No message data provided"
            }), 400
        
        # Send the message using the Slack API
        result = send_slack_message(
            message_data.get("channel_id"),
            message_data.get("text")
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return jsonify({
            "status": "error",
            "error_message": str(e)
        }), 500

@app.route('/get_messages', methods=['POST'])
def get_messages():
    """Get messages from a Slack channel."""
    try:
        request_data = request.json
        if not request_data or 'channel' not in request_data:
            return jsonify({
                "status": "error",
                "error_message": "No channel specified"
            }), 400

        channel = request_data['channel']
        limit = request_data.get('limit', 1)  # Default to 1 message if not specified
        
        logger.info(f"Attempting to get messages from channel: {channel}")
        
        # Get messages using the Slack API
        result = get_slack_messages(channel, limit)
        return jsonify(result)

    except Exception as e:
        error_msg = f"Error getting messages: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "status": "error",
            "error_message": error_msg
        }), 500

@app.route('/list_users', methods=['GET'])
def list_users():
    """List all users in the Slack workspace."""
    try:
        logger.info("Fetching users from Slack workspace")
        
        # Get users using the Slack API
        result = list_slack_users()
        return jsonify(result)
            
    except Exception as e:
        error_msg = f"Error listing users: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "status": "error",
            "error_message": error_msg
        }), 500

@app.route('/list_channels', methods=['GET'])
def list_channels():
    """List all channels in the Slack workspace."""
    try:
        logger.info("Fetching channels from Slack workspace")
        
        # Get channels using the Slack API
        result = list_slack_channels()
        return jsonify(result)
            
    except Exception as e:
        error_msg = f"Error listing channels: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "status": "error",
            "error_message": error_msg
        }), 500

@app.route('/process_query', methods=['POST'])
def process_query():
    """Process a user query using the agent."""
    try:
        query_data = request.json
        if not query_data or 'query' not in query_data:
            return jsonify({
                "status": "error",
                "error_message": "No query provided"
            }), 400
        
        query = query_data['query']
        context = query_data.get('context', {})
        context_data = query_data.get('context_data', '')
        
        logger.info(f"Processing query: {query}")
        if context_data:
            logger.info(f"Using context data: {context_data}")
        
        # Process the query using the agent
        result = root_agent.process_with_gpt4(query)
        
        # Add context to the response if needed
        if context:
            result['context'] = context
        
        return jsonify(result)
        
    except Exception as e:
        error_msg = f"Error processing query: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "status": "error",
            "error_message": error_msg
        }), 500

@app.route('/reload_context', methods=['POST'])
def reload_context():
    """Reload the context data from the file."""
    try:
        logger.info("Reloading context data")
        
        # Reload the context data using the agent
        result = root_agent.reload_context()
        return jsonify(result)
        
    except Exception as e:
        error_msg = f"Error reloading context data: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            "status": "error",
            "error_message": error_msg
        }), 500

def send_slack_message(channel_id: str, message: str) -> Dict[str, Any]:
    """Send a message to a Slack channel.
    
    Args:
        channel_id (str): The channel ID to send the message to.
        message (str): The message to send.
        
    Returns:
        dict: status and message_id or error message.
    """
    try:
        result = slack_client.chat_postMessage(
            channel=channel_id,
            text=message
        )
        return {
            "status": "success",
            "message_id": result.get("ts")
        }
    except SlackApiError as e:
        logger.error(f"Error sending message to Slack: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e)
        }

def get_slack_messages(channel: str, limit: int = 1) -> Dict[str, Any]:
    """Get messages from a Slack channel.
    
    Args:
        channel (str): The channel name to get messages from.
        limit (int): Number of messages to retrieve.
        
    Returns:
        dict: status and messages or error message.
    """
    try:
        # Remove the '#' if present in the channel name
        if channel.startswith('#'):
            channel = channel[1:]

        # Get the channel ID from the channel name
        channel_list = slack_client.conversations_list()
        channel_id = None
        for ch in channel_list['channels']:
            if ch['name'] == channel:
                channel_id = ch['id']
                break

        if not channel_id:
            return {
                "status": "error",
                "error_message": f"Channel '{channel}' not found"
            }

        # Get messages from the channel
        result = slack_client.conversations_history(
            channel=channel_id,
            limit=limit
        )
        
        messages = result['messages'][:limit]
        return {
            "status": "success",
            "messages": messages
        }
    except SlackApiError as e:
        logger.error(f"Error getting messages from Slack: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e)
        }

def list_slack_users() -> Dict[str, Any]:
    """List all users in the Slack workspace.
    
    Returns:
        dict: status and users or error message.
    """
    try:
        result = slack_client.users_list()
        users = []
        for user in result['members']:
            # Skip bots and deleted users
            if user.get('is_bot') or user.get('deleted'):
                continue
            
            users.append({
                'id': user.get('id'),
                'name': user.get('name'),
                'real_name': user.get('real_name'),
                'is_admin': user.get('is_admin', False),
                'is_owner': user.get('is_owner', False),
                'is_primary_owner': user.get('is_primary_owner', False),
                'profile': {
                    'email': user.get('profile', {}).get('email'),
                    'image_72': user.get('profile', {}).get('image_72'),
                    'status_text': user.get('profile', {}).get('status_text'),
                    'status_emoji': user.get('profile', {}).get('status_emoji')
                }
            })
        
        return {
            "status": "success",
            "users": users
        }
    except SlackApiError as e:
        logger.error(f"Error listing Slack users: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e)
        }

def list_slack_channels() -> Dict[str, Any]:
    """List all channels in the Slack workspace.
    
    Returns:
        dict: status and channels or error message.
    """
    try:
        result = slack_client.conversations_list()
        return {
            "status": "success",
            "channels": result['channels']
        }
    except SlackApiError as e:
        logger.error(f"Error listing Slack channels: {str(e)}")
        return {
            "status": "error",
            "error_message": str(e)
        }

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 8080))
        logger.info(f"Starting MCP server on port {port}...")
        logger.info("Available endpoints:")
        logger.info("  • GET  /            - Health check")
        logger.info("  • POST /register    - Register a new agent")
        logger.info("  • POST /handle_message - Handle incoming messages")
        logger.info("  • POST /send_message - Send messages")
        logger.info("  • POST /get_messages - Get messages from a Slack channel")
        logger.info("  • GET  /list_users  - List all users in the workspace")
        logger.info("  • GET  /list_channels - List all channels in the workspace")
        logger.info("  • POST /process_query - Process a user query using the agent")
        logger.info("  • POST /reload_context - Reload context data")
        
        # Run the server with host set to '0.0.0.0' to allow external connections
        app.run(host='0.0.0.0', port=port, debug=True, threaded=True)
    except Exception as e:
        logger.error(f"Failed to start MCP server: {str(e)}") 