from resume_processor import (
    client,
    extract_text_from_docx,
    MODEL_ID,
    render_tailored_resume_on_template,
)
import re
from dotenv import load_dotenv

load_dotenv()

def generate_custom_resume(email_body, base_resume_path, output_path):
    base_text = extract_text_from_docx(base_resume_path)
    
    # Hard-code the date correction to avoid AI hallucination
    # Original: Jan 2013- July 2014
    base_text = base_text.replace("Jan 2013 July 2014", "Jan 2013 - March 24, 2026")
    base_text = base_text.replace("Jan 2013- July 2014", "Jan 2013 - March 24, 2026")
    
    custom_prompt = f"""
    You are a careful resume editor.
    Tailor the resume to the recruiter email using only the facts already present in the base resume.

    CRITICAL RULES:
    - Preserve the existing employers, dates, titles, and achievements from the base resume.
    - Do not invent schools, degrees, institutions, certifications, or names.
    - Do not invent new companies, dates, technologies, or bullet points.
    - If a section or detail is not present in the base resume, omit it instead of creating it.
    - If the recruiter email mentions relevant keywords, emphasize them only through existing experience and skills already supported by the base resume.
    - Keep the resume factual, professional, and conservative.
    - Output the resume in PURE MARKDOWN format.

    Important personal details to preserve:
    - Name: Jose C. Ramirez
    - Location: Chandler, AZ
    - Phone: (480) 209-3709
    - Email: cyclsun@gmail.com
    - GitHub: https://github.com/cyclonesundevil

    Email from Recruiter:
    {email_body}

    Base Resume:
    {base_text}
    """
    
    print("Generating resume with custom prompt...")
    tailored_md = client.models.generate_content(model=MODEL_ID, contents=custom_prompt).text

    # Drop fabricated education/school details that are not present in the base resume.
    base_text_lower = base_text.lower()
    filtered_lines = []
    skip_education_section = False
    for line in tailored_md.splitlines():
        stripped = line.strip()
        if re.match(r'^(#{1,6}\s*)?education\b', stripped, re.I):
            skip_education_section = True
            continue
        if skip_education_section and (stripped.startswith('#') or stripped.startswith('##') or stripped.startswith('###') or stripped == '---'):
            skip_education_section = False
        if skip_education_section:
            continue
        if re.search(r'\b(bachelor|bachelor\'s|master|masteral|doctoral|associate|degree|university|college|school|stanford|berkeley)\b', stripped, re.I):
            if 'education' not in base_text_lower and 'degree' not in base_text_lower and 'university' not in base_text_lower and 'college' not in base_text_lower:
                continue
        filtered_lines.append(line)
    tailored_md = '\n'.join(filtered_lines).strip()

    if re.search(r'\b(stanford|berkeley|bachelor|bachelor\'s|master|masteral|doctoral|associate|degree|university|college|school|30\+ years|30 years)\b', tailored_md, re.I):
        print("Suspicious hallucinated education/experience details detected; falling back to the verified base resume text.")
        tailored_md = base_text

    # Globally strip markdown code blocks if present
    tailored_md = tailored_md.replace("```markdown", "").replace("```", "").strip()
    
    # FORCE WEBSITE INCLUSIONS
    if "www.microcompit.com" not in tailored_md:
        tailored_md = tailored_md.replace("cyclsun@gmail.com", "cyclsun@gmail.com | www.microcompit.com")
    
    # STRIP ANY AI PARENTHETICAL NOTES
    tailored_md = re.sub(r'\(Note:.*?\)', '', tailored_md)
    # Ensure the date is exactly as requested
    tailored_md = tailored_md.replace("March 2026", "March 24, 2026")
    tailored_md = tailored_md.replace("March 24, 2026", "March 24, 2026") # Ensure it's not doubled

    print(f"Saving formatted resume to {output_path}...")
    render_tailored_resume_on_template(base_resume_path, tailored_md, output_path)
    print("Resume generated successfully!")
    return output_path

if __name__ == "__main__":
    with open('full_email_utf8.txt', 'r', encoding='utf-8') as f:
        email_body = f.read()
    generate_custom_resume(email_body, 'base_resume.docx', 'tailored_resume_final_v18.docx')
