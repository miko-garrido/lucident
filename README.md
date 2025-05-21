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

Visit `http://localhost:8000` to interact with Lucident.

## Google Cloud Run Deployment

1. Ensure you have gcloudCLI installed on your machine. You can find instructions here: https://cloud.google.com/sdk/docs/install

2. Authenticate Google Cloud
```bash
gcloud auth login
```

3. Set the project to the project ID
```bash
gcloud config set project gen-lang-client-0922281168
```

3. Export all .env variables
```bash
export $(grep -v '^#' .env | xargs)
```

4. Begin the deployment
```bash
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$GOOGLE_CLOUD_LOCATION" \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars="\
CLICKUP_API_KEY=$CLICKUP_API_KEY,\
CLICKUP_CLIENT_ID=$CLICKUP_CLIENT_ID,\
CLICKUP_CLIENT_SECRET=$CLICKUP_CLIENT_SECRET,\
CLICKUP_ACCESS_TOKEN=$CLICKUP_ACCESS_TOKEN,\
OPENAI_API_KEY=$OPENAI_API_KEY,\
SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN,\
GOOGLE_API_KEY=$GOOGLE_API_KEY,\
GOOGLE_GENAI_USE_VERTEXAI=$GOOGLE_GENAI_USE_VERTEXAI,\
GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,\
GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION,\
AGENT_PATH=$AGENT_PATH,\
SERVICE_NAME=$SERVICE_NAME,\
APP_NAME=$APP_NAME,\
SUPABASE_URL=$SUPABASE_URL,\
SUPABASE_KEY=$SUPABASE_KEY"
```

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

#### Slack Tools
The Slack tools module provides functionality for the Lucident agent to interact with Slack workspaces:

**Message Operations**
- Send messages to channels
- Update existing messages
- Get channel message history
- Get thread replies

**User Operations**
- Get bot user ID and information
- List workspace users

**Channel Operations**
- List available channels
- Get channel ID from name or ID

**Document Processing**
- Detect and list files shared in channels or threads
- Get detailed file information
- Read and extract text from various document types
- Process PDFs with OCR capabilities for scanned documents
- Extract text from images using OCR

**Document Processing Capabilities**
- Fully supported formats (text extraction): Plain text, Markdown, HTML, XML, JSON, CSV, PDF
- OCR support: Images (PNG, JPG, GIF, etc.) and scanned PDFs
- Not yet supported: Office documents, Spreadsheets

**Document Processing Requirements**
- PDF processing: `pip install PyPDF2`
- OCR: `pip install pytesseract Pillow pdf2image`
- External dependencies:
  - Tesseract OCR engine
  - Poppler (for PDF to image conversion)

## Development

Built on Google's Agent Development Kit (ADK), Harpy leverages:
- LiteLLM for flexible selection of LLM model
- Large language models for reasoning and natural language
- ADK's multi-agent architecture
- Tool integration framework