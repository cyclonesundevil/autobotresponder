import base64
import mimetypes
from email.message import EmailMessage
import os

def create_draft(service, to_email, subject, body, attachment_path=None):
    """Create and insert a draft email with an optional attachment.
    Returns the created draft.
    """
    try:
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to_email
        message['From'] = 'me'
        message['Subject'] = subject

        if attachment_path and os.path.exists(attachment_path):
            filename = os.path.basename(attachment_path)
            type_subtype, _ = mimetypes.guess_type(attachment_path)
            maintype, subtype = type_subtype.split('/') if type_subtype else ('application', 'octet-stream')

            with open(attachment_path, 'rb') as fp:
                attachment_data = fp.read()
            
            message.add_attachment(
                attachment_data,
                maintype=maintype,
                subtype=subtype,
                filename=filename
            )

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'message': {'raw': encoded_message}}
        
        draft = service.users().drafts().create(userId='me', body=create_message).execute()
        print(f"Draft id: {draft['id']} created.")
        return draft
    
    except Exception as error:
        print(f'An error occurred creating draft: {error}')
        return None
