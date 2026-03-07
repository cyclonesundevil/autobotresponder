# Google Cloud Console Setup for Gmail API

To use the Gmail API, you need to create a project in the Google Cloud Console and download an OAuth 2.0 Client ID credential file.

Follow these steps carefully:

1. **Go to Google Cloud Console**: https://console.cloud.google.com/
2. **Create a New Project**:
   - Click the project dropdown near the top-left (next to the Google Cloud logo).
   - Click **New Project**.
   - Name it "Auto Recruiter Responder" and click **Create**.
3. **Enable the Gmail API**:
   - Make sure your new project is selected.
   - Go to "APIs & Services" -> "Library".
   - Search for "Gmail API" and click it.
   - Click **Enable**.
4. **Configure the OAuth Consent Screen**:
   - Go to "APIs & Services" -> "OAuth consent screen".
   - Choose **External** (unless you have a Google Workspace account, then choose Internal). Click **Create**.
   - Fill in required fields (App Name: "Auto Responder", User Support Email: your email, Developer Contact Info: your email).
   - Click **Save and Continue**.
   - For **Scopes**, click "Add or Remove Scopes" and add `https://www.googleapis.com/auth/gmail.modify`. Click Save and Continue.
   - For **Test users**, click "Add Users" and type in your own Gmail address. **THIS IS CRITICAL**, otherwise it will block you from logging in. Click Save and Continue.
5. **Create Credentials**:
   - Go to "APIs & Services" -> "Credentials".
   - Click **Create Credentials** -> **OAuth client ID**.
   - Application type: **Desktop app**.
   - Name: "Auto Responder Desktop Client".
   - Click **Create**.
6. **Download JSON**:
   - In the popup that appears with your Client ID and Secret, click **DOWNLOAD JSON**.
   - Rename the downloaded file to exactly `credentials.json`.
   - **Move this file to**: `C:\Users\cyclo\.gemini\antigravity\scratch\auto-recruiter-responder\credentials.json`

Once you have done this, let me know!
