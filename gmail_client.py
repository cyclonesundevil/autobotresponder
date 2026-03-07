import os.path
import base64
import sys
from email.message import EmailMessage

# Ensure standard output can handle Unicode characters on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_body(payload):
    """
    Recursively extract the plain text body from a Gmail message payload.
    Falls back to html if plain text is not found.
    """
    # 1. Look for text/plain
    def find_mime(p, mime):
        if p.get('mimeType') == mime:
            data = p.get('body', {}).get('data')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
        
        if 'parts' in p:
            for part in p['parts']:
                res = find_mime(part, mime)
                if res:
                    return res
        return None

    # Try plain text first
    body = find_mime(payload, 'text/plain')
    if body:
        return body
    
    # Fallback to html
    html = find_mime(payload, 'text/html')
    if html:
        # Very crude html to text: ideally we'd use BeautifulSoup, 
        # but let's just strip basic tags to keep it simple and avoid new deps.
        import re
        text = re.sub('<[^<]+?>', '', html)
        return text
    
    return ""

def get_gmail_service(token_file='token.json'):
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token_file stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Token expired or invalid. Deleting {token_file} to force re-authentication.")
                if os.path.exists(token_file):
                    os.remove(token_file)
                creds = None
        
        if not creds or not creds.valid:
            if not os.path.exists('credentials.json'):
                print("credentials.json not found! Please follow the README instructions to get your credentials.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(token_file, 'w') as token:
                token.write(creds.to_json())

    try:
        # Call the Gmail API
        service = build('gmail', 'v1', credentials=creds)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

if __name__ == '__main__':
    service = get_gmail_service()
    if service:
        print("Successfully connected to Gmail!")
