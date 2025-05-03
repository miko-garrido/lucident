# Lucident AI: Project Management Assistant

Lucident is an AI-powered project management assistant built on Google's Agent Development Kit (ADK). It provides a unified interface for managing projects across ClickUp, Gmail, and Slack, intelligently understanding and responding to user queries about project status, tasks, and communications.

## Features

- **Unified Project Interface**: Single point of interaction for project-related queries
- **Cross-Platform Integration**: 
  - ClickUp: User, time, task, and overall project management
  - Gmail: Project communications
  - Slack: Team and client updates and discussions
- **Natural Language Understanding**: Process complex queries about projects and tasks
- **Intelligent Response System**: Combine information from multiple platforms for comprehensive answers


## Setup

1. **Create and activate a virtual environment:**
```bash
# Create the virtual environment
python3 -m venv .venv

# Activate the virtual environment (run this in your terminal)
source .venv/bin/activate

# Upgrade pip (recommended)
pip install --upgrade pip
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables:**
```bash
# Copy the example environment file
cp .env.example .env
# Fill in your API credentials in the .env file
```

4. **Start the ADK web interface:**
```bash
adk web
```

Visit `http://localhost:8000` to interact with Harpy.

## Technical Implementation

### Main Agent
The main agent (`agent.py`) uses Google ADK's `LlmAgent` to:
- Process user queries
- Route requests to appropriate sub-agents
- Coordinate responses across platforms

### Sub-Agents
Each sub-agent specializes in a specific platform:
- ClickUp Agent: Retrieval and context building of ClickUp-specific data
- Gmail Agent: Retrieval and context building of Gmail-specific data
- Slack Agent: Retrieval and context building of Slack-specific data

### Tools
Platform-specific tools handle API interactions:
- Authentication and error handling
- Data retrieval and processing

## Development

Built on Google's Agent Development Kit (ADK), Harpy leverages:
- LiteLLM for flexible selection of LLM model
- Large language models for reasoning and natural language
- ADK's multi-agent architecture
- Tool integration framework