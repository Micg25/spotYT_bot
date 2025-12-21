# spotYT_bot
A telegram bot that allows you to download: tracks, albums and even your playlists from Youtube and Spotify.
It uses Youtube API to find each song, on the Spotify side it's used only to retreive the metadata that will be crunched by the Youtube APIs to find the exact song.
Finally each song is downloaded with yt_dlp.


In order to make it work:
1. Inside spotytdl_bot.py at the 10th row insert your BOT_TOKEN="" 
2. Inside spotydl.py at the 10th row insert your Youtube Api keys API_KEY=["",""] #insert yor Youtube API_keys
3. The Spotify Token retrieving proocesso is not working at the moment, so if you need it (you'll need it in actions such as loading Spotify playlists or Albums) put your spotify access token inside the variable at the 130th row: access_token="" #insert your access token
