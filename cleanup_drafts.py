import os
import json
from gmail_client import get_gmail_service

def delete_all_drafts():
    print("--- Deleting all drafts from Gmail accounts ---")
    
    tokens = ['token.json', 'token_work.json']
    
    for token in tokens:
        if not os.path.exists(token):
            continue
            
        print(f"\nProcessing account: {token}")
        service = get_gmail_service(token)
        if not service:
            print(f"Could not connect to service for {token}")
            continue
            
        try:
            results = service.users().drafts().list(userId='me').execute()
            drafts = results.get('drafts', [])
            
            if not drafts:
                print("No drafts found.")
                continue
                
            print(f"Found {len(drafts)} drafts. Deleting...")
            for draft in drafts:
                try:
                    service.users().drafts().delete(userId='me', id=draft['id']).execute()
                    print(f"Deleted draft: {draft['id']}")
                except Exception as e:
                    print(f"Error deleting draft {draft['id']}: {e}")
                    
            print(f"Finished deleting drafts for {token}")
            
        except Exception as e:
            print(f"Error listing drafts for {token}: {e}")

if __name__ == "__main__":
    delete_all_drafts()
