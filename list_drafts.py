from gmail_client import get_gmail_service

def list_drafts():
    service = get_gmail_service()
    if not service:
        print("Failed to get Gmail service.")
        return

    results = service.users().drafts().list(userId='me', maxResults=10).execute()
    drafts = results.get('drafts', [])
    
    print(f"Found {len(drafts)} drafts (showing top 10):")
    for d in drafts:
        draft_info = service.users().drafts().get(userId='me', id=d['id']).execute()
        msg = draft_info.get('message', {})
        headers = msg.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        to = next((h['value'] for h in headers if h['name'].lower() == 'to'), 'No To')
        
        print(f"  ID: {d['id']}")
        print(f"  To: {to}")
        print(f"  Subject: {subject}")
        print("-" * 20)

if __name__ == "__main__":
    list_drafts()
