import os
import datetime
from dotenv import load_dotenv
from gmail_client import get_gmail_service

load_dotenv()

def analyze_history():
    service = get_gmail_service()
    if not service:
        return

    email = "4802093709@tmomail.net"
    print(f"--- Detailed Analysis for {email} ---")
    
    results = service.users().messages().list(userId='me', q=f'to:{email}').execute()
    messages = results.get('messages', [])
    
    for msg in messages:
        m = service.users().messages().get(userId='me', id=msg['id']).execute()
        dt = datetime.datetime.fromtimestamp(int(m['internalDate'])/1000)
        snippet = m['snippet']
        
        # Check for matching bounce
        thread_id = m['threadId']
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
        has_bounce = any("failure" in m_in['snippet'].lower() or "not delivered" in m_in['snippet'].lower() for m_in in thread['messages'])
        
        status = "BOUNCED" if has_bounce else "LIKELY DELIVERED"
        print(f"[{dt}] Status: {status} | Snippet: {snippet}")

if __name__ == "__main__":
    analyze_history()
