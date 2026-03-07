import os
from dotenv import load_dotenv
from gmail_client import get_gmail_service

load_dotenv()

def check_recruiter_emails():
    service = get_gmail_service()
    if not service:
        print("Failed to get Gmail service.")
        return

    keywords = (
        '(hiring OR recruiter OR "job opportunity" OR opening OR role OR '
        'position OR engineer OR scientist OR developer OR interview OR interviewing)'
    )
    query = f'is:unread {keywords}'
    
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])
    
    if not messages:
        print("No unread recruitment emails found.")
        return
    
    print(f"Found {len(messages)} unread potential recruiter emails:")
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
        headers = msg_data.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
        print(f"- From: {sender}\n  Subject: {subject}\n  ID: {msg['id']}")

if __name__ == "__main__":
    check_recruiter_emails()
