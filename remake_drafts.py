import os
import json
from gmail_client import get_gmail_service, get_body
from resume_processor import generate_tailored_resume_docx
from email_drafter import create_draft
import sms_manager

def remake_all_drafts():
    service = get_gmail_service()
    if not service:
        print("Failed to get Gmail service.")
        return

    pending_map = sms_manager._load_pending_approvals()
    if not pending_map:
        print("No pending approvals found.")
        return

    print(f"Starting batch update for {len(pending_map)} drafts...")
    new_map = {}

    for short_id, draft_id in list(pending_map.items()):
        try:
            print(f"\nProcessing Short ID {short_id} (Draft {draft_id})...")
            
            # 1. Get current draft info
            try:
                draft_info = service.users().drafts().get(userId='me', id=draft_id).execute()
            except Exception as e:
                print(f"  Error fetching draft {draft_id}: {e}. Skipping.")
                continue

            msg = draft_info.get('message', {})
            payload = msg.get('payload', {})
            headers = payload.get('headers', [])
            
            # Find the msg_id from attachment filename
            msg_id = None
            for part in payload.get('parts', []):
                filename = part.get('filename')
                if filename and filename.startswith("tailored_resume_") and filename.endswith(".docx"):
                    msg_id = filename.replace("tailored_resume_", "").replace(".docx", "")
                    break
            
            if not msg_id:
                print(f"  Could not find msg_id in attachment for draft {draft_id}. Skipping.")
                new_map[short_id] = draft_id
                continue

            # Fetch the original recruiter message to get body and sender
            try:
                recruiter_msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
                recruiter_body = get_body(recruiter_msg.get('payload', {}))
                
                t_headers = recruiter_msg.get('payload', {}).get('headers', [])
                recruiter_email = next((h['value'] for h in t_headers if h['name'].lower() == 'from'), None)
            except Exception as e:
                print(f"  Error fetching original message {msg_id}: {e}. Skipping.")
                new_map[short_id] = draft_id
                continue

            if not recruiter_body or not recruiter_email:
                print(f"  Incomplete message data for {msg_id}. Skipping.")
                new_map[short_id] = draft_id
                continue

            # 2. Regenerate resume
            output_docx = f"tailored_resume_{msg_id}.docx"
            print(f"  Regenerating resume for {recruiter_email}...")
            filepath = generate_tailored_resume_docx(recruiter_body, os.getenv("BASE_RESUME_PATH"), output_docx)
            
            if not filepath:
                print(f"  Failed to regenerate resume for {short_id}. Keeping original.")
                new_map[short_id] = draft_id
                continue

            # 3. Create new draft
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), "Re: Your message")
            body = (
                "Hello,\n\n"
                "Thank you for reaching out regarding this opportunity. "
                "I have attached my tailored resume for your review. Let me know if you would like "
                "to schedule a time to chat.\n\n"
                "Best regards,\nJose C. Ramirez"
            )
            
            print("  Creating replacement draft...")
            new_draft = create_draft(service, recruiter_email, subject, body, filepath)
            
            if new_draft:
                # 4. Delete old draft
                service.users().drafts().delete(userId='me', id=draft_id).execute()
                print(f"  Success! Replaced {draft_id} with {new_draft['id']}")
                new_map[short_id] = new_draft['id']
            else:
                new_map[short_id] = draft_id

        except Exception as e:
            print(f"  Fatal error processing {short_id}: {e}")
            new_map[short_id] = draft_id

    # Save the updated map
    sms_manager._save_pending_approvals(new_map)
    print("\nBatch update complete.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    remake_all_drafts()
