# 🎵 spotYT_bot 🚀

<p align="center">
  <img src="https://img.shields.io/badge/Spotify-1ED760?style=for-the-badge&logo=spotify&logoColor=white" alt="Spotify Logo">
  <img src="https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="YouTube Logo">
  <img src="https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram Logo">
</p>

A powerful Telegram bot designed to download **tracks, albums, and playlists** seamlessly. It bridges the gap between Spotify metadata and YouTube's vast library.

## 🛠 How it works
1. **Metadata Retrieval:** The bot uses the Spotify API (or manual input) to gather song details (Title, Artist, Album).
2. **Search:** It leverages the **YouTube Data API** to find the most accurate video match for the song.
3. **Download:** The audio is extracted and downloaded at high quality using `yt_dlp`.

---

## 🚀 Getting Started

Follow these steps to get your bot up and running:

### 1. Telegram Bot Token
Open `spotytdl_bot.py` and insert your Telegram Bot Token at **row 10**:
```python
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
```
2. YouTube API Keys

Open spotydl.py and add your YouTube API keys at row 10. You can add multiple keys to avoid rate limits:
Python
```python
API_KEY = ["KEY_1", "KEY_2"]
```
3. Spotify Access Token (Temporary Workaround)

    [!IMPORTANT]

    The automatic Spotify token retrieval is currently under maintenance.

If you need to download Spotify Playlists or Albums, you must manually provide a valid access token. Open spotydl.py, go to row 130 and insert your token:
Python
```python
access_token = "YOUR_SPOTIFY_ACCESS_TOKEN"
```
📦 Requirements

    Python 3.x

    yt_dlp

    python-telegram-bot

    A valid YouTube Data API v3 Key

Developed with ❤️ for music lovers.
