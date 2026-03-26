import os
import re
import json
import discord
import requests
from twilio.rest import Client as TwilioClient
from discord.ext import commands, tasks
from dotenv import load_dotenv
from google import genai
from gmail_client import get_body
from persistence_utils import get_state_path

load_dotenv()

# Gemini setup
MODEL_ID = 'gemini-2.5-flash-lite'
PENDING_APPROVALS_FILE = get_state_path("pending_approvals.json")
SENT_NOTIFICATIONS_FILE = get_state_path("sent_notifications.json")

# Discord Setup
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Global reference to the gmail service so the bot can send emails
_gmail_service = None

def _get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)
    return None

def _load_pending_approvals():
    if os.path.exists(PENDING_APPROVALS_FILE):
        try:
            with open(PENDING_APPROVALS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def _save_pending_approvals(data):
    with open(PENDING_APPROVALS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def register_pending_draft(short_id, draft_id, token_file="token.json"):
    data = _load_pending_approvals()
    data[str(short_id)] = {
        "draft_id": draft_id,
        "token": token_file
    }
    _save_pending_approvals(data)

def _get_service_for_token(token_file):
    """Helper to get a Gmail service for a specific token file."""
    # We can't easily cache these without complex logic, 
    # so we'll rely on the main script to pass the correct service 
    # or re-initialize if needed.
    from gmail_client import get_gmail_service
    return get_gmail_service(token_file)

def _is_already_sent(draft_id, channel="sms", recipient=None):
    """Checks if a notification for this draft has already been sent to a specific channel/recipient."""
    if not os.path.exists(SENT_NOTIFICATIONS_FILE):
        return False
    try:
        with open(SENT_NOTIFICATIONS_FILE, 'r') as f:
            data = json.load(f)
            key = f"{channel}_{recipient}" if recipient else channel
            is_sent = data.get(draft_id, {}).get(key, False)
            if is_sent:
                print(f"[Sentinel] Already sent: {draft_id} | {key}")
            return is_sent
    except Exception as e:
        print(f"[Sentinel] Error reading registry: {e}")
        return False

def _mark_as_sent(draft_id, channel="sms", recipient=None):
    """Marks a notification as sent in the registry."""
    data = {}
    if os.path.exists(SENT_NOTIFICATIONS_FILE):
        try:
            with open(SENT_NOTIFICATIONS_FILE, 'r') as f:
                data = json.load(f)
        except:
            pass
    
    if draft_id not in data:
        data[draft_id] = {}
    
    key = f"{channel}_{recipient}" if recipient else channel
    data[draft_id][key] = True
    print(f"[Sentinel] Marking as sent: {draft_id} | {key}")
    
    with open(SENT_NOTIFICATIONS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_dynamic_phrasing(company_name, short_id):
    """Uses Gemini to generate a natural, varied notification."""
    gemini_client = _get_gemini_client()
    instruction = f"Reply YES {short_id} to send."
    
    if not gemini_client:
        return f"Draft ready for {company_name}. {instruction}"

    prompt = f"""
    Write a short, natural-sounding notification (1 sentence) for a user.
    The goal is to inform them that a recruitment email draft for '{company_name}' is ready for approval.
    Include the exact instruction: "{instruction}"
    Vary the phrasing so it doesn't look like a template. Be conversational but concise.
    """
    try:
        response = gemini_client.models.generate_content(model=MODEL_ID, contents=prompt).text.strip()
        if f"YES {short_id}" not in response.upper():
            response += f" {instruction}"
        return response
    except Exception as e:
        print(f"Error generating dynamic phrasing: {e}")
        return f"Draft ready for {company_name}. {instruction}"

async def send_discord_notification(draft_id, company_name, custom_body=None, file_path=None, short_id=None):
    """Sends a notification via Discord (Bot or Webhook fallback)."""
    if _is_already_sent(draft_id, "discord"):
        print(f"Discord notification already sent for {draft_id}. Skipping.")
        return True

    content = custom_body if custom_body else f"Draft ready for {company_name}. Reply YES {short_id if short_id else ''} to send."
    
    # 1. Try Bot if logged in
    if bot.is_ready():
        try:
            channel = bot.get_channel(int(CHANNEL_ID))
            if not channel:
                channel = await bot.fetch_channel(int(CHANNEL_ID))
            
            if channel:
                if file_path and os.path.exists(file_path):
                    file = discord.File(file_path, filename=os.path.basename(file_path))
                    await channel.send(content=content, file=file)
                else:
                    await channel.send(content=content)
                
                _mark_as_sent(draft_id, "discord")
                return True
        except Exception as e:
            print(f"Bot notification failed, trying Webhook fallback: {e}")

    # 2. Try Webhook fallback (useful for tests or if bot is flapping)
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_url:
        try:
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    response = requests.post(
                        webhook_url, 
                        data={"payload_json": json.dumps({"content": content})}, 
                        files={"file": (os.path.basename(file_path), f)}
                    )
            else:
                response = requests.post(webhook_url, json={"content": content})
                
            if response.status_code < 300:
                print("Discord Webhook notification sent.")
                _mark_as_sent(draft_id, "discord")
                return True
            else:
                print(f"Discord Webhook failed: {response.status_code}")
        except Exception as e:
            print(f"Discord Webhook error: {e}")

    print("All Discord notification paths failed.")
    return False

def _send_twilio_sms(draft_id, short_id, target_phone):
    """
    Sends a minimalist SMS via Twilio. 
    Note: Kept for fallback capability but not used in primary execution 'for now' as requested.
    """
    if _is_already_sent(draft_id, "sms", target_phone):
        print(f"Twilio SMS already sent to {target_phone}. Skipping.")
        return True

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")

    if not all([account_sid, auth_token, from_number]) or "XXXX" in from_number:
        print("Twilio credentials or phone number not set in .env.")
        return False

    try:
        client = TwilioClient(account_sid, auth_token)
        message = client.messages.create(
            body=f"Lead ready: YES {short_id}",
            from_=from_number,
            to=target_phone
        )
        print(f"Twilio SMS sent to {target_phone} (SID: {message.sid})")
        _mark_as_sent(draft_id, "sms", target_phone)
        return True
    except Exception as e:
        print(f"Failed to send Twilio SMS: {e}")
        return False

def _send_carrier_sms(draft_id, short_id, recipient=None, custom_body=None):
    """Sends a minimalist SMS via Gmail gateway (T-Mobile) or Twilio (AT&T fallback)."""
    global _gmail_service
    
    target_phone = os.getenv("SMS_TARGET_PHONE")
    
    # Logic to decide which path to take
    # AT&T email gateways are discontinued as of 2025.
    is_att = recipient and "att.net" in recipient.lower()
    
    if not recipient:
        if not target_phone or "XXXX" in target_phone:
            print("SMS_TARGET_PHONE not set correctly in .env.")
            return False
        # Default recipient is T-Mobile gateway (free)
        clean_phone = "".join(filter(str.isdigit, target_phone))
        if len(clean_phone) == 11 and clean_phone.startswith("1"):
            clean_phone = clean_phone[1:]
        recipient = f"{clean_phone}@tmomail.net"

    if is_att:
        print(f"AT&T recipient detected ({recipient}). Using Twilio fallback as gateways are discontinued.")
        pure_phone = target_phone if target_phone else recipient.split("@")[0]
        if not pure_phone.startswith("+"):
            pure_phone = "+1" + "".join(filter(str.isdigit, pure_phone))
        return _send_twilio_sms(draft_id, short_id, pure_phone)

    # Gmail Gateway Path (T-Mobile)
    if not _gmail_service:
        print("Gmail service not available for SMS.")
        return False

    if _is_already_sent(draft_id, "sms", recipient):
        print(f"SMS already sent for {draft_id} to {recipient}. Skipping.")
        return True

    from email.message import EmailMessage
    import base64
    
    msg = EmailMessage()
    msg.set_content(custom_body if custom_body else f"Lead ready: YES {short_id}")
    msg['To'] = recipient
    msg['Subject'] = ""
    
    try:
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        _gmail_service.users().messages().send(userId='me', body={'raw': raw}).execute()
        print(f"Carrier SMS sent to {recipient}")
        _mark_as_sent(draft_id, "sms", recipient)
        return True
    except Exception as e:
        print(f"Failed to send Carrier SMS to {recipient}: {e}. Trying Twilio fallback...")
        pure_phone = target_phone if target_phone else recipient.split("@")[0]
        if not pure_phone.startswith("+"):
            pure_phone = "+1" + "".join(filter(str.isdigit, pure_phone))
        return _send_twilio_sms(draft_id, short_id, pure_phone)

async def send_dual_notification(draft_id, company_name, custom_body=None, file_path=None, short_id=None, recipient=None):
    """Triggers both Discord and SMS notifications."""
    print(f"Triggering dual notifications for {company_name} (ID: {short_id})...")
    
    # 1. Discord (Rich) - Only send once per draft_id
    discord_success = False
    if not _is_already_sent(draft_id, "discord"):
        discord_success = await send_discord_notification(draft_id, company_name, custom_body, file_path, short_id)
    else:
        print(f"Skipping global Discord notification for {draft_id} (already sent).")
        discord_success = True
    
    # 2. SMS (Minimalist) - Can be sent to multiple specific recipients
    sms_success = _send_carrier_sms(draft_id, short_id, recipient, custom_body)
    
    return discord_success or sms_success

# Compatibility alias
send_sms_notification = send_dual_notification

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('------')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    content = message.content.strip().upper()
    if content.startswith("YES"):
        print(f"Received approval command in Discord: {message.content}")
        await handle_approval(message)

    await bot.process_commands(message)

async def handle_approval(message):
    global _gmail_service
    if not _gmail_service:
        await message.channel.send("❌ Bot is not connected to Gmail API. Please check the main script.")
        return

    content = message.content.strip().upper()
    # Find all patterns of "YES [digit]"
    matches = re.findall(r"YES\s+(\d+)", content)
    
    if not matches:
        # Check for plain "YES" without a number
        if content == "YES":
            pending_map = _load_pending_approvals()
            if pending_map:
                try:
                    last_key = sorted(pending_map.keys(), key=lambda x: int(x) if x.isdigit() else 0)[-1]
                    matches = [last_key]
                except:
                    matches = [list(pending_map.keys())[-1]]
            else:
                await message.channel.send("❌ No pending drafts found to approve.")
                return
        else:
            return # Not a command we recognize

    pending_map = _load_pending_approvals()
    results = []

    for val in matches:
        if val in pending_map:
            target_data = pending_map[val]
            
            # Compatibility check for old format
            if isinstance(target_data, str):
                draft_id = target_data
                service = _gmail_service 
            else:
                draft_id = target_data.get("draft_id")
                token_file = target_data.get("token", "token.json")
                service = _get_service_for_token(token_file)

            try:
                print(f"Sending approved draft {draft_id} for ID {val}...")
                service.users().drafts().send(userId='me', body={'id': draft_id}).execute()
                results.append(f"✅ `{val}`: Sent")
                # Remove from pending map once sent
                del pending_map[val]
            except Exception as e:
                print(f"Failed to send draft {draft_id}: {e}")
                results.append(f"❌ `{val}`: Error ({e})")
        else:
            results.append(f"❓ `{val}`: Not found")

    _save_pending_approvals(pending_map)
    
    if results:
        await message.channel.send("**Approval Results:**\n" + "\n".join(results))

# Maintain backward compatibility for the check_for_sms_approvals name, 
# although we now handle it live via on_message. 
# We still keep it to check for EMAIL-based replies if the user prefers that.
def check_for_email_approvals(service):
    """Checks Gmail inbox for YES replies (if user still sends emails to themselves)."""
    try:
        results = service.users().messages().list(
            userId='me',
            q='is:unread "YES"'
        ).execute()
        messages = results.get('messages', [])
        
        pending_map = _load_pending_approvals()
        
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            body = get_body(msg_data.get('payload', {})).upper()
            
            if "YES" not in body:
                continue
                
            # Find all patterns of "YES [digit]"
            matches = re.findall(r"YES\s+(\d+)", body)
            
            if not matches:
                # Fallback to last ID if no digit provided
                if pending_map:
                    try:
                        last_key = sorted(pending_map.keys(), key=lambda x: int(x) if x.isdigit() else 0)[-1]
                        matches = [last_key]
                    except:
                        matches = [list(pending_map.keys())[-1]]
            
            sent_count = 0
            for val in matches:
                if val in pending_map:
                    target_data = pending_map[val]
                    if isinstance(target_data, str):
                        draft_id = target_data
                        send_service = service
                    else:
                        draft_id = target_data.get("draft_id")
                        token_file = target_data.get("token", "token.json")
                        send_service = _get_service_for_token(token_file)
                        
                    try:
                        print(f"Sending approved draft {draft_id} for ID {val} via email...")
                        send_service.users().drafts().send(userId='me', body={'id': draft_id}).execute()
                        del pending_map[val]
                        sent_count += 1
                    except Exception as e:
                        print(f"Failed to send draft {draft_id} from email approval: {e}")
            
            if sent_count > 0:
                _save_pending_approvals(pending_map)
                
            # Mark email as read once it's processed (sent or not, to prevent loops on invalid replies)
            try:
                service.users().messages().modify(userId='me', id=msg['id'], body={'removeLabelIds': ['UNREAD']}).execute()
            except Exception as e:
                print(f"Failed to mark email {msg['id']} as read: {e}")
                
    except Exception as error:
        print(f'An error occurred checking Email approvals: {error}')
