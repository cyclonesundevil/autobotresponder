import os
import re
from dotenv import load_dotenv
from google import genai
from docx import Document

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    client = None
    
# gemini-2.5-flash-lite: Google's smallest/cheapest model, built for at-scale usage
MODEL_ID = 'gemini-2.5-flash-lite'

def extract_text_from_docx(file_path):
    """Reads paragraphs and tables from a word doc to ensure no content is missed."""
    doc = Document(file_path)
    full_text = []
    # Extract from paragraphs
    for para in doc.paragraphs:
        if para.text.strip():
            full_text.append(para.text)
    # Extract from tables (resumes often use tables for layout)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    full_text.append(cell.text)
    return '\n'.join(full_text)

def is_recruiter_opportunity(email_body):
    """
    Uses Gemini to determine if the email is a legitimate recruiter job opportunity.
    Returns True if it is, False otherwise.
    """
    if not API_KEY:
        return True # Default to True if AI is not available to avoid missing any

    prompt = f"""
    Analyze the following email and determine if it is a legitimate job opportunity, 
    a recruiter reaching out about a role, or a forwarded recruitment email.
    
    CRITERIA FOR 'TRUE':
    - Recruiters (internal or agency) reaching out about current or future roles.
    - Automated alerts from job boards (LinkedIn, Indeed) about specific matching jobs.
    - Forwarded emails that contain a job description or recruiter reach-out.
    - Mention of specific titles (Engineer, Developer, etc.), companies, or interview requests.

    CRITERIA FOR 'FALSE':
    - Generic newsletters, marketing spam, or promotional material (e.g., Domino's, SoFi, Total Wine).
    - Personal non-work correspondence.
    - "Work from home" scams or generic "earn money fast" emails.

    Respond with ONLY the word 'TRUE' if it is a legitimate recruiting/job opportunity, 
    or 'FALSE' if it is junk/irrelevant.
    
    Email:
    {email_body}
    """
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt).text.strip()
        return "TRUE" in response.upper()
    except Exception as e:
        print(f"Error classifying email: {e}")
        return True # Default to True on error

def extract_forward_to_email(email_body, sender_email):
    """
    Uses Gemini to determine if there is an explicit email address to forward
    the resume/application to, instead of the original sender.
    Returns the target email address, or the original sender_email if none found.
    """
    if not API_KEY:
        return sender_email
        
    prompt = f"""
    Analyze the following email and determine if the sender is asking for a resume or application 
    to be sent to a SPECIFIC email address that is NOT the sender's address and NOT my own email addresses (cyclsun@gmail.com or cyclonesundevil@gmail.com).

    CRITICAL RULES:
    1. DO NOT return my own email addresses: cyclsun@gmail.com or cyclonesundevil@gmail.com.
    2. DO NOT return LinkedIn email addresses (e.g., matching-reply@linkedin.com) or LinkedIn profile URLs.
    3. IF THIS IS A FORWARDED EMAIL (starts with "Forwarded message" or similar): 
       - Look for the "From:" line in the forwarded header to find the ORIGINAL recruiter's email.
       - Use that original email as the target unless there is an even more specific instruction to "forward" to another address.
    4. ONLY return a specific email address if there is an explicit instruction to "forward", "send", or "email" the resume to it, or if it's the original sender of a forwarded message.
    5. If the email just says "apply on LinkedIn" or provides a link to an application portal, respond with 'NONE'.

    Look for phrases like:
    - "Please forward your resume to hr@example.com"
    - "Send your details to recruiting@somecompany.com"
    - "Reply to hiringmanager@domain.com"
    - "If interested, email your resume to jobs@test.com"

    If you find a specific, valid target email address (not my own and not generic LinkedIn),
    respond with ONLY that email address (e.g., hr@example.com).
    
    If there is no specific target address found, respond with 'NONE'.

    Email:
    {email_body}
    """
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt).text.strip()
        # Clean up the output to make sure it's just the email or NONE
        response = response.strip("<> \n\r\t*")
        
        if response.upper() == 'NONE' or '@' not in response:
            return sender_email
            
        return response
    except Exception as e:
        print(f"Error extracting forward-to email: {e}")
        return sender_email

def generate_tailored_resume_docx(email_body, base_resume_path, output_path):
    """
    1. Extracts job requirements from email
    2. Tailors base resume
    3. Saves tailored resume as a simple docx
    """
    if not API_KEY:
        print("GEMINI_API_KEY is not set. Cannot use AI.")
        return None

    print(f"Reading base resume from {base_resume_path}...")
    base_text = extract_text_from_docx(base_resume_path)

    # Single prompt: extract requirements AND tailor resume in one API call
    # (halves quota usage vs. the previous two-call approach)
    print("Tailoring resume with Gemini (single call)...")
    combined_prompt = f"""
    You are an expert career coach. Below is a recruiter email and my base resume.
    First, internally identify the key skills, technologies, job title, and company name from the email.
    Then, rewrite my resume to highlight experience that best fits those requirements.
    
    CRITICAL INSTRUCTION: LEAN HEAVILY INTO MY AI EXPERIENCE. 
    Regardless of the specific role, aggressively emphasize any and all artificial intelligence, 
    machine learning, or LLM experience I have. 
    Bring my AI-related projects and responsibilities to the very top of my experience section 
    and ensure they are the focal point of my summary. Make it clear I am an AI-focused engineer.
    
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
    - Tailor the bullet points to the job description provided in the email, but ALWAYS filter it through an AI-heavy lens.
    
    Output the tailored resume in PURE MARKDOWN format.
    Use '#' for the main title (Jose C. Ramirez), '##' for section headers (e.g., Summary, Experience, Education),
    and standard bullet points ('-') for list items.
    DO NOT include any conversational text, preamble, or explanation — just the resume.

    Recruiter Email:
    {email_body}

    My Base Resume:
    {base_text}
    """
    tailored_md = client.models.generate_content(model=MODEL_ID, contents=combined_prompt).text

    print(f"Generating new Word document at {output_path}...")
    doc = Document()
    
    # Simple markdown parser
    lines = tailored_md.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('# '):
            doc.add_heading(line[2:].strip(), level=1)
        elif line.startswith('## '):
            doc.add_heading(line[3:].strip(), level=2)
        elif line.startswith('### '):
            doc.add_heading(line[4:].strip(), level=3)
        elif line.startswith('- ') or line.startswith('* '):
            # Clean up the bullet and any bolding asterisks which docx list bullets handle poorly natively without runs
            text = line[2:].strip().replace('**', '') 
            doc.add_paragraph(text, style='List Bullet')
        else:
            text = line.replace('**', '')
            doc.add_paragraph(text)
            
    doc.save(output_path)
    print("Done generating resume!")
    return output_path

if __name__ == "__main__":
    # Test block
    print("This file contains the resume processing logic.")
