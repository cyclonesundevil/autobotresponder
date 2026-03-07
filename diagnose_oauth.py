import json
import os

def diagnose():
    credentials_path = "credentials.json"
    
    if not os.path.exists(credentials_path):
        print(f"ERROR: {credentials_path} not found in the current directory.")
        return

    try:
        with open(credentials_path, "r") as f:
            data = json.load(f)
            
        client_info = data.get("installed") or data.get("web")
        if not client_info:
            print("ERROR: credentials.json format is unrecognized (neither 'installed' nor 'web' found).")
            return

        client_id = client_info.get("client_id")
        project_id = client_info.get("project_id")
        
        print("\n=== OAuth Diagnostic Details ===")
        print(f"Project ID: {project_id}")
        print(f"Client ID:  {client_id}")
        print("\nMATCH CHECK:")
        print("1. Go to https://console.cloud.google.com/apis/credentials")
        print("2. Ensure the project at the top left is exactly: " + project_id)
        print("3. Check if the 'OAuth 2.0 Client IDs' listed matches the Client ID above.")
        
        from gmail_client import SCOPES
        print("\nRequested Scopes:")
        for scope in SCOPES:
            print(f" - {scope}")
            
    except Exception as e:
        print(f"An error occurred during diagnosis: {e}")

if __name__ == "__main__":
    diagnose()
