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
