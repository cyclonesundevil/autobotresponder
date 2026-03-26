import os
import time
import base64
import asyncio
import json
import datetime
from dotenv import load_dotenv
from googleapiclient.errors import HttpError
from discord.ext import tasks

from gmail_client import get_gmail_service, get_body
from resume_processor import generate_tailored_resume_docx, is_recruiter_opportunity, extract_forward_to_email
from email_drafter import create_draft
from persistence_utils import get_state_path
import sms_manager

load_dotenv()

BASE_RESUME_PATH = os.getenv("BASE_RESUME_PATH")
PROCESSED_RECRUITERS_FILE = get_state_path("processed_recruiters.json")

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

def get_email_body_and_sender(service, msg_id):
    msg_data = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    headers = msg_data.get('payload', {}).get('headers', [])
    sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
    
    body = get_body(msg_data.get('payload', {}))
    return body, sender

# Global list of Gmail services for multi-account checking
_gmail_services = []

@tasks.loop(seconds=180)
async def gmail_check_task():
    """Background task that runs every 60 seconds inside the Discord Bot loop."""
    print("\n--- Checking for Gmail approvals ---")
    for service_entry in _gmail_services:
        sms_manager.check_for_email_approvals(service_entry['service'])

    print("--- Checking for recruiter emails ---")
    
    # Remote Control Check
    bot_state_file = get_state_path("bot_state.json")
    if os.path.exists(bot_state_file):
        with open(bot_state_file, "r") as f:
            state = json.load(f)
            if state.get("paused"):
                print("Bot is PAUSED via SMS. Skipping loop.")
                return

    # Date Filter: Only last 3 months
    three_months_ago = (datetime.datetime.now() - datetime.timedelta(days=90)).strftime("%Y/%m/%d")
    
    keywords = (
        '(hiring OR recruiter OR "job opportunity" OR opening OR role OR '
        'position OR engineer OR scientist OR developer OR interview OR interviewing)'
    )
    query = f'is:unread {keywords} after:{three_months_ago} -in:spam -in:trash'
    
    for service_entry in _gmail_services:
        service = service_entry['service']
        token_name = service_entry['token']
        print(f"Checking account: {token_name}...")
        
        try:
            results = service.users().messages().list(userId='me', q=query).execute()
            messages = results.get('messages', [])
            
            if messages:
                print(f"Found {len(messages)} unread potential recruiter emails.")
            else:
                print("No new recruiter emails found.")
                
            for msg in messages:
                msg_id = msg['id']
                print(f"Processing email {msg_id}...")
                
                body, sender = get_email_body_and_sender(service, msg_id)
                
                if not body:
                    print("Could not extract email body. Skipping.")
                    continue
                
                print(f"Checking if email from {sender} is a recruiter opportunity...")
                if not is_recruiter_opportunity(body):
                    print("Email classified as NOT a recruiter opportunity. Skipping.")
                    service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
                    continue

                print("Legitimate recruiter opportunity identified. Proceeding.")
                print("Checking for forward-to email address...")
                target_email = extract_forward_to_email(body, sender)

                # Check for own emails
                my_emails = ["cyclsun@gmail.com", "cyclonesundevil@gmail.com"]
                if any(email in target_email.lower() for email in my_emails):
                    print(f"-> Target email {target_email} is one of your own. Skipping draft creation.")
                    service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
                    continue

                if target_email != sender:
                    print(f"-> Found specific forward-to address: {target_email}")
                else:
                    print(f"-> Replying to sender: {target_email}")

                # No-reply check
                if "noreply" in target_email.lower() or "no-reply" in target_email.lower():
                    print(f"-> Target email {target_email} is a no-reply address. Skipping draft creation.")
                    service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
                    continue

                # De-duplication check
                processed_recruiters = _load_processed_recruiters()
                if target_email.lower() in [e.lower() for e in processed_recruiters]:
                    print(f"-> Already processed recruiter {target_email}. Skipping to avoid spam.")
                    service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
                    continue

                output_docx = f"tailored_resume_{msg_id}.docx"
                print("Generating tailored resume...")
                filepath = generate_tailored_resume_docx(body, BASE_RESUME_PATH, output_docx)
                
                if filepath:
                    print("Drafting reply...")
                    reply_body = (
                        "Hello,\n\n"
                        "Thank you for reaching out regarding this opportunity. "
                        "I have attached my tailored resume for your review. Let me know if you would like "
                        "to schedule a time to chat.\n\n"
                        "Best regards,\nJose C. Ramirez"
                    )
                    
                    draft = create_draft(service, target_email, "Re: Your message regarding the opportunity", reply_body, filepath)
                    
                    if draft:
                        pending_map = sms_manager._load_pending_approvals()
                        try:
                            next_id = max([int(k) for k in pending_map.keys() if k.isdigit()] + [0]) + 1
                        except:
                            next_id = 1
                        
                        short_id = str(next_id)
                        sms_manager.register_pending_draft(short_id, draft['id'], token_file=token_name)

                        print(f"Draft created successfully. Generating phrased alert for ID {short_id}...")
                        dynamic_body = sms_manager.get_dynamic_phrasing(sender, short_id)
                        
                        print(f"Sending dual notifications (Discord + SMS)...")
                        success = await sms_manager.send_dual_notification(
                            draft['id'], 
                            target_email, 
                            custom_body=dynamic_body,
                            file_path=filepath,
                            short_id=short_id
                        )
                        
                        if success:
                            print(f"Discord notification sent successfully (ID: {short_id}).")
                            _save_processed_recruiter(target_email)
                        else:
                            print("Discord notification failed. Check bot logs.")
                    else:
                        print("Failed to create draft.")
                    
                service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
                print(f"Finished processing {msg_id}.")

        except HttpError as e:
            if e.resp.status == 429:
                print(f"Gmail Rate Limit Exceeded for {token_name}: {e}. Bot will retry in next loop.")
            else:
                print(f"Gmail API Error for {token_name}: {e}")
        except Exception as e:
            print(f"Error processing account {token_name}: {e}")

@gmail_check_task.before_loop
async def before_gmail_check():
    """Wait for the bot to be ready before starting the Gmail loop."""
    await sms_manager.bot.wait_until_ready()

@sms_manager.bot.listen()
async def on_ready():
    """Starts the Gmail task only after the bot's event loop is running."""
    if not gmail_check_task.is_running():
        gmail_check_task.start()
        print("--- Gmail check task has started! ---")

def main():
    print("Starting Auto Recruiter Responder (Discord Bot Edition)...")
    
    # 1. Main Account
    s1 = get_gmail_service('token.json')
    if s1:
        _gmail_services.append({'service': s1, 'token': 'token.json'})
    
    # 2. Second Account (Work/Other)
    s2 = get_gmail_service('token_work.json')
    if s2:
        _gmail_services.append({'service': s2, 'token': 'token_work.json'})

    if not _gmail_services:
        print("Failed to start: Could not connect to any Gmail accounts.")
        return

    # Store first service as default for legacy compatibility
    sms_manager._gmail_service = _gmail_services[0]['service']

    # Run the Discord Bot
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token or "your_token" in token:
        print("CRITICAL: DISCORD_BOT_TOKEN not found in .env. Cannot start bot.")
        return

    try:
        sms_manager.bot.run(token)
    except Exception as e:
        print(f"Fatal error running Discord Bot: {e}")

if __name__ == "__main__":
    main()
