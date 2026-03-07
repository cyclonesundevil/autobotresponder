from gmail_client import get_gmail_service, get_body
import json

def debug_approvals():
    service = get_gmail_service()
    if not service:
        print("Failed to get Gmail service.")
        return

    # Check with different queries
    queries = [
        '"YES"'
    ]

    for q in queries:
        print(f"\nSearching with query: {q}")
        results = service.users().messages().list(userId='me', q=q).execute()
        messages = results.get('messages', [])
        
        print(f"Found {len(messages)} unread messages.")
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            headers = msg_data.get('payload', {}).get('headers', [])
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
            body = get_body(msg_data.get('payload', {}))
            
            # Use same logic as sms_manager
            words = [w.strip() for w in body.split() if w.strip()]
            has_yes = "YES" in [w.upper() for w in words]
            
            if has_yes or "YES" in body.upper():
                print(f"  ID: {msg['id']}")
                print(f"  From: {sender}")
                print(f"  Words: {words[:10]}")
                print(f"  Is exact 'YES' match: {has_yes}")
                print("-" * 20)

if __name__ == "__main__":
    debug_approvals()
