import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from telegram.request import HTTPXRequest
import spotytdl
from spotytdl import QuotaExceededException
import os
from telegram.error import TimedOut, TelegramError
import asyncio
import httpx
from telegram.ext import ConversationHandler, MessageHandler, filters
from Youtube_auth import YouTubeManager
from Spotify_auth import SpotifyManager
from functools import partial

BOT_TOKEN=""
CLIENT_SECRETS_FILE = ["client_secrets.json","client_secrets2.json","..."]

# Spotify credentials - Insert here your Spotify app credentials
SPOTIFY_CLIENT_ID = ""
SPOTIFY_CLIENT_SECRET = ""
SPOTIFY_REDIRECT_URI = ""

user_sessions = {}
spotify_sessions = {}

WAITING_CODE = 1
WAITING_CODE_SPOTIFY = 2

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE,i=None):
    chat_id = update.effective_chat.id
    manager = YouTubeManager()
    user_sessions[chat_id] = manager
    print("Inside login i=",i[0],CLIENT_SECRETS_FILE[i[0]])
    auth_url = manager.get_auth_url(CLIENT_SECRETS_FILE=CLIENT_SECRETS_FILE[i[0]])
    
    msg = (
        f"To migrate your playlist you must authorize the app on Youtube.\n"
        f"1. Click here: <a href='{auth_url}'>AUTH LINK</a>\n"
        f"2. Access, conesent and copy the code that will appear\n"
        f"3. Send it here in the chat."
    )
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
    return WAITING_CODE

async def receive_auth_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    code = update.message.text
    
    manager = user_sessions.get(chat_id)
    if not manager:
        await update.message.reply_text("Session error. Restart the login")
        return ConversationHandler.END

    if manager.authorize(code):
        await update.message.reply_text("✅ Login was successful now you can use the /spotifytoyt {link_spotify} command ")
    else:
        await update.message.reply_text("❌ Invalid code or general error")
    
    return ConversationHandler.END

async def login_spotify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    manager = SpotifyManager()
    spotify_sessions[chat_id] = manager
    
    auth_url = manager.get_auth_url(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI
    )
    
    msg = (
        f"To access Spotify you must authorize the app.\n"
        f"1. Click here: <a href='{auth_url}'>SPOTIFY AUTH LINK</a>\n"
        f"2. Access, consent and you will be redirected to a page\n"
        f"3. Copy the full URL from the address bar (it will contain 'code=...')\n"
        f"4. Send the complete URL here in the chat."
    )
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
    return WAITING_CODE_SPOTIFY

async def receive_spotify_auth_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    response = update.message.text
    
    manager = spotify_sessions.get(chat_id)
    if not manager:
        await update.message.reply_text("Session error. Restart the login with /loginspotify")
        return ConversationHandler.END

    # Extract the code parameter from the URL if the user sent the entire URL
    code = response
    if "code=" in response:
        try:
            code = response.split("code=")[1].split("&")[0]
        except:
            await update.message.reply_text("❌ Cannot extract code from URL. Please try again.")
            return ConversationHandler.END

    if manager.authorize(code):
        await update.message.reply_text("✅ Spotify login was successful! You can now use Spotify features.")
    else:
        await update.message.reply_text("❌ Invalid code or general error. Please try /loginspotify again.")
    
    return ConversationHandler.END


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="1. use the command <code>/dl {spotify/youtube link}</code>  to start downloading tracks and albums " \
    "\n 2. use the command <code>/migrate {playlist_link}</code> to migrate playlists:" \
    "\n    • Spotify → YouTube: <code>/migrate {spotify_playlist_link}</code>" \
    "\n    • YouTube → Spotify: <code>/migrate {youtube_playlist_link}</code>" \
    "\n    • Add to existing: <code>/migrate {source_playlist} {destination_playlist}</code>" \
    "\n 3. Login commands:" \
    "\n    • <code>/loginyoutube</code> - Login to YouTube (required for Spotify → YouTube)" \
    "\n    • <code>/loginspotify</code> - Login to Spotify (required for YouTube → Spotify)",parse_mode="HTML")


async def sendSong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if not context.args:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Error: Missing link. Usage: /dl {link}")
        return

    print(f"User {chat_id} requested: {context.args[0]}")
    await context.bot.send_message(chat_id=chat_id, text="The download is starting...",parse_mode="HTML")
    
    try:

        titles = await asyncio.to_thread(spotytdl.main, context.args[0], chat_id=chat_id)
        
        if (titles is None):
            await context.bot.send_message(chat_id=chat_id, text="Error while downloading.")
            return
            
        print("TITLES:", titles)
        
        if isinstance(titles, list):
            for title in titles:
                n_try=0
                print("trying to send: ",title)
                file_path = title + str(chat_id) + ".m4a"
                
                while True:
                    if(n_try>5):
                        await context.bot.send_message(chat_id=chat_id, text=f"Error while sending: {title}")
                        break
                    try:
                        n_try+=1
                        if os.path.exists(file_path):
                            await context.bot.send_audio(chat_id=chat_id,audio=open(file_path,"rb"))
                            os.remove(file_path)
                        else:
                            print(f"File {file_path} not found (maybe download failed)")
                        break
                    except TimedOut:
                        print(f"⏱ Timeout while sending: '{title}', trying again...")
                        await asyncio.sleep(3)  
                    except TelegramError as e:
                        await context.bot.send_message(chat_id=chat_id, text=f"Error while sending: '{title}, {e}'")
                        break  
                    except Exception as e:
                        await context.bot.send_message(chat_id=chat_id, text=f"Error while sending: {title}, {e}")
                        break
        else:
            await context.bot.send_message(chat_id=chat_id, text="The download of the song is almost done...",parse_mode="HTML")
            title = titles
            file_path = title + str(chat_id) + ".m4a"
            
            while True:
                n_try=0
                if(n_try>2):
                    await context.bot.send_message(chat_id=chat_id, text=f"Error while sending: {title}")
                    break
                try:
                    n_try+=1
                    if os.path.exists(file_path):
                        await context.bot.send_audio(chat_id=chat_id,audio=open(file_path,"rb"))
                        os.remove(file_path)
                    else:
                        await context.bot.send_message(chat_id=chat_id, text="Error: File not found on server.")
                    break
                except TimedOut:
                    print(f"Timeout while sending: '{title}', trying again...")
                    await asyncio.sleep(3) 
                except TelegramError as e:
                    print(f"Error while sending: '{title}'")
                    await context.bot.send_message(chat_id=chat_id, text=f"Error while sending: '{title}', {e}")
                    break  
                except Exception as e:
                    await context.bot.send_message(chat_id=chat_id, text=f"Error while sending: '{title}', {e}")
                    break

    except RuntimeError as e:
        await context.bot.send_message(chat_id=chat_id, text=f"{str(e)}")
        return
    await context.bot.send_message(chat_id=chat_id, text="Done",parse_mode="HTML")
    
async def migratePlaylist(update: Update, context: ContextTypes.DEFAULT_TYPE,i=None):
    chat_id = update.effective_chat.id
    
    if not context.args:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ You must insert a link Example:\n<code>/migrate https://open.spotify.com/playlist/...</code> (Spotify to YouTube)\n<code>/migrate https://www.youtube.com/playlist?list=...</code> (YouTube to Spotify)\nOr:\n<code>/migrate https://open.spotify.com/playlist/... https://www.youtube.com/playlist?list=...</code> (Add Spotify to existing YouTube playlist)\n<code>/migrate https://www.youtube.com/playlist?list=... https://open.spotify.com/playlist/...</code> (Add YouTube to existing Spotify playlist)", parse_mode="HTML")
        return

    
    url = context.args[0]
    
    if len(context.args) == 2:
        second_url = context.args[1]
        
        # Case 1: YouTube → Spotify 
        if url.startswith("https://www.youtube.com/playlist") and second_url.startswith("https://open.spotify.com/playlist"):
            spotify_manager = spotify_sessions.get(chat_id)
            
            if not spotify_manager or not spotify_manager.spotify:
                await context.bot.send_message(chat_id=chat_id, text="⚠️ Error: you must be logged in to Spotify first: \n<code>/loginspotify</code> ", parse_mode="HTML")
                return
            
            await context.bot.send_message(chat_id=chat_id, text="🔄 Adding YouTube playlist tracks to existing Spotify playlist...")
            
            try:
                titles = await asyncio.to_thread(spotytdl.main, url, second_url, "add_yt_to_spotify_playlist", None, spotify_manager.spotify)
                
                if titles:
                    await context.bot.send_message(chat_id=chat_id, text=f"✅ Migration completed! {len(titles)} videos processed.")
                else:
                    await context.bot.send_message(chat_id=chat_id, text="⚠️ No new tracks were added")
            
            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ An error has occurred: {str(e)}")
        
        # Case 2: Spotify → YouTube 
        elif url.startswith("https://open.spotify.com/playlist") and second_url.startswith("https://www.youtube.com/playlist"):
            manager = user_sessions.get(chat_id)
            
            if not manager or not manager.youtube:
                await context.bot.send_message(chat_id=chat_id, text="⚠️ Error: you must be logged in to YouTube: \n<code>/loginyoutube</code> ", parse_mode="HTML")
                return
            
            await context.bot.send_message(chat_id=chat_id, text="🔄 Adding songs to the existing YouTube playlist")

            try:
                titles = await asyncio.to_thread(spotytdl.main, url, second_url, "addtoplaylist", manager.youtube)

                if titles:
                    await context.bot.send_message(chat_id=chat_id, text=f"✅ Migration completed! {len(titles)} songs were processed.")
                else:
                    await context.bot.send_message(chat_id=chat_id, text="⚠️ It looks like the playlist is empty or there was a problem")

            except QuotaExceededException as e:
                await context.bot.send_message(chat_id=chat_id, text=f"⚠️ The YouTube API quota exceeded during the process! Even tho some songs were probably added✅ please login again with /loginyoutube to switch to other oauth credentials in order to keep adding songs to your playlists.")
                i[0] = (i[0] + 1) % len(CLIENT_SECRETS_FILE)
                if chat_id in user_sessions:
                    del user_sessions[chat_id]
                if i[0] >= len(CLIENT_SECRETS_FILE):
                    i[0] = 0
                    await context.bot.send_message(chat_id=chat_id, text=f"❌ All available OAuth accounts have exceeded their quota. Please try again in 24 hours.")
            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ An error has occured: {str(e)}, current oauth index: {i[0]}")
                i[0] = (i[0] + 1) % len(CLIENT_SECRETS_FILE)
                if i[0] < len(CLIENT_SECRETS_FILE):
                    await context.bot.send_message(chat_id=chat_id, text=f"Please, do the login again")   
                else:
                    await context.bot.send_message(chat_id=chat_id, text=f"❌ Impossible to migrate playlists at the moment, try in 24hrs")
        else:
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Invalid URL combination. Please provide compatible playlist URLs.")
        return
    

    # If the URL is from YouTube → Migrate to Spotify
    if url.startswith("https://www.youtube.com/playlist"):
        # Migration from YouTube to Spotify
        spotify_manager = spotify_sessions.get(chat_id)
        
        if not spotify_manager or not spotify_manager.spotify:
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Error: you must be logged in to Spotify first: \n<code>/loginspotify</code> ", parse_mode="HTML")
            return
        
        await context.bot.send_message(chat_id=chat_id, text="🔄 Migrating YouTube playlist to Spotify...")
        
        try:
            titles = await asyncio.to_thread(spotytdl.main, url, None, "migrate_yt_to_spotify", None, spotify_manager.spotify)
            
            if titles:
                await context.bot.send_message(chat_id=chat_id, text=f"✅ Migration completed! {len(titles)} videos processed.")
            else:
                await context.bot.send_message(chat_id=chat_id, text="⚠️ It looks like the playlist is empty or there was a problem")
        
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ An error has occurred: {str(e)}")
    
    # If the URL is from Spotify → Migrate to YouTube
    elif url.startswith("https://open.spotify.com/playlist"):
        manager = user_sessions.get(chat_id)
        
        if not manager or not manager.youtube:
            await context.bot.send_message(chat_id=chat_id, text="⚠️ Error: you must be logged in to YouTube: \n<code>/loginyoutube</code> ", parse_mode="HTML")
            return

        await context.bot.send_message(chat_id=chat_id, text="🔄 Creating a new YouTube playlist")

        try:
            titles = await asyncio.to_thread(spotytdl.main, url, None, "migrate_playlist", manager.youtube)

            if titles:
                await context.bot.send_message(chat_id=chat_id, text=f"✅ Migration completed!")
            else:
                await context.bot.send_message(chat_id=chat_id, text="⚠️ It looks like the playlist is empty or there was a problem")

        except QuotaExceededException as e:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ The YouTube API quota exceeded during the process! Even tho some songs were probably added✅ please login again with /loginyoutube to switch to other oauth credentials in order to keep adding songs to your playlists.")
            i[0] = (i[0] + 1) % len(CLIENT_SECRETS_FILE)
            if chat_id in user_sessions:
                del user_sessions[chat_id]
            if i[0] >= len(CLIENT_SECRETS_FILE):
                i[0] = 0
                await context.bot.send_message(chat_id=chat_id, text=f"❌ All available OAuth accounts have exceeded their quota. Please try again in 24 hours.")
        except Exception as e:
            await context.bot.send_message(chat_id=chat_id, text=f"❌ An error has occured: {str(e)}, current oauth index: {i[0]}")
            i[0] = (i[0] + 1) % len(CLIENT_SECRETS_FILE)
            if i[0] < len(CLIENT_SECRETS_FILE):
                await context.bot.send_message(chat_id=chat_id, text=f"Please, do the login again")   
            else:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ Impossible to migrate playlists at the moment, try in 24hrs")
    else:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Invalid URL. Please provide either a Spotify or YouTube playlist URL.")  


if __name__ == '__main__':
    
    i_value=[0]
    request = HTTPXRequest(
        http_version="1.1", 
        read_timeout=120.0,
        write_timeout=120.0,
        connect_timeout=120.0,
        pool_timeout=120.0,
        media_write_timeout=900.0,  
    )
    application = ApplicationBuilder().token(BOT_TOKEN).request(request).build()
    
    start_handler = CommandHandler('start', start) 
    
    dl_handler = CommandHandler('dl',sendSong)

    migratePl_handler = CommandHandler('migrate',partial(migratePlaylist, i=i_value))

    application.add_handler(start_handler)
    
    application.add_handler(dl_handler)
    
    application.add_handler(migratePl_handler)

    loginyt_handler = ConversationHandler(
    entry_points=[CommandHandler('loginyoutube', partial(login_command, i=i_value))],
    states={
        WAITING_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_auth_code)],
    },
    fallbacks=[],
    )

    loginspotify_handler = ConversationHandler(
    entry_points=[CommandHandler('loginspotify', login_spotify_command)],
    states={
        WAITING_CODE_SPOTIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_spotify_auth_code)],
    },
    fallbacks=[],
    )

    application.add_handler(loginyt_handler)
    application.add_handler(loginspotify_handler)
    
    print("Bot is running...")
    application.run_polling()