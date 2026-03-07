import os
import sys
import argparse
import time
from dotenv import load_dotenv
from gmail_client import get_gmail_service
from sms_manager import send_dual_notification

load_dotenv()

SMS_TARGET_PHONE = os.getenv("SMS_TARGET_PHONE")
NEW_ATT_NUMBER = "4802316231@txt.att.net"

def test_notifications():
    # Mock data for test
    mock_draft_id = "test_draft_" + str(int(time.time()))
    mock_sender = "Acme Corp"
    
    # Initialize Gmail service if not present for the manager
    import sms_manager
    if not sms_manager._gmail_service:
        sms_manager._gmail_service = get_gmail_service()

    # Generate dynamic phrasing
    print("Generating dynamic phrasing for test...")
    from sms_manager import get_dynamic_phrasing
    custom_msg = get_dynamic_phrasing(mock_sender, "99") 
    print(f"Test message: \"{custom_msg}\"")

    recipients = [
        "4802093709@tmomail.net",  # T-Mobile
        "4802316231@txt.att.net"   # AT&T (Note: Likely to bounce via Gmail gateway)
    ]

    # Register the test ID so it can be "approved" in the next step
    print(f"Registering test ID '99' for draft: {mock_draft_id}")
    sms_manager.register_pending_draft("99", mock_draft_id)

    import asyncio
    for recipient in recipients:
        print(f"\n>> Sending to: {recipient}")
        try:
            success = asyncio.run(sms_manager.send_dual_notification(
                mock_draft_id, 
                mock_sender, 
                custom_body=custom_msg,
                short_id="99",
                recipient=recipient
            ))
            if success:
                print(f"   Success for {recipient}! Check your channel/phone.")
            else:
                print(f"   Failed for {recipient}.")
        except Exception as e:
            print(f"   Error sending to {recipient}: {e}")

    print("\n" + "="*40)
    print("Test sequence complete.")

if __name__ == "__main__":
    test_notifications()
