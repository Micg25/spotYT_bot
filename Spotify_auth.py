import spotipy
from spotipy.oauth2 import SpotifyOAuth

SCOPES = [
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-public",
    "playlist-modify-private",
    "user-library-read",
    "user-library-modify"
]

class SpotifyManager:
    def __init__(self):
        self.credentials = None
        self.spotify = None
        self.auth_manager = None

    def get_auth_url(self, client_id, client_secret, redirect_uri='http://127.0.0.1:8888/callback'):
        self.auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=" ".join(SCOPES),
            show_dialog=True,
            cache_path=None,
            open_browser=False
        )
        
        auth_url = self.auth_manager.get_authorize_url()
        return auth_url

    def authorize(self, code):
        try:
            token_info = self.auth_manager.get_access_token(code, as_dict=True, check_cache=False)
            self.credentials = token_info
            self.spotify = spotipy.Spotify(auth_manager=self.auth_manager)
            return True
        except Exception as e:
            print(f"Errore auth: {e}")
            return False
