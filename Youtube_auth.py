import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

SCOPES = ["https://www.googleapis.com/auth/youtube"]
CLIENT_SECRETS_FILE = "client_secrets.json"

class YouTubeManager:
    def __init__(self):
        self.credentials = None
        self.youtube = None
        self.flow = None

    def get_auth_url(self):
        self.flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, SCOPES)
        self.flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
        
        auth_url, _ = self.flow.authorization_url(prompt='consent')
        return auth_url

    def authorize(self, code):
        try:
            self.flow.fetch_token(code=code)
            self.credentials = self.flow.credentials
            self.youtube = googleapiclient.discovery.build(
                "youtube", "v3", credentials=self.credentials)
            return True
        except Exception as e:
            print(f"Errore auth: {e}")
            return False
