import os
from dotenv import load_dotenv
from gmail_client import get_gmail_service

load_dotenv()

def list_recent_unread():
    service = get_gmail_service()
    if not service:
        print("Failed to get Gmail service.")
        return

    # Broad search for all unread emails to see what's actually there
    query = 'is:unread'
    results = service.users().messages().list(userId='me', q=query, maxResults=10).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No unread messages found.")
        return

    print(f"Found {len(messages)} unread messages. Analyzing headers:")
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
        headers = msg_data.get('payload', {}).get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
        
        print(f"\nID: {msg['id']}")
        print(f"From: {sender}")
        print(f"Subject: {subject}")

if __name__ == "__main__":
    list_recent_unread()
