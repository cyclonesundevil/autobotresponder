import subprocess
import time
import sys

def run_services():
    print("--- Starting Combined Auto-Recruiter Services ---")
    
    # Start the Recruiter Bot (main.py)
    # Note: main.py includes the Discord bot which has its own event loop
    print("Launching Recruiter Bot (main.py)...")
    p1 = subprocess.Popen([sys.executable, "main.py"])
    
    # Start the SMS Command Center (sms_command_center.py)
    print("Launching SMS Command Center (sms_command_center.py)...")
    p2 = subprocess.Popen([sys.executable, "sms_command_center.py"])
    
    try:
        while True:
            # Check if processes are still running
            if p1.poll() is not None:
                print("ERORR: Recruiter Bot (main.py) stopped. Restarting...")
                p1 = subprocess.Popen([sys.executable, "main.py"])
            
            if p2.poll() is not None:
                print("ERROR: SMS Command Center stopped. Restarting...")
                p2 = subprocess.Popen([sys.executable, "sms_command_center.py"])
                
            time.sleep(10)
    except KeyboardInterrupt:
        print("Shutting down...")
        p1.terminate()
        p2.terminate()

if __name__ == "__main__":
    run_services()
