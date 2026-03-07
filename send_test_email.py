import os
import base64
from email.message import EmailMessage
from gmail_client import get_gmail_service

def send_test_email():
    service = get_gmail_service()
    if not service:
        print("Could not get Gmail service.")
        return

    try:
        # Get user's own email address to send to themselves
        profile = service.users().getProfile(userId='me').execute()
        user_email = profile['emailAddress']

        message = EmailMessage()
        message.set_content(
            "Hi there,\n\n"
            "We came across your profile and think you would be a great fit for our "
            "Senior Python Developer role at TechCorp.\n\n"
            "We are looking for someone with strong experience in Python, API integration, "
            "and building automated systems. Familiarity with LLMs and the Google Cloud Platform "
            "is a huge plus.\n\n"
            "If you are interested, please send over your updated resume.\n\n"
            "Best,\n"
            "Jane Doe\n"
            "Recruiter, TechCorp"
        )
        message['To'] = user_email
        message['From'] = user_email
        message['Subject'] = "Exciting New Opportunity at TechCorp"

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}

        send_message = service.users().messages().send(userId='me', body=create_message).execute()
        print(f"Test email sent! Message Id: {send_message['id']}")

    except Exception as error:
        print(f'An error occurred sending test email: {error}')

if __name__ == '__main__':
    send_test_email()
