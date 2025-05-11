# Streaming in ADK

Streaming in ADK enables low-latency, bidirectional voice and video interaction for agents using Gemini Live API. Agents can process text, audio, and video inputs, and provide real-time text and audio output.

## Supported Models
- Requires Gemini models with Live API support (see Google AI Studio or Vertex AI docs for model IDs).

## Setup
1. Create and activate a Python virtual environment:
   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install ADK:
   ```sh
   pip install google-adk
   ```
3. Set up your agent project with an agent using a supported Gemini model.

## Using Streaming
- Run your agent with `adk web` for a dev UI supporting text, voice, and video.
- For custom apps, use FastAPI and ADK's streaming APIs to build real-time chat or multimodal interfaces.

## Benefits
- Real-time, natural conversations
- Interrupt agent responses with voice
- Multimodal: text, audio, video

Streaming mode makes agent interactions more responsive and human-like. 