from google.adk.agents import Agent
# from google.adk.models.lite_llm import LiteLlm # Original ADK import
from ..adk_patch.lite_llm_patched import LiteLlm # Relative import for patched LiteLlm
from google.genai import types
from dotenv import load_dotenv  
from lucident_agent.config import Config
from ..tools.calendar_tools import (
    list_calendar_accounts,
    add_new_calendar_account,
    list_calendar_events,
    create_calendar_event,
    update_calendar_event,
    delete_calendar_event,
    get_calendar_event,
    quick_add_calendar_event,
    add_event_with_recurrence,
    add_event_with_reminders,
    check_free_busy,
    find_free_slots,
    create_and_send_calendar_event,
    send_calendar_invite,
    create_event_with_attendees,
    find_mutual_free_slots
)
from ..tools.basic_tools import (
    get_current_time,
    calculate,
    calculate_date,
    convert_ms_to_hhmmss,
    convert_datetime_to_unix
)

load_dotenv()

OPENAI_MODEL = Config.OPENAI_MODEL
GEMINI_MODEL = Config.GEMINI_MODEL
TIMEZONE = Config.TIMEZONE

# Create the calendar agent
calendar_agent = Agent(
    name="calendar_agent",
    model=LiteLlm(model=OPENAI_MODEL),
    # model=GEMINI_MODEL,
    description=(
        "Manages and interacts with Google Calendar, allowing users to schedule, view, edit, and manage calendar events. "
        "Supports natural language input for event creation and searching."
    ),
    instruction=(
        "You are a specialized Google Calendar assistant. Your primary function is to interact with Google Calendar using the provided tools. "
        "IMPORTANT: You must ALWAYS start by listing available accounts using list_calendar_accounts() before performing any other operations. "
        "After listing accounts, you can proceed with operations like creating, viewing, editing, or deleting events."
        "When responding to user requests, ALWAYS follow these steps:"
        "1. Parse the user's natural language request into structured event data when creating or editing events"
        "2. Confirm understanding of the request with specific details (e.g., 'Creating a meeting with Anna tomorrow at 3 PM, is that correct?')"
        "3. Handle errors gracefully and provide clear error messages to the user"
        "4. Convert all times to the user's time zone when necessary"
        "5. Give concise and clear responses, focusing on the task at hand"
        "For event creation, help the user by extracting key information:"
        "- Event summary/title from their description"
        "- Start and end times, parsing natural language like 'tomorrow' or 'next Friday'"
        "- Location details if mentioned"
        "- Attendees who should be invited"
        "- Recurrence patterns if the event should repeat"
        "- Reminder settings if mentioned"
        "If the user mentions a time zone, use it. Otherwise, default to their local time zone."
        "For scheduling conflicts, warn the user and suggest alternative times or dates."
        "Focus solely on Google Calendar-related actions and provide helpful responses that guide the user through their request."
        "\n\nIMPORTANT FOR SEQUENTIAL OPERATIONS:"
        "1. When creating an event with attendees, automatically send the invite - no need to ask for confirmation"
        "2. When updating an event, always include the 'updates' parameter, even if it's an empty dictionary: updates={}"
        "3. When the user asks to create an event and send invites in one request, use create_event_with_attendees instead of create_calendar_event"
        "4. If sending an invite after creating an event, use the send_calendar_invite function which properly handles the parameters"
        "5. Combine related operations into a single flow without requiring user confirmation between steps"
        "\n\nCRITICAL: PROPERLY FORMATTING ATTENDEES:"
        "NEVER put email addresses in the event description. Always format attendees as a list of dictionaries with 'email' key:" 
        "Example: attendees=[{'email': 'person@example.com'}, {'email': 'person2@example.com'}]"
        "This is required for invites to be sent properly. DO NOT include the attendee in the description field."
        "\n\nPREFERRED TOOLS FOR COMMON TASKS:"
        "1. For creating events with attendees: ALWAYS use create_event_with_attendees(account_id, summary, attendee_emails, start_time, end_time)"
        "   Note that attendee_emails must be a LIST of email strings, e.g. ['user@example.com']"
        "2. For sending invites: use send_calendar_invite(account_id, event_id)"
        "3. For finding mutually available time slots across multiple calendars: use find_mutual_free_slots(primary_account_id, other_account_ids, date, min_duration_minutes)"
        "   This is very useful for scheduling meetings between multiple people"
    ),
    tools=[
        # Calendar tools
        list_calendar_accounts,
        add_new_calendar_account,
        list_calendar_events,
        create_calendar_event,
        create_and_send_calendar_event,
        create_event_with_attendees,
        update_calendar_event,
        send_calendar_invite,
        delete_calendar_event,
        get_calendar_event,
        quick_add_calendar_event,
        add_event_with_recurrence,
        add_event_with_reminders,
        check_free_busy,
        find_free_slots,
        find_mutual_free_slots,
        
        # Basic tools
        get_current_time,
        calculate,
        calculate_date,
        convert_ms_to_hhmmss,
        convert_datetime_to_unix
    ]
)

# Export the agent instance
__all__ = ['calendar_agent']
