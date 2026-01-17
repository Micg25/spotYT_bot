# 🎵 spotYT_bot 🚀

<img width="1259" height="374" alt="Screenshot from 2026-01-16 11-18-26" src="https://github.com/user-attachments/assets/60678e59-2c83-4f56-901c-886d6481f1fd" />

<p align="center">
  <img src="https://img.shields.io/badge/Spotify-1ED760?style=for-the-badge&logo=spotify&logoColor=white" alt="Spotify Logo">
  <img src="https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="YouTube Logo">
  <img src="https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram Logo">
</p>

A powerful Telegram bot designed to download **tracks, albums, and playlists** seamlessly, and now **migrate your Spotify playlists directly to your YouTube account**. It bridges the gap between Spotify metadata and YouTube's vast library.

## 🛠 How it works
1. **Metadata Retrieval:** The bot uses the Spotify API (or manual input) to gather song details (Title, Artist, Album).
2. **Search:** It leverages the **YouTube Data API** to find the most accurate video match for the song.
3. **Download:** The audio is extracted and downloaded at high quality using `yt_dlp`.
4. **Migration (New!):** Authenticates securely with your YouTube account to migrate your Spotify playlists on your youtube and youtube music personal account!.

---

## 🚀 Getting Started

Follow these steps to get your bot up and running:

### 1. Telegram Bot Token
Open `spotytdl_bot.py` and insert your Telegram Bot Token at **row 12**:

    BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

###2. YouTube API Keys

Open spotytdl.py and add your YouTube API keys at row 10. You can add multiple keys to avoid rate limits:
Python

    API_KEY = ["KEY_1", "KEY_2"]

###3. YouTube OAuth Credentials (Required for Migration)

To use the playlist migration feature (/SpotifyToYoutube), the bot needs to act on your behalf:

    Go to the Google Cloud Console.

    Create a new Project or select an existing one.

    Navigate to APIs & Services > Credentials.

    Click Create Credentials > OAuth Client ID.

    Select Desktop App as the application type.

    Download the JSON file, rename it to client_secrets.json, and place it in the main directory of the bot.

    Important: Ensure you add your email (and any other testers) to the Test Users list in the "OAuth Consent Screen" section.

###4. Spotify Access Token (Temporary Workaround)

    [!IMPORTANT] The automatic Spotify token retrieval is currently under maintenance.

If you need to download Spotify Playlists or Albums, you must manually provide a valid access token. Open spotytdl.py, go to row 127 and insert your token:
Python

    access_token = "YOUR_SPOTIFY_ACCESS_TOKEN"

🎮 Commands

    /dl <link> : Download tracks, albums, or playlists from Spotify/YouTube.

    /login : Authenticate with your YouTube account (required once before migrating).

    /spotifytoyt <spotify_link> : Migrate a Spotify playlist to your YouTube account.

📦 Requirements

    Python 3.x

    yt_dlp

    python-telegram-bot

    google-auth-oauthlib

    google-api-python-client

    A valid YouTube Data API v3 Key

    client_secrets.json for OAuth functionality

Developed with ❤️ for music lovers.
