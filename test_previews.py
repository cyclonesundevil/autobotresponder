import os
from dotenv import load_dotenv
import sms_manager

load_dotenv()

def test_enhanced_notifications():
    # Setup dummy data
    company = "FutureTech Corp"
    short_id = "99" # Test identifier
    dummy_file = "test_resume.docx"
    
    # Create a dummy file if base resume exists
    base_resume = os.getenv("BASE_RESUME_PATH")
    if base_resume and os.path.exists(base_resume):
        import shutil
        shutil.copy(base_resume, dummy_file)
    else:
        # Create empty file if no base resume
        with open(dummy_file, "w") as f:
            f.write("Dummy Resume Content")

    print(f"Testing Discord notification for {company} with Short ID {short_id}...")
    
    # Generate phrasing
    body = sms_manager.get_dynamic_phrasing(company, short_id)
    print(f"Alert Text: {body}")
    
    # Send
    success = sms_manager.send_sms_notification(
        draft_id="test_draft_id",
        company_name=company,
        custom_body=body,
        file_path=dummy_file,
        short_id=short_id
    )
    
    if success:
        print("Success! Check Discord for the message AND the file attachment.")
    else:
        print("Failed. Check logs.")

if __name__ == "__main__":
    test_enhanced_notifications()
