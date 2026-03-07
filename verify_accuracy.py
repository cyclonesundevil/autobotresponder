import os
import re
from dotenv import load_dotenv
from gmail_client import get_gmail_service, get_body
from resume_processor import is_recruiter_opportunity

load_dotenv()

def verify_new_accuracy():
    service = get_gmail_service()
    if not service:
        print("Failed to get Gmail service.")
        return

    print("--- Testing NEW Search Query ---")
    keywords = (
        '(hiring OR recruiter OR "job opportunity" OR opening OR role OR '
        'position OR engineer OR scientist OR developer OR interview OR interviewing)'
    )
    query = f'is:unread {keywords}'
    print(f"Query: {query}")
    
    results = service.users().messages().list(userId='me', q=query, maxResults=5).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No matches found with the new query.")
        return

    print(f"Found {len(messages)} potential matches. Classifying...\n")
    for msg in messages:
        msg_id = msg['id']
        msg_data = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        headers = msg_data.get('payload', {}).get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
        body = get_body(msg_data.get('payload', {}))

        print(f"[{msg_id}] From: {sender} | Subject: {subject}")
        is_match = is_recruiter_opportunity(body)
        print(f"   -> AI Classification: {'RECRUITER' if is_match else 'JUNK'}")
        print("-" * 20)

if __name__ == "__main__":
    verify_new_accuracy()
