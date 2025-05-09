import streamlit as st
from lucident_agent.agent import root_agent # Assuming root_agent is an instance of ADK agent.
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part # Used for constructing messages
# Corrected import path based on grep search and previous error
from google.adk.agents import RunConfig
from google.adk.agents.run_config import StreamingMode
import uuid # For generating unique session IDs
import time # For simulating streaming effect if needed, or for small delays

st.set_page_config(layout="wide")

# App title
st.title("Lucident AI Chat - Streaming")

# Initialize Runner and services
if "session_service" not in st.session_state: # SessionService should persist across the session
    st.session_state.session_service = InMemorySessionService()

# Runner is initialized once and stored in session_state
if "runner" not in st.session_state:
    st.session_state.runner = Runner(
        agent=root_agent,
        app_name="streamlit_chat_app_streaming", # Consistent app name
        session_service=st.session_state.session_service
    )

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if "session_id" not in st.session_state:
    try:
        session = st.session_state.session_service.create_session(
            app_name="streamlit_chat_app_streaming",
            user_id=st.session_state.user_id,
        )
        st.session_state.session_id = session.id
    except Exception as e:
        st.error(f"Failed to create session: {e}")
        st.stop()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("What is up?"):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Prepare for assistant's streaming response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        list_of_completed_utterances = [] # Stores each complete message from the agent
        current_streaming_ui_buffer = "" # For the token-by-token effect of the current utterance being formed
        
        try:
            new_user_message = Content(parts=[Part(text=prompt)])
            
            if not st.session_state.session_id:
                raise ValueError("Session ID is not initialized.")

            run_config = RunConfig(streaming_mode=StreamingMode.SSE)

            # Use the session-state runner
            events = st.session_state.runner.run(
                user_id=st.session_state.user_id,
                session_id=st.session_state.session_id,
                new_message=new_user_message,
                run_config=run_config
            )

            for event_idx, event in enumerate(events):
                if event.author == root_agent.name and event.content and hasattr(event.content, 'parts'):
                    text_chunk = "".join(p.text for p in event.content.parts if hasattr(p, 'text') and p.text)
                    
                    if text_chunk:
                        is_partial = getattr(event, 'partial', False)
                        
                        if is_partial:
                            current_streaming_ui_buffer += text_chunk
                        else: # Not partial, this event's text_chunk is a complete utterance
                            # Append the fully formed segment (previous partials + this final chunk)
                            completed_segment = current_streaming_ui_buffer + text_chunk
                            list_of_completed_utterances.append(completed_segment)
                            current_streaming_ui_buffer = "" # Reset for next utterance
                        
                        # Update UI placeholder
                        display_text = "\n\n".join(list_of_completed_utterances)
                        if current_streaming_ui_buffer: # Show current partial stream if any
                            if list_of_completed_utterances: # Add separator if there's already complete content
                                display_text += "\n\n"
                            display_text += current_streaming_ui_buffer
                        
                        message_placeholder.markdown(display_text + "▌")

            # After loop, finalize display and store history
            # Consolidate the final response from completed utterances and any trailing partial buffer
            final_agent_response_parts = list(list_of_completed_utterances) # Make a mutable copy
            if current_streaming_ui_buffer: # If loop ended on partials
                final_agent_response_parts.append(current_streaming_ui_buffer)
            
            final_agent_response = "\n\n".join(final_agent_response_parts)
            
            message_placeholder.markdown(final_agent_response) # Final render without cursor
            
            if final_agent_response: # Only add to history if there's content
                st.session_state.messages.append({"role": "assistant", "content": final_agent_response})
            
        except Exception as e:
            error_message = f"Error interacting with agent: {e}"
            message_placeholder.markdown(error_message)
            # Add the error message to history
            st.session_state.messages.append({"role": "assistant", "content": error_message})

# Sidebar for potential future use (e.g., settings, history, etc.)
with st.sidebar:
    st.header("Controls / Info")
    # Add any sidebar elements here if needed in the future
    st.write("This is a chat application using the Lucident ADK agent.") 