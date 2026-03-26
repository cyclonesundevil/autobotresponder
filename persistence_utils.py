import os
from dotenv import load_dotenv

# Redundantly load dotenv in case it's mounted as a secret file in a non-standard path
load_dotenv()

def get_state_path(filename):
    """
    Returns the absolute path for a state file, favoring the STATE_DIR 
    environment variable (used for Render persistent disks).
    """
    state_dir = os.environ.get("STATE_DIR", ".")
    path = os.path.abspath(os.path.join(state_dir, filename))
    
    # Debug: Print environment keys (sanitized)
    keys = [k for k in os.environ.keys() if k.isupper()]
    print(f"[Persistence] Debug: Available Env Keys: {', '.join(keys[:10])}... (Total: {len(keys)})")
    print(f"[Persistence] Request for '{filename}'. Target path: {path}")
    
    if not os.path.exists(path):
        # Look for ENV var like TOKEN_JSON_CONTENT
        env_key = filename.replace(".", "_").upper() + "_CONTENT"
        env_val = os.environ.get(env_key)
        
        print(f"[Persistence] File missing. Checking env var '{env_key}'...")
        
        if env_val:
            try:
                # Ensure directory exists before writing
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w') as f:
                    f.write(env_val)
                print(f"[Persistence] SUCCESS: Bootstrapped {filename} from {env_key}.")
            except Exception as e:
                print(f"[Persistence] ERROR writing bootstrap file: {e}")
        else:
            print(f"[Persistence] WARNING: Env var '{env_key}' not found or empty.")
                
    return path

def cleanup_old_resumes(max_count=5):
    """
    Scans the STATE_DIR for tailored resumes and deletes all but the 
    most recent 'max_count' files to conserve disk space.
    """
    state_dir = os.environ.get("STATE_DIR", ".")
    resumes = []
    
    # Identify tailored resume files
    for f in os.listdir(state_dir):
        if f.startswith("tailored_resume_") and f.endswith(".docx"):
            full_path = os.path.join(state_dir, f)
            resumes.append({
                "path": full_path,
                "mtime": os.path.getmtime(full_path)
            })
            
    # Sort by time (newest first)
    resumes.sort(key=lambda x: x["mtime"], reverse=True)
    
    # Delete older ones
    if len(resumes) > max_count:
        print(f"[Cleanup] Found {len(resumes)} resumes. Keeping {max_count} newest.")
        for r in resumes[max_count:]:
            try:
                os.remove(r["path"])
                print(f"[Cleanup] Deleted old resume: {os.path.basename(r['path'])}")
            except Exception as e:
                print(f"[Cleanup] ERROR deleting {r['path']}: {e}")
    else:
        print(f"[Cleanup] System healthy. Resumes Count: {len(resumes)}/{max_count}")
