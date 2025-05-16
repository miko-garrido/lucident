"""
Extract promises from text messages.

This module provides functionality to identify and extract promises or commitments
from text messages, emails, or transcripts.
"""

import logging
import re
from typing import Dict, Any, List
import datetime
from dateutil import parser

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_date_from_text(text: str) -> tuple:
    """
    Extract date information from text.
    
    Args:
        text: The text to analyze for date references
        
    Returns:
        A tuple containing (due_date, due_date_text) where:
        - due_date is the parsed date in ISO format or None
        - due_date_text is the original date text found
    """
    text_lower = text.lower()
    
    # Common time expressions
    time_patterns = {
        "today": datetime.datetime.now().date(),
        "tomorrow": (datetime.datetime.now() + datetime.timedelta(days=1)).date(),
        "next week": (datetime.datetime.now() + datetime.timedelta(days=7)).date(),
        "next month": (datetime.datetime.now() + datetime.timedelta(days=30)).date(),
        "tonight": datetime.datetime.now().date(),
        "this evening": datetime.datetime.now().date(),
        "this afternoon": datetime.datetime.now().date(),
        "this morning": datetime.datetime.now().date(),
        "end of day": datetime.datetime.now().date(),
        "eod": datetime.datetime.now().date(),
        "cob": datetime.datetime.now().date(),
    }
    
    # Check common time expressions
    for time_expr, date_value in time_patterns.items():
        if time_expr in text_lower:
            return date_value.isoformat(), time_expr
    
    # Days of the week
    days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for day in days_of_week:
        if day in text_lower or f"next {day}" in text_lower:
            # We found a day reference, but don't have context for which specific date
            # Just return the day name for now
            day_text = f"next {day}" if f"next {day}" in text_lower else day
            return None, day_text
    
    # Look for specific date patterns (MM/DD/YYYY, etc.)
    date_patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # MM/DD/YYYY or DD/MM/YYYY
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',    # YYYY-MM-DD
    ]
    
    for pattern in date_patterns:
        date_match = re.search(pattern, text)
        if date_match:
            date_text = date_match.group(1)
            try:
                # Try to parse the date
                parsed_date = parser.parse(date_text)
                return parsed_date.date().isoformat(), date_text
            except (ValueError, parser.ParserError):
                # If parsing fails, just return the text
                return None, date_text
    
    # Look for month and day
    month_pattern = r'(?:on|by|before|after)\s+(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?'
    month_match = re.search(month_pattern, text_lower)
    if month_match:
        try:
            month_name = month_match.group(1)
            day_num = month_match.group(2)
            date_text = f"{month_name} {day_num}"
            
            # Try to parse a date like "October 15"
            current_year = datetime.datetime.now().year
            date_str = f"{month_name} {day_num}, {current_year}"
            
            try:
                parsed_date = parser.parse(date_str)
                # If the date is in the past, assume it's next year
                if parsed_date.date() < datetime.datetime.now().date():
                    parsed_date = parser.parse(f"{month_name} {day_num}, {current_year + 1}")
                return parsed_date.date().isoformat(), date_text
            except (ValueError, parser.ParserError):
                return None, date_text
        except:
            # If there's any error in parsing, just continue
            pass
    
    # No date found
    return None, None

def extract_promises_from_text(text: str, include_third_party: bool = False) -> Dict[str, Any]:
    """
    Extract promises or commitments from text.
    
    A "promise" is defined as a statement where the speaker commits to a future action.
    Examples: "I'll update you tomorrow", "I will follow up next week", etc.
    
    Args:
        text: The text to analyze for promises
        include_third_party: Whether to include promises made by others (default: False)
        
    Returns:
        A dictionary containing:
        - 'success': Boolean indicating if the operation succeeded
        - 'promises': List of extracted promises with action, due_date, context, and original_text
        - 'error': Error message if unsuccessful
    """
    try:
        # Initialize empty results
        promises = []
        
        # Split text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Common first-person promise patterns
        first_person_patterns = [
            # I'll/I will pattern
            r"(I['']ll|I\s+will)\s+([^,.!?;]+)",
            # Let me pattern
            r"(Let\s+me)\s+([^,.!?;]+)",
            # Going to/Gonna pattern
            r"(I['']m\s+going\s+to|I['']m\s+gonna)\s+([^,.!?;]+)",
            # I can pattern (when indicating future action)
            r"(I\s+can)\s+([^,.!?;]+)\s+for\s+you",
            # I promise pattern
            r"(I\s+promise\s+to)\s+([^,.!?;]+)",
            # We'll/We will pattern
            r"(We['']ll|We\s+will)\s+([^,.!?;]+)",
            # We're planning/We are planning
            r"(We['']re\s+planning\s+to|We\s+are\s+planning\s+to)\s+([^,.!?;]+)",
        ]
        
        # Third-party promise patterns (if include_third_party is True)
        third_party_patterns = [
            # Name + will pattern
            r"(\w+)\s+(mentioned|said|noted|promised)\s+(he|she|they|[\w-]+)\s+(will|['']ll|is\s+going\s+to)\s+([^,.!?;]+)",
            # Name + is going to pattern
            r"(\w+)\s+is\s+going\s+to\s+([^,.!?;]+)",
        ]
        
        # Check each sentence for promises
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Look for first-person promise patterns
            found_promise = False
            
            for pattern in first_person_patterns:
                matches = re.search(pattern, sentence, re.IGNORECASE)
                if matches:
                    found_promise = True
                    
                    # Extract the action (what is promised)
                    action_prefix = matches.group(1)  # "I'll", "Let me", etc.
                    action_text = matches.group(2)  # The rest of the promise
                    
                    # Full action text
                    action = f"{action_prefix} {action_text}".strip()
                    
                    # Extract due date if mentioned
                    due_date, due_date_text = extract_date_from_text(sentence)
                    
                    # Add the promise to results
                    promises.append({
                        "action": action,
                        "due_date": due_date,
                        "due_date_text": due_date_text,
                        "context": sentence,
                        "original_text": sentence,
                        "is_third_party": False
                    })
                    
                    break  # No need to check other patterns for this sentence
            
            # If no first-person matches and third-party is enabled, check for third-party promises
            if not found_promise and include_third_party:
                for pattern in third_party_patterns:
                    matches = re.search(pattern, sentence, re.IGNORECASE)
                    if matches:
                        found_promise = True
                        
                        # For the first pattern (Name mentioned...)
                        if len(matches.groups()) >= 5:
                            person = matches.group(1)  # The person's name
                            verb = matches.group(2)    # mentioned/said/etc.
                            pronoun = matches.group(3) # he/she/they
                            will_word = matches.group(4) # will/'ll/is going to
                            action_text = matches.group(5) # The action
                            
                            # Full action text
                            action = f"{person} {verb} {pronoun} {will_word} {action_text}".strip()
                        else:
                            # For the second pattern (Name is going to...)
                            person = matches.group(1)  # The person's name
                            action_text = matches.group(2) # The action
                            
                            # Full action text
                            action = f"{person} is going to {action_text}".strip()
                        
                        # Extract due date if mentioned
                        due_date, due_date_text = extract_date_from_text(sentence)
                        
                        # Add the promise to results
                        promises.append({
                            "action": action,
                            "due_date": due_date,
                            "due_date_text": due_date_text,
                            "context": sentence,
                            "original_text": sentence,
                            "is_third_party": True,
                            "person": person
                        })
                        
                        break  # No need to check other patterns for this sentence
            
            # If no matches from explicit patterns, look for less obvious commitments
            if not found_promise and any(kw in sentence.lower() for kw in ["follow up", "get back to", "update", "send", "complete", "finish"]):
                if any(pronoun in sentence.lower() for pronoun in ["i ", "i'll", "i'm", "we ", "we'll", "we're"]):
                    # This might be a promise expressed in a less structured way
                    
                    # Try to extract the action
                    action = sentence
                    
                    # Extract due date if mentioned
                    due_date, due_date_text = extract_date_from_text(sentence)
                    
                    # Add the promise to results
                    promises.append({
                        "action": action,
                        "due_date": due_date,
                        "due_date_text": due_date_text,
                        "context": sentence,
                        "original_text": sentence,
                        "is_third_party": False
                    })
        
        return {
            "success": True,
            "promises": promises
        }
    except Exception as e:
        logger.error(f"Error extracting promises: {e}")
        return {
            "success": False,
            "error": f"Error extracting promises: {str(e)}"
        }

def extract_promises_from_slack_history(channel: str, limit: int = 100, include_third_party: bool = False) -> Dict[str, Any]:
    """
    Extract promises from a Slack channel history.
    
    Args:
        channel: The channel name or ID to get promises from
        limit: The maximum number of messages to retrieve (default: 100)
        include_third_party: Whether to include promises made by others (default: False)
        
    Returns:
        A dictionary containing:
        - 'success': Boolean indicating if the operation succeeded
        - 'promises': List of extracted promises with additional message metadata
        - 'error': Error message if unsuccessful
    """
    from .message_tools import get_slack_channel_history
    
    try:
        # First get the channel history
        channel_history = get_slack_channel_history(channel, limit)
        
        if not channel_history.get("success", False):
            return {
                "success": False,
                "error": f"Invalid channel history: {channel_history.get('error', 'Unknown error')}"
            }
        
        # Extract messages
        raw_messages = channel_history.get("raw_messages", [])
        all_promises = []
        
        # Process each message
        for msg in raw_messages:
            text = msg.get("text", "")
            
            # Skip empty messages
            if not text:
                continue
            
            # Extract promises from this message
            result = extract_promises_from_text(text, include_third_party)
            
            if result.get("success", False) and result.get("promises", []):
                promises = result["promises"]
                
                # Add message metadata to each promise
                for promise in promises:
                    promise["message_ts"] = msg.get("ts")
                    promise["message_link"] = msg.get("link")
                    promise["user"] = msg.get("user")
                    promise["channel"] = channel_history.get("channel")
                    promise["channel_name"] = channel_history.get("channel_name")
                
                all_promises.extend(promises)
        
        return {
            "success": True,
            "promises": all_promises,
            "channel": channel_history.get("channel"),
            "channel_name": channel_history.get("channel_name")
        }
    except Exception as e:
        logger.error(f"Error extracting promises from Slack history: {e}")
        return {
            "success": False,
            "error": f"Error extracting promises from Slack history: {str(e)}"
        } 