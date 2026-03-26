import os

def get_state_path(filename):
    """
    Returns the absolute path for a state file, favoring the STATE_DIR 
    environment variable (used for Render persistent disks).
    If the file is a token and is missing on disk, it tries to bootstrap 
    it from an environment variable (e.g., TOKEN_JSON_CONTENT).
    """
    state_dir = os.environ.get("STATE_DIR", ".")
    
    # Ensure the directory exists
    if not os.path.exists(state_dir):
        os.makedirs(state_dir, exist_ok=True)
        
    path = os.path.join(state_dir, filename)
    
    # Bootstrap from ENV if missing (useful for first-time Render deployment)
    if not os.path.exists(path):
        # Look for ENV var like TOKEN_JSON or TOKEN_WORK_JSON
        env_key = filename.replace(".", "_").upper() + "_CONTENT"
        env_val = os.environ.get(env_key)
        if env_val:
            print(f"Bootstrapping {filename} from environment variable {env_key}...")
            with open(path, 'w') as f:
                f.write(env_val)
                
    return path
