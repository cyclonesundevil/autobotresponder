import os
from dotenv import load_dotenv

from resume_processor import extract_forward_to_email

load_dotenv()

def test_extraction():
    sender = "recruiter@agency.com"
    
    # Test 1: Explicit instruction
    body1 = "Hi Jose, we have a great role for you. Please forward your resume to hiringmanager@techcorp.com if interested."
    print("Test 1 (Explicit instruction):")
    print(f"Body: {body1}")
    result1 = extract_forward_to_email(body1, sender)
    print(f"Result: {result1}")
    print(f"Pass: {result1 == 'hiringmanager@techcorp.com'}\n")

    # Test 2: No instruction
    body2 = "Hi Jose, please let me know when you are free to chat about this opportunity. Thanks, Sarah."
    print("Test 2 (No instruction):")
    print(f"Body: {body2}")
    result2 = extract_forward_to_email(body2, sender)
    print(f"Result: {result2}")
    print(f"Pass: {result2 == sender}\n")

    # Test 3: Multiple emails (should pick the designated one)
    body3 = ("I'm reaching out from TopTalent recruiting. While I (recruiter@agency.com) am managing the intake, "
             "please send your details to careers-intake@clientcompany.com to be officially considered.")
    print("Test 3 (Multiple emails, pick designated):")
    print(f"Body: {body3}")
    result3 = extract_forward_to_email(body3, sender)
    print(f"Result: {result3}")
    print(f"Pass: {result3 == 'careers-intake@clientcompany.com'}\n")

    # Test 4: My own email in signature
    body4 = "Hi Jose, looking forward to your reply. Best, Jose C. Ramirez (cyclsun@gmail.com)"
    print("Test 4 (Own email in signature):")
    print(f"Body: {body4}")
    result4 = extract_forward_to_email(body4, sender)
    print(f"Result: {result4}")
    print(f"Pass: {result4 == sender}\n")

    # Test 5: LinkedIn reply address
    body5 = "A new job matches your profile! Click here to apply: https://www.linkedin.com/jobs/view/123456. Reply to: matching-reply@linkedin.com"
    print("Test 5 (LinkedIn address):")
    print(f"Body: {body5}")
    result5 = extract_forward_to_email(body5, sender)
    print(f"Result: {result5}")
    print(f"Pass: {result5 == sender}\n")

    # Test 6: Second own email in signature
    body6 = "Hi Jose, looking forward to your reply. Best, Jose C. Ramirez (cyclonesundevil@gmail.com)"
    print("Test 6 (Second own email in signature):")
    print(f"Body: {body6}")
    result6 = extract_forward_to_email(body6, sender)
    print(f"Result: {result6}")
    print(f"Pass: {result6 == sender}\n")

    # Test 7: Forwarded email
    body7 = """
    ---------- Forwarded message ---------
    From: Recruiter Name <recruiter@bigagency.com>
    Date: Mon, Feb 24, 2026 at 10:00 AM
    Subject: Job Opportunity
    To: <cyclonesundevil@gmail.com>

    Hi Jose, I work for Big Agency and we have a role for you...
    """
    print("Test 7 (Forwarded email):")
    print(f"Body: {body7}")
    result7 = extract_forward_to_email(body7, sender)
    print(f"Result: {result7}")
    print(f"Pass: {result7 == 'recruiter@bigagency.com'}\n")

if __name__ == "__main__":
    test_extraction()
