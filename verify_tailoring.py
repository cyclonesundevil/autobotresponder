from gmail_client import get_gmail_service, get_body
from resume_processor import generate_tailored_resume_docx, client, MODEL_ID, extract_text_from_docx
import os
from dotenv import load_dotenv

load_dotenv()

def verify_tailoring(msg_id, token_file='token.json'):
    service = get_gmail_service(token_file)
    if not service:
        print(f"Failed to connect using {token_file}")
        return

    print(f"Fetching message {msg_id}...")
    try:
        msg_data = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        body = get_body(msg_data.get('payload', {}))
        
        base_resume_path = os.getenv("BASE_RESUME_PATH")
        print(f"Reading base resume from {base_resume_path}...")
        base_text = extract_text_from_docx(base_resume_path)

        prompt = f"""
        You are an expert career coach. Below is a recruiter email and my base resume.
        First, internally identify the key skills, technologies, job title, and company name from the email.
        Then, rewrite my resume to highlight experience that best fits those requirements.
        
        IMPORTANT PERSONAL DETAILS (USE EXACTLY):
        - Name: Jose C. Ramirez
        - Location: Chandler, AZ (Always include City, State)
        - Phone: (480) 209-3709
        - Email: cyclsun@gmail.com
        - GitHub: https://github.com/cyclonesundevil
        - LinkedIn: DO NOT include any LinkedIn links or references.
        
        IMPORTANT CONTENT RULES:
        - Use the company names exactly as they appear in the Base Resume.
        - Preserve the original dates and job titles where appropriate.
        - Tailor the bullet points to the job description provided in the email.
        
        Output the tailored resume in PURE MARKDOWN format.
        Use '#' for the main title (Jose C. Ramirez), '##' for section headers (e.g., Summary, Experience, Education),
        and standard bullet points ('-') for list items.
        DO NOT include any conversational text, preamble, or explanation — just the resume.

        Recruiter Email:
        {body}

        My Base Resume:
        {base_text}
        """

        print("\n--- RECRUITER EMAIL ---")
        print(body[:500] + "...")
        print("\n--- CALLING GEMINI ---")
        
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        print("\n--- TAILORED RESUME (MARKDOWN) ---")
        print(response.text)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Looking for a real ID from sent_notifications.json or similar
    # r-1881654357432235849 -> 193c78864771c981 (Wait, I need the HEX ID, not the DECIMAL ID often shown in logs)
    # Actually, the IDs in the json were like "r-1881654357432235849"
    # Let's try to list messages first to get a valid hex ID correctly.
    service = get_gmail_service('token.json')
    results = service.users().messages().list(userId='me', q='is:unread', maxResults=1).execute()
    messages = results.get('messages', [])
    if messages:
        verify_tailoring(messages[0]['id'], 'token.json')
    else:
        print("No unread messages found to test with.")
