import os
import json
import asyncio
import requests
from dotenv import load_dotenv

import sms_manager
from resume_processor import generate_tailored_resume_docx

load_dotenv()

BASE_RESUME_PATH = os.getenv("BASE_RESUME_PATH")

PROCESSED_JOBS_FILE = "processed_jobs.json"

# You can adjust these keywords to match exactly what you're looking for!
KEYWORDS = ["python", "software engineer", "backend developer", "data scientist"] 

def _load_processed_jobs():
    if os.path.exists(PROCESSED_JOBS_FILE):
        try:
            with open(PROCESSED_JOBS_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def _save_processed_jobs(jobs):
    with open(PROCESSED_JOBS_FILE, "w") as f:
        json.dump(list(jobs), f, indent=4)

def fetch_himalayas_jobs(keywords):
    jobs = []
    url = "https://himalayas.app/jobs/api"
    try:
        response = requests.get(f"{url}?limit=50")
        if response.status_code == 200:
            data = response.json()
            for job in data.get('jobs', []):
                title = job.get('title', '').lower()
                description = job.get('description', '').lower()
                
                if any(kw.lower() in title or kw.lower() in description for kw in keywords):
                    jobs.append({
                        "id": f"himalayas_{job.get('guid')}",
                        "title": job.get('title'),
                        "company": job.get('companyName'),
                        "url": job.get('applicationLink') or job.get('himalayasLink'),
                        "source": "Himalayas.app",
                        "description": description
                    })
    except Exception as e:
        print(f"Error fetching from Himalayas: {e}")
    return jobs

def fetch_remotive_jobs(keywords):
    jobs = []
    # Using the software-dev category to narrow it down and make the payload smaller
    url = "https://remotive.com/api/remote-jobs?category=software-dev"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Remotive returns a lot of jobs, limit our search to the 100 most recent
            for job in data.get('jobs', [])[:100]: 
                title = job.get('title', '').lower()
                description = job.get('description', '').lower()
                
                if any(kw.lower() in title or kw.lower() in description for kw in keywords):
                    jobs.append({
                        "id": f"remotive_{job.get('id')}",
                        "title": job.get('title'),
                        "company": job.get('company_name'),
                        "url": job.get('url'),
                        "source": "Remotive.com",
                        "description": description
                    })
    except Exception as e:
        print(f"Error fetching from Remotive: {e}")
    return jobs

async def scan_and_notify():
    print(f"Scanning job boards for keywords: {', '.join(KEYWORDS)}...")
    processed_jobs = _load_processed_jobs()
    
    h_jobs = fetch_himalayas_jobs(KEYWORDS)
    r_jobs = fetch_remotive_jobs(KEYWORDS)
    
    all_jobs = h_jobs + r_jobs
    new_jobs = [job for job in all_jobs if job['id'] not in processed_jobs]
    
    if not new_jobs:
        print("No new jobs found matching the keywords right now.")
        return

    print(f"Found {len(new_jobs)} new jobs!\n")
    
    for job in new_jobs:
        msg = f"🚀 New {job['source']} Job!\n**{job['title']}** at {job['company']}\nLink: {job['url']}"
        print(msg)
        print("-" * 40)
        
        filepath = None
        try:
            if BASE_RESUME_PATH and os.path.exists(BASE_RESUME_PATH):
                print(f"Generating tailored resume for {job['company']}...")
                import re
                safe_id = re.sub(r'[^A-Za-z0-9]', '_', job['id'])
                filepath = generate_tailored_resume_docx(
                    job['description'], 
                    BASE_RESUME_PATH, 
                    f"tailored_resume_{safe_id}.docx"
                )
        except Exception as e:
            print(f"Error generating resume for {job['id']}: {e}")
        
        try:
            # Send rich notification to Discord
            await sms_manager.send_discord_notification(
                draft_id=job['id'], # Using job ID as draft_id for the sentinel registry
                company_name=job['company'],
                custom_body=msg,
                file_path=filepath
            )
            
            # Send brief SMS notification
            sms_body = f"Job: {job['title']} @ {job['company']}"
            target_phone = os.getenv("SMS_TARGET_PHONE")
            
            # Try to send via T-Mobile Gateway or Twilio fallback
            sms_manager._send_carrier_sms(
                draft_id=job['id'],
                short_id="JOB", # No YES approval needed for job alerts
                custom_body=sms_body
            )
        except Exception as e:
            print(f"Error sending notifications for job {job['id']}: {e}")
            
        processed_jobs.add(job['id'])
        
    _save_processed_jobs(processed_jobs)
    print("\nFinished scanning.")

if __name__ == "__main__":
    asyncio.run(scan_and_notify())
