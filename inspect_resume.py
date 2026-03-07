import os
from resume_processor import extract_text_from_docx
from dotenv import load_dotenv

load_dotenv()

def inspect_base_resume():
    path = os.getenv("BASE_RESUME_PATH")
    if not path or not os.path.exists(path):
        print(f"Base resume not found at {path}")
        return

    print(f"Extracting text from {path}...")
    try:
        text = extract_text_from_docx(path)
        print("\n--- Start of Resume Text ---")
        # Print first 20 lines to see header/contact info
        lines = text.split('\n')
        for line in lines[:30]:
            print(line)
        print("--- ... ---")
        
        # Look for companies/locations
        print("\n--- Potential Companies/Locations Found ---")
        # Search for lines that look like experience headers (usually they have dates or specific names)
        for line in lines:
            if any(key in line for key in ["Inc", "Corp", "LLC", "Ltd", "Company"]):
                print(f"Found: {line}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_base_resume()
