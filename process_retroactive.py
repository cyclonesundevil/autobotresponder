import os
import json
import asyncio
import datetime
from dotenv import load_dotenv

from gmail_client import get_gmail_service
from main import get_email_body_and_sender
from resume_processor import generate_tailored_resume_docx, is_recruiter_opportunity, extract_forward_to_email
from email_drafter import create_draft
import sms_manager

load_dotenv()
BASE_RESUME_PATH = os.getenv("BASE_RESUME_PATH")

PROCESSED_RECRUITERS_FILE = "processed_recruiters.json"

def _load_processed_recruiters():
    if os.path.exists(PROCESSED_RECRUITERS_FILE):
        try:
            with open(PROCESSED_RECRUITERS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def _save_processed_recruiter(email):
    processed = _load_processed_recruiters()
    if email.lower() not in [e.lower() for e in processed]:
        processed.append(email.lower())
        with open(PROCESSED_RECRUITERS_FILE, 'w') as f:
            json.dump(processed, f, indent=4)

async def process_retroactive_emails():
    print("--- Starting Retroactive Email Processing ---")
    
    # Setup Services
    _gmail_services = []
    s1 = get_gmail_service('token.json')
    if s1: _gmail_services.append({'service': s1, 'token': 'token.json'})
    s2 = get_gmail_service('token_work.json')
    if s2: _gmail_services.append({'service': s2, 'token': 'token_work.json'})

    if not _gmail_services:
        print("Could not connect to Gmail.")
        return

    sms_manager._gmail_service = _gmail_services[0]['service']

    # We need the bot to be 'logged in' so we can send discord messages
    # But we don't want to start the whole event loop forever. 
    # We will log it in just to send the messages.
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token or "your_token" in token:
        print("CRITICAL: DISCORD_BOT_TOKEN not found.")
        return
        
    await sms_manager.bot.login(token)
    
    # Look back 30 days
    one_month_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y/%m/%d")
    
    # Same keywords as main.py, but NO is:unread constraint
    keywords = (
        '(hiring OR recruiter OR "job opportunity" OR opening OR role OR '
        'position OR engineer OR scientist OR developer OR interview OR interviewing)'
    )
    query = f'{keywords} after:{one_month_ago} -in:spam -in:trash'

    for service_entry in _gmail_services:
        service = service_entry['service']
        token_name = service_entry['token']
        print(f"\nChecking account: {token_name} with query: {query}")
        
        try:
            results = service.users().messages().list(userId='me', q=query).execute()
            messages = results.get('messages', [])
            
            if not messages:
                print("No emails found matching query in this account.")
                continue
                
            print(f"Found {len(messages)} total emails matching keywords from the last 30 days.")
            
            for msg in messages:
                msg_id = msg['id']
                print(f"\nEvaluating email {msg_id}...")
                
                msg_data = service.users().messages().get(userId='me', id=msg_id, format='metadata', metadataHeaders=[]).execute()
                labels = msg_data.get('labelIds', [])
                if 'SPAM' in labels or 'TRASH' in labels:
                    print(f"- Email {msg_id} is in SPAM or TRASH. Skipping.")
                    continue

                body, sender = get_email_body_and_sender(service, msg_id)
                if not body:
                    print("- Could not extract email body. Skipping.")
                    continue
                
                if not is_recruiter_opportunity(body):
                    print("- Email classified as NOT a recruiter opportunity. Skipping.")
                    continue

                print("- Legitimate recruiter opportunity identified. Proceeding.")
                target_email = extract_forward_to_email(body, sender)
                
                # Check for own emails
                my_emails = ["cyclsun@gmail.com", "cyclonesundevil@gmail.com"]
                if any(email in target_email.lower() for email in my_emails):
                    print(f"- Target email {target_email} is one of your own. Skipping draft creation to avoid loops.")
                    continue

                if target_email != sender:
                    print(f"- Found specific forward-to address: {target_email}")
                else:
                    print(f"- Replying to sender: {target_email}")

                # De-duplication check
                processed_recruiters = _load_processed_recruiters()
                if target_email.lower() in [e.lower() for e in processed_recruiters]:
                    print(f"- Already processed recruiter {target_email}. Skipping to avoid spam.")
                    continue

                output_docx = f"tailored_resume_{msg_id}.docx"
                print("- Generating AI-focused tailored resume...")
                filepath = generate_tailored_resume_docx(body, BASE_RESUME_PATH, output_docx)
                
                if filepath:
                    print("- Drafting reply...")
                    reply_body = (
                        "Hello,\n\n"
                        "Thank you for reaching out regarding this opportunity. "
                        "I have attached my tailored resume emphasizing my AI engineering experience for your review. Let me know if you would like "
                        "to schedule a time to chat.\n\n"
                        "Best regards,\nJose C. Ramirez"
                    )
                    
                    draft = create_draft(service, target_email, "Re: Your message regarding the opportunity", reply_body, filepath)
                    
                    if draft:
                        pending_map = sms_manager._load_pending_approvals()
                        next_id = max([int(k) for k in pending_map.keys() if k.isdigit()] + [0]) + 1
                        short_id = str(next_id)
                        
                        sms_manager.register_pending_draft(short_id, draft['id'], token_file=token_name)
                        dynamic_body = sms_manager.get_dynamic_phrasing(sender, short_id)
                        
                        print("- Sending dual notifications (Discord + SMS)...")
                        success = await sms_manager.send_dual_notification(
                            draft['id'], 
                            target_email, 
                            custom_body=dynamic_body,
                            file_path=filepath,
                            short_id=short_id
                        )
                        if success:
                            print(f"- Discord notification sent (ID: {short_id}).")
                            _save_processed_recruiter(target_email)
                        else:
                            print("- Discord notification failed.")
                    else:
                        print("- Failed to create draft.")

        except Exception as e:
            print(f"Error processing account {token_name}: {e}")

    await sms_manager.bot.close()
    print("\n--- Finished Retroactive Email Processing ---")

if __name__ == "__main__":
    asyncio.run(process_retroactive_emails())
