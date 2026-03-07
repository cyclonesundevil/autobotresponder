import os
from dotenv import load_dotenv
from gmail_client import get_gmail_service

load_dotenv()

def check_sent_and_bounces():
    service = get_gmail_service()
    if not service:
        print("Failed to get Gmail service.")
        return

    print("--- Checking Sent Messages ---")
    for email in ["4802093709@tmomail.net", "4802316231@txt.att.net"]:
        print(f"\nRecipient: {email}")
        query = f'to:{email}'
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        
        if not messages:
            print("  No messages found in Sent folder.")
        else:
            print(f"  Found {len(messages)} messages sent.")
            last_msg = service.users().messages().get(userId='me', id=messages[0]['id'], format='minimal').execute()
            print(f"  Latest Snippet: {last_msg['snippet']}")

    print("\n--- Checking for Bounces/Failures in Inbox ---")
    for email in ["4802093709@tmomail.net", "4802316231@txt.att.net"]:
        print(f"\nRecipient: {email}")
        bounce_query = f'"{email}" ("failure" OR "rejected" OR "undelIVERABLE" OR "not delivered" OR "error")'
        results_bounce = service.users().messages().list(userId='me', q=bounce_query).execute()
        bounces = results_bounce.get('messages', [])
        
        if not bounces:
            print("  No bounce notifications found.")
        else:
            print(f"  Found {len(bounces)} potential bounce notifications.")
            for msg in bounces:
                m = service.users().messages().get(userId='me', id=msg['id']).execute()
                import datetime
                dt = datetime.datetime.fromtimestamp(int(m['internalDate'])/1000)
                print(f"  [{dt}] Snippet: {m['snippet']}")

if __name__ == "__main__":
    check_sent_and_bounces()
