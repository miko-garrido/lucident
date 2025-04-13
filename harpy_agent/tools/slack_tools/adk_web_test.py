from flask import Flask, request, jsonify, render_template_string
import os
import logging
from dotenv import load_dotenv
from flask_cors import CORS
from .agent import root_agent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Google ADK Agent Test Interface</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .chat-container {
            border: 1px solid #ccc;
            border-radius: 5px;
            padding: 20px;
            margin-bottom: 20px;
            height: 400px;
            overflow-y: auto;
        }
        .message {
            margin-bottom: 10px;
            padding: 10px;
            border-radius: 5px;
        }
        .user-message {
            background-color: #e6f7ff;
            margin-left: 20%;
        }
        .agent-message {
            background-color: #f0f0f0;
            margin-right: 20%;
        }
        .input-container {
            display: flex;
        }
        #message-input {
            flex-grow: 1;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
            margin-right: 10px;
        }
        button {
            padding: 10px 20px;
            background-color: #4285f4;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        button:hover {
            background-color: #3367d6;
        }
        .tools-container {
            margin-top: 20px;
            border: 1px solid #ccc;
            border-radius: 5px;
            padding: 20px;
        }
        .tool {
            margin-bottom: 10px;
            padding: 10px;
            background-color: #f9f9f9;
            border-radius: 5px;
        }
        .tool-name {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .tool-description {
            margin-bottom: 5px;
        }
        .tool-parameters {
            margin-left: 20px;
        }
    </style>
</head>
<body>
    <h1>Google ADK Agent Test Interface</h1>
    <div class="chat-container" id="chat-container"></div>
    <div class="input-container">
        <input type="text" id="message-input" placeholder="Type your message here...">
        <button onclick="sendMessage()">Send</button>
    </div>

    <div class="tools-container">
        <h2>Available Tools</h2>
        <div id="tools-list"></div>
    </div>

    <script>
        // Fetch and display available tools
        fetch('/get_tools')
            .then(response => response.json())
            .then(data => {
                const toolsList = document.getElementById('tools-list');
                data.tools.forEach(tool => {
                    const toolDiv = document.createElement('div');
                    toolDiv.className = 'tool';
                    
                    const nameDiv = document.createElement('div');
                    nameDiv.className = 'tool-name';
                    nameDiv.textContent = tool.name;
                    
                    const descDiv = document.createElement('div');
                    descDiv.className = 'tool-description';
                    descDiv.textContent = tool.description;
                    
                    const paramsDiv = document.createElement('div');
                    paramsDiv.className = 'tool-parameters';
                    
                    if (tool.parameters && Object.keys(tool.parameters).length > 0) {
                        const paramsTitle = document.createElement('div');
                        paramsTitle.textContent = 'Parameters:';
                        paramsDiv.appendChild(paramsTitle);
                        
                        const paramsList = document.createElement('ul');
                        for (const [paramName, paramInfo] of Object.entries(tool.parameters)) {
                            const paramItem = document.createElement('li');
                            paramItem.textContent = `${paramName} (${paramInfo.type}): ${paramInfo.description}`;
                            paramsList.appendChild(paramItem);
                        }
                        paramsDiv.appendChild(paramsList);
                    } else {
                        paramsDiv.textContent = 'No parameters';
                    }
                    
                    toolDiv.appendChild(nameDiv);
                    toolDiv.appendChild(descDiv);
                    toolDiv.appendChild(paramsDiv);
                    toolsList.appendChild(toolDiv);
                });
            })
            .catch(error => {
                console.error('Error fetching tools:', error);
                document.getElementById('tools-list').innerHTML = '<p>Error loading tools</p>';
            });

        function addMessage(message, isUser) {
            const chatContainer = document.getElementById('chat-container');
            const messageDiv = document.createElement('div');
            messageDiv.className = isUser ? 'message user-message' : 'message agent-message';
            messageDiv.textContent = message;
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function sendMessage() {
            const input = document.getElementById('message-input');
            const message = input.value.trim();
            
            if (message) {
                addMessage(message, true);
                input.value = '';
                
                fetch('/process_message', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ text: message })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // Check if the response is a string or an object
                        if (typeof data.response === 'string') {
                            addMessage(data.response, false);
                        } else if (data.response && typeof data.response === 'object') {
                            // If response is an object, try to extract the message content
                            if (data.response.response) {
                                addMessage(data.response.response, false);
                            } else {
                                addMessage(JSON.stringify(data.response), false);
                            }
                        } else {
                            addMessage('Error: Invalid response format', false);
                        }
                    } else {
                        addMessage('Error: ' + (data.error_message || 'Unknown error'), false);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    addMessage('Error processing message', false);
                });
            }
        }

        // Allow sending message with Enter key
        document.getElementById('message-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    """Render the web interface."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/get_tools', methods=['GET'])
def get_tools():
    """Get the tools available to the agent."""
    try:
        tools = root_agent.tools
        return jsonify({
            "status": "success",
            "tools": tools
        })
    except Exception as e:
        logger.error(f"Error getting tools: {str(e)}")
        return jsonify({
            "status": "error",
            "error_message": str(e)
        }), 500

@app.route('/process_message', methods=['POST'])
def process_message():
    """Process a message using the Slack agent."""
    try:
        message_data = request.json
        if not message_data or 'text' not in message_data:
            return jsonify({
                "status": "error",
                "error_message": "No message text provided"
            }), 400
        
        # Process the message using the Slack agent
        result = root_agent.handle_message({"text": message_data['text'], "channel_id": "test"})
        
        # Return the result directly since it already has the correct structure
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return jsonify({
            "status": "error",
            "error_message": str(e)
        }), 500

if __name__ == '__main__':
    try:
        port = int(os.environ.get('ADK_PORT', 5000))
        logger.info(f"Starting ADK web test interface on port {port}...")
        logger.info("Available endpoints:")
        logger.info("  • GET  /              - Web interface")
        logger.info("  • GET  /get_tools     - Get available tools")
        logger.info("  • POST /process_message - Process messages")
        
        # Run the server with host set to '0.0.0.0' to allow external connections
        app.run(host='0.0.0.0', port=port, debug=True, threaded=True)
    except Exception as e:
        logger.error(f"Failed to start ADK web test interface: {str(e)}") 