import os
import json
import datetime
import time
from twilio.rest import Client as TwilioClient
from dotenv import load_dotenv
from gmail_client import get_gmail_service
import sms_manager

load_dotenv()

BOT_STATE_FILE = "bot_state.json"
AGENT_NOTES_FILE = "agent_notes.txt"
SENT_NOTIFICATIONS_FILE = "sent_notifications.json"
ACTIVITY_LOG_FILE = "activity_log.txt"
PROCESSED_MESSAGES_FILE = "processed_messages.json"

# Global Gmail service for sending approvals
_gmail_service = None

def _load_state():
    if os.path.exists(BOT_STATE_FILE):
        with open(BOT_STATE_FILE, "r") as f:
            return json.load(f)
    return {"paused": False}

def _save_state(state):
    state["last_update"] = datetime.datetime.now().isoformat()
    with open(BOT_STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def _log_activity(msg):
    with open(ACTIVITY_LOG_FILE, "a") as f:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {msg}\n")

def _load_processed_messages():
    if os.path.exists(PROCESSED_MESSAGES_FILE):
        try:
            with open(PROCESSED_MESSAGES_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def _save_processed_messages(processed_ids):
    with open(PROCESSED_MESSAGES_FILE, "w") as f:
        json.dump(list(processed_ids), f, indent=4)

def process_command(body, from_number):
    """Processes a single command and returns the reply text."""
    # Security check
    target_phone = os.getenv("SMS_TARGET_PHONE")
    clean_target = "".join(filter(str.isdigit, target_phone)) if target_phone else ""
    clean_from = "".join(filter(str.isdigit, from_number))
    
    if not clean_target or not (clean_from.endswith(clean_target) or clean_target.endswith(clean_from)):
        print(f"[Security] Unauthorized SMS from {from_number}: {body}")
        return "System error: Unauthorized sender."

    print(f"[Authorized] User {from_number} sent: {body}")
    cmd = body.strip().upper()
    
    if cmd == "STATUS":
        state = _load_state()
        status_str = "PAUSED" if state.get("paused") else "RUNNING"
        lead_count = 0
        if os.path.exists(SENT_NOTIFICATIONS_FILE):
            with open(SENT_NOTIFICATIONS_FILE, "r") as f:
                lead_count = len(json.load(f))
        _log_activity(f"Command: STATUS | Result: {status_str}, {lead_count} leads")
        return f"Bot Status: {status_str}\nTotal Leads: {lead_count}"

    elif cmd == "PAUSE":
        state = _load_state()
        state["paused"] = True
        _save_state(state)
        _log_activity("Command: PAUSE | Result: Bot Paused")
        return "Bot has been PAUSED."

    elif cmd == "RESUME":
        state = _load_state()
        state["paused"] = False
        _save_state(state)
        _log_activity("Command: RESUME | Result: Bot Resumed")
        return "Bot has been RESUMED."

    elif cmd.startswith("YES"):
        global _gmail_service
        if not _gmail_service:
            _gmail_service = get_gmail_service()
        
        words = body.split()
        pending_map = sms_manager._load_pending_approvals()
        target_data = None

        if len(words) > 1:
            val = words[1]
            if val in pending_map:
                target_data = pending_map[val]
            else:
                _log_activity(f"Command: {body} | Result: ID {val} not found")
                return f"Could not find a pending draft for ID: {val}"
        else:
            # Plain "YES" - find the most recent short ID
            if pending_map:
                try:
                    last_key = sorted(pending_map.keys(), key=lambda x: int(x) if x.isdigit() else 0)[-1]
                    target_data = pending_map[last_key]
                except:
                    last_key = list(pending_map.keys())[-1]
                    target_data = pending_map[last_key]
            else:
                _log_activity(f"Command: {body} | Result: No pending drafts")
                return "No pending drafts found to approve."

        if target_data:
            # Compatibility check
            if isinstance(target_data, str):
                target_draft_id = target_data
                service = _gmail_service
            else:
                target_draft_id = target_data.get("draft_id")
                token_file = target_data.get("token", "token.json")
                service = sms_manager._get_service_for_token(token_file)

            try:
                print(f"Sending approved draft {target_draft_id}...")
                service.users().drafts().send(userId='me', body={'id': target_draft_id}).execute()
                _log_activity(f"Command: {body} | Result: Sent draft {target_draft_id}")
                return f"Sent! Draft {target_draft_id[:8]}... has been sent."
            except Exception as e:
                print(f"Failed to send draft {target_draft_id}: {e}")
                _log_activity(f"Command: {body} | Result: Error {e}")
                return f"Failed to send draft: {e}"

    elif cmd.startswith("NOTE "):
        note = body[5:].strip()
        with open(AGENT_NOTES_FILE, "a") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {note}\n")
        return "Note saved for Antigravity."

    else:
        with open(AGENT_NOTES_FILE, "a") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {body}\n")
        return "Message saved as a note for Antigravity."

def run_polling():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
    
    if not all([account_sid, auth_token, twilio_number]):
        print("Missing Twilio credentials in .env")
        return

    client = TwilioClient(account_sid, auth_token)
    processed_ids = _load_processed_messages()
    
    # On first run, we record existing message SIDs to avoid processing history
    print("Initializing Command Center (Polling Model)...")
    try:
        initial_messages = client.messages.list(to=twilio_number, limit=20)
        for m in initial_messages:
            processed_ids.add(m.sid)
        _save_processed_messages(processed_ids)
        print("Listening for incoming SMS commands... (No Ngrok required!)")
    except Exception as e:
        print(f"Error checking Twilio messages: {e}")
        return

    while True:
        try:
            # Check for messages sent TO our Twilio number
            messages = client.messages.list(to=twilio_number, limit=5)
            
            for msg in reversed(messages): # Process oldest first
                if msg.sid not in processed_ids:
                    print(f"\n[Incoming SMS] From: {msg.from_} | Body: {msg.body}")
                    
                    # Process the command
                    reply_text = process_command(msg.body, msg.from_)
                    
                    # Send reply back via Twilio
                    if reply_text:
                        client.messages.create(
                            body=reply_text,
                            from_=twilio_number,
                            to=msg.from_
                        )
                        print(f"[Reply Sent] {reply_text}")
                    
                    # Mark as processed
                    processed_ids.add(msg.sid)
                    _save_processed_messages(processed_ids)
            
        except Exception as e:
            print(f"Error in polling loop: {e}")
            
        time.sleep(5) # Poll every 5 seconds

if __name__ == "__main__":
    _gmail_service = get_gmail_service()
    run_polling()
