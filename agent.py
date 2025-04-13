import os
import asyncio
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For multi-model support
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.tools.tool_context import ToolContext
from google.genai import types # For creating message Content/Parts
from dotenv import load_dotenv  
from config import Config
from sub_agents.gmail_agent import gmail_agent
from sub_agents.slack_agent import slack_agent
from sub_agents.clickup_agent import clickup_agent

AGENT_MODEL = Config.MODEL_NAME
APP_NAME = Config.APP_NAME
USER_ID = Config.USER_ID
SESSION_ID = Config.SESSION_ID

main_agent = Agent(
    name="main_agent",
    model=LiteLlm(model=AGENT_MODEL), # Specifies the underlying LLM
    description="Provides weather information for specific cities.", # Crucial for delegation later
    instruction="You are the main Weather Agent coordinating a team. Your primary responsibility is to provide weather information. "
                "Use the 'get_weather' tool ONLY for specific weather requests (e.g., 'weather in London'). "
                "When providing weather information, use the temperature unit from state['user_preference_temperature_unit'] if available. "
                "You have specialized sub-agents: "
                "1. 'greeting_agent': Handles simple greetings like 'Hi', 'Hello'. Delegate to it for these. "
                "2. 'farewell_agent': Handles simple farewells like 'Bye', 'See you'. Delegate to it for these. "
                "Analyze the user's query. If it's a greeting, delegate to 'greeting_agent'. If it's a farewell, delegate to 'farewell_agent'. "
                "If it's a weather request, handle it yourself using 'get_weather'. "
                "For anything else, respond appropriately or state you cannot handle it.", # Make the tool available to this agent
    sub_agents=[gmail_agent, slack_agent, clickup_agent],
    output_key="last_weather_report"  # Save weather report to state
)

session_service = InMemorySessionService()

initial_state = {
    "user_preference_temperature_unit": "Fahrenheit"
}

session = session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID,
    state=initial_state
)

runner_agent_team = Runner(
        agent=weather_agent, # Use the root agent object
        app_name=APP_NAME,       # Use the specific app name
        session_service=session_service # Use the specific session service
        )

async def call_agent_async(query: str):
  """Sends a query to the agent and prints the final response."""
  print(f"\n>>> User Query: {query}")

  # Prepare the user's message in ADK format
  content = types.Content(role='user', parts=[types.Part(text=query)])

  final_response_text = "Agent did not produce a final response." # Default

  # Key Concept: run_async executes the agent logic and yields Events.
  # We iterate through events to find the final answer.
  async for event in runner_agent_team.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content):
      # You can uncomment the line below to see *all* events during execution
      # print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")

      # Key Concept: is_final_response() marks the concluding message for the turn.
      if event.is_final_response():
          if event.content and event.content.parts:
             # Assuming text response in the first part
             final_response_text = event.content.parts[0].text
          elif event.actions and event.actions.escalate: # Handle potential errors/escalations
             final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
          # Add more checks here if needed (e.g., specific error codes)
          break # Stop processing events once the final response is found

  print(f"<<< Agent Response: {final_response_text}")

async def run_team_conversation():
    print("\n--- Testing Agent Team Delegation ---")

    print(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")

    # Corrected print statement to show the actual root agent's name
    print(f"Runner created for agent '{weather_agent.name}'.")

    # Always interact via the root agent's runner, passing the correct IDs
    await call_agent_async("Hello!")
    await call_agent_async("What is the weather in New York?")
    await call_agent_async("What is the weather in Tokyo?")
    await call_agent_async("What was the weather again, in New York but in Celsius?")
    await call_agent_async("Thanks, bye!")

# Execute the conversation
# Note: This may require API keys for the models used by root and sub-agents!
asyncio.run(run_team_conversation())