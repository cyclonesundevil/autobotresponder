import os
from dotenv import load_dotenv
from gmail_client import get_gmail_service, get_body
from resume_processor import is_recruiter_opportunity

load_dotenv()

def test_specific_email(msg_id):
    service = get_gmail_service()
    if not service:
        print("Failed to get Gmail service.")
        return

    print(f"Fetching email {msg_id}...")
    msg_data = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    body = get_body(msg_data.get('payload', {}))
    
    print("\n--- Email Body Snippet ---")
    print(body[:500] + "...")
    
    print("\nRunning is_recruiter_opportunity...")
    result = is_recruiter_opportunity(body)
    print(f"Result: {result}")

if __name__ == "__main__":
    test_specific_email("19c7d2b29cc123d7")
