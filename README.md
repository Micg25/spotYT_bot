🎵 spotYT_bot 🚀

<p align="center"> <img src="https://img.shields.io/badge/Spotify-1ED760?style=for-the-badge&logo=spotify&logoColor=white" alt="Spotify Logo"> <img src="https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="YouTube Logo"> <img src="https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram Logo"> </p>

A powerful Telegram bot designed to download tracks, albums, and playlists, and now featuring advanced capabilities to migrate playlists between Spotify and YouTube in both directions. It also includes smart features to resume interrupted migrations or merge playlists.
🛠 How It Works

    Metadata Retrieval: The bot uses Spotify and YouTube APIs to gather track details.

    Search & Download: Leverages yt_dlp and YouTube APIs to find and download audio in the best available quality.

    Bidirectional Migration (New!): Secure OAuth authentication allows you to manage playlists directly on your personal YouTube and Spotify accounts.

    Resume/Append Function (New!): If you provide both a source and a destination link, the bot will smartly add only the missing songs, preventing duplicates.

🚀 Installation and Configuration

Follow these steps to configure the bot correctly. You need to set variables in two main files.
1. Telegram Bot and Spotify Config (spotytdl_bot.py)

Open spotytdl_bot.py and fill in the following variables at the top:

    Telegram Bot:
    Python

    BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

    YouTube OAuth (Multi-Account): The bot supports rotating multiple Google accounts to bypass quota limits. Enter the filenames of your JSON credentials (downloaded from Google Cloud Console):
    Python

    CLIENT_SECRETS_FILE = ["client_secrets.json", "client_secrets2.json"]

    Spotify App Credentials: Create an app on the Spotify Developer Dashboard and enter the details:
    Python

    SPOTIFY_CLIENT_ID = "YOUR_CLIENT_ID"
    SPOTIFY_CLIENT_SECRET = "YOUR_CLIENT_SECRET"
    SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback" # Or the URI you set in the dashboard

2. Advanced YouTube Config (spotytdl.py)

Open spotytdl.py and configure the following:

    SOCS Cookie (Crucial): To prevent GDPR consent blocks when scraping public playlists, you must enter the value of the SOCS cookie from Google (get this by inspecting browser requests on YouTube):
    Python

    SOCS = "YOUR_SOCS_COOKIE_VALUE"

🎮 Available Commands
🔐 Authentication

Before migrating playlists, you must log in to the respective services:

    /loginyoutube : Log in to your YouTube account (required to create playlists or add videos). Supports account rotation if quota is exceeded.

    /loginspotify : Log in to your Spotify account (required to create playlists on Spotify).

📥 Download

    /dl <link> : Download single tracks, albums, or entire playlists from Spotify or YouTube and receive them as audio files on Telegram.

🔄 Migration (/migrate)

The /migrate command is smart and changes behavior based on the links provided:

    Spotify ➡ YouTube (New Playlist) Creates a new playlist on YouTube with songs from Spotify.

    /migrate <spotify_playlist_link>

    YouTube ➡ Spotify (New Playlist) Creates a new playlist on Spotify with videos from YouTube.

    /migrate <youtube_playlist_link>

    Spotify ➡ YouTube (Append/Resume) Adds songs from a Spotify playlist to an existing YouTube playlist. Useful for updating playlists or resuming an interrupted migration (skips existing duplicates).

    /migrate <spotify_playlist_link> <existing_youtube_playlist_link>

    YouTube ➡ Spotify (Append/Resume) Adds songs from a YouTube playlist to an existing Spotify playlist.

    /migrate <youtube_playlist_link> <existing_spotify_playlist_link>

📦 Requirements

    Python 3.x

    FFmpeg (installed on the system for audio conversion)

    Python Libraries:

        python-telegram-bot

        yt_dlp

        spotipy

        google-auth-oauthlib

        google-api-python-client

        requests

        beautifulsoup4

⚠️ Important Notes

    YouTube Quotas: Adding videos to playlists consumes a lot of API quota. The bot handles automatic rotation of client_secrets.json files if you provide more than one.

    SOCS Cookie: Without a valid SOCS cookie in spotytdl.py, functions reading public YouTube playlists may fail due to Google's consent banners.

Developed with ❤️ for music lovers.
