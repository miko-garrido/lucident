#!/usr/bin/env python3
"""
Test script for promise extraction functionality.
This script demonstrates the promise extraction feature.
"""

from lucident_agent.tools.slack_tools import extract_promises_from_text
import json

# Test data - various sentences with and without promises
test_data = [
    "I'll update you on the status tomorrow.",
    "Can you send me that report?",  # Not a promise
    "Let me get back to you next week with more information.",
    "I'm going to review the document by end of day.",
    "We will fix this bug by next Friday.",
    "The meeting is scheduled for 3 PM.",  # Not a promise
    "I promise to deliver the feature by the end of the sprint.",
    "I can handle this task for you by tomorrow.",
    "Let's discuss this further in our next meeting.",  # Not a clear promise
    "I will follow up once I have more information.",
    "I'm planning to send this by 03/21/2024."
]

print("=== STANDARD PROMISE EXTRACTION ===")
# Run the tests
for i, text in enumerate(test_data):
    print(f"\nTest {i+1}: {text}")
    result = extract_promises_from_text(text)
    
    if result.get("success", False):
        promises = result.get("promises", [])
        if promises:
            print(f"✅ Found {len(promises)} promise(s):")
            for j, promise in enumerate(promises):
                print(f"  Promise {j+1}:")
                print(f"  - Action: {promise.get('action')}")
                print(f"  - Due date: {promise.get('due_date_text') or 'Not specified'}")
                print(f"  - Original text: {promise.get('original_text')}")
        else:
            print("❌ No promises found")
    else:
        print(f"❌ Error: {result.get('error')}")

# Test with a more complex paragraph
complex_text = """
Hi everyone,

Thanks for joining the meeting yesterday. I'll send out the meeting notes by end of day today.
Let me get back to you next week with the updated project timeline.
John mentioned he will prepare the budget report by Friday, and Sarah is going to review the marketing materials tomorrow.
We're planning to launch the feature on November 15th. I'll make sure to follow up once we have more information.

Best regards,
Alex
"""

print("\n\n=== COMPLEX TEXT TEST (WITHOUT THIRD-PARTY PROMISES) ===")
print(complex_text)
print("\nResults:")
result = extract_promises_from_text(complex_text)

if result.get("success", False):
    promises = result.get("promises", [])
    if promises:
        print(f"✅ Found {len(promises)} promise(s):")
        for j, promise in enumerate(promises):
            print(f"\nPromise {j+1}:")
            print(f"- Action: {promise.get('action')}")
            print(f"- Due date: {promise.get('due_date_text') or 'Not specified'}")
            print(f"- Original text: {promise.get('original_text')}")
    else:
        print("❌ No promises found")
else:
    print(f"❌ Error: {result.get('error')}")
    
print("\n\n=== COMPLEX TEXT TEST (WITH THIRD-PARTY PROMISES) ===")
print(complex_text)
print("\nResults:")
result = extract_promises_from_text(complex_text, include_third_party=True)

if result.get("success", False):
    promises = result.get("promises", [])
    if promises:
        print(f"✅ Found {len(promises)} promise(s):")
        for j, promise in enumerate(promises):
            third_party = promise.get("is_third_party", False)
            person = promise.get("person", "Unknown") if third_party else "Self"
            
            print(f"\nPromise {j+1}:")
            print(f"- Action: {promise.get('action')}")
            print(f"- Due date: {promise.get('due_date_text') or 'Not specified'}")
            print(f"- From: {person} (Third-party: {third_party})")
            print(f"- Original text: {promise.get('original_text')}")
    else:
        print("❌ No promises found")
else:
    print(f"❌ Error: {result.get('error')}") 