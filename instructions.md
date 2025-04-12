# Harpy Project Plan - Simplified Implementation

## System Overview
Harpy is an AI cross-platform project management assistant that intelligently understands user queries and uses its access to ClickUp, Gmail, and Slack to answer questions. It is built fully on Google's Agent Development Kit (ADK). For this initial implementation, Slack and Gmail are placeholders and will be expanded.

## Technical Requirements

### Core Dependencies
- Google ADK
- ClickUp API v2
- OpenAI API

## Project Structure
```
harpy/
├── __init__.py
├── agent.py
├── config.py
├── sub_agents/
│   ├── clickup_agent.py
│   ├── slack_agent.py
│   └── gmail_agent.py
├── tools/
│   ├── clickup_tools.py
│   ├── slack_tools.py
│   └── gmail_tools.py
├── eval/
│   ├── data/
│   │   ├── clickup_tasks.evalset.json
│   │   └── task_summaries.evalset.json
│   └── test_eval.py
├── .env.example
└── README.md
```

## Core Components

### 1. Configuration (config.py)
The configuration module defines the core settings for the Harpy agent system. It uses Pydantic for type-safe configuration management, allowing easy modification of model parameters, agent names, and other runtime settings.

### 2. Prompts (prompts.py)
This module contains the core instructions and guidelines that shape Harpy's behavior. The global instruction defines Harpy's primary identity as a project management assistant, while specific instructions detail how to handle task-related queries. The prompts are structured to ensure consistent, clear, and actionable responses to user requests.

### 3. Sub-Agents

#### ClickUp Agent
The ClickUp agent specializes in retrieving information from ClickUp. It must be able to take into account ClickUp's general structure. It's configured with the ClickUp tool and specific instructions for handling task-related queries. The agent processes user requests, formats API responses to the main agent, and manages task data retrieval and presentation.

#### Slack Agent
Leave this as a placeholder for now.

#### Gmail Agent
Leave this as a placeholder for now.

### 4. Tools

### ClickUp Tool
The ClickUp tool provides direct API interaction with ClickUp's services. It manages all reading API requests, and processes responses. The tool implements error handling for API limitations.

### Gmail Tool
Placeholder

### Slack Tool
Placeholder

### 5. Main Agent (agent.py)
The main agent orchestrates the entire system, coordinating between sub-agents and tools. It processes incoming requests, routes them to appropriate sub-agents, and manages the overall conversation flow. The agent includes callbacks for rate limiting, pre-processing, and error handling.

## Goal

We should be able to run the agent by going to the top level directory

```bash
adk web
```