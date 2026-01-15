import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from telegram.request import HTTPXRequest
import spotytdl
import os
from telegram.error import TimedOut, TelegramError
import asyncio
import httpx
from telegram.ext import ConversationHandler, MessageHandler, filters
from Youtube_auth import YouTubeManager
BOT_TOKEN=""

user_sessions = {}


WAITING_CODE = 1

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    manager = YouTubeManager()
    user_sessions[chat_id] = manager
    
    auth_url = manager.get_auth_url()
    
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


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="1. use the command <code>/dl {spotify/youtube link}</code>  to start downloading tracks and albums " \
    "\n 2. use the command <code>/spotifytoyt {spotify_playlist_link}</code> to migrate your spotify playlist to your youtube and youtube music account! \n3. before " \
    "using the <code>/spotifytoyt</code> command you must login by using the <code>/login</code> command ",parse_mode="HTML")


async def sendSong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(context.args[0])
    await context.bot.send_message(chat_id=update.effective_chat.id, text="The download is starting...",parse_mode="HTML")
    try:
        titles=spotytdl.main(context.args[0])
        if (titles is None):
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error while downloading: '{title}'")
            return
        print("TITLES:", titles)
        if(type(titles)==list):
            for title in titles:
                n_try=0
                print("trying to send: ",title)
                while True:
                    if(n_try>5):
                        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error while sending: {title}")
                        break
                    try:
                        n_try+=1
                        await context.bot.send_audio(chat_id=update.effective_chat.id,audio=open(title+".m4a","rb"))
                        os.remove(title+".m4a")
                        break
                    except TimedOut:
                        print(f"⏱ Timeout while sending: '{title}', trying again...")
                        await asyncio.sleep(3)  
                    except TelegramError as e:
                        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error while sending: '{title}, {e}'")
                        break  
                    except Exception as e:
                        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error while sending: {title}, {e}")
                        break
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="The download of the song is almost done...",parse_mode="HTML")
            while True:
                n_try=0
                if(n_try>2):
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error while sending: {titles}")
                    break
                try:
                    n_try+=1
                    await context.bot.send_audio(chat_id=update.effective_chat.id,audio=open(titles+".m4a","rb"))
                    os.remove(titles+".m4a")
                    break
                except TimedOut:
                    print(f"Timeout while sending: '{titles}', trying again...")
                    await asyncio.sleep(3) 
                except TelegramError as e:
                    print(f"Error while sending: '{titles}'")
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error while sending: '{titles}', {e}")
                    break  
                except Exception as e:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error while sending: '{titles}', {e}")
                    break
    except RuntimeError as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{str(e)}")
        return
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Done",parse_mode="HTML")
    
async def migratePlaylist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    manager = user_sessions.get(chat_id)

    if not manager or not manager.youtube:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Error: you must be logged in: \n<code>/login</code> ")
        return

    if not context.args:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ You must insert a spotify link Example:\n<code>/spotifytoyt https://open.spotify.com/playlist/...</code>", parse_mode="HTML")
        return

    await context.bot.send_message(chat_id=chat_id, text="🔄 Creating the playlist")
    titles=spotytdl.main(context.args[0],"migrate",manager.youtube)
    try:
        if titles:
                await context.bot.send_message(chat_id=chat_id, text=f"✅ Migration completed {len(titles)} songs were added.")
        else:
            await context.bot.send_message(chat_id=chat_id, text="⚠️ It looks like the playlist is empty or there was a problem")

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ An error has occured {str(e)}")


if __name__ == '__main__':
    
    request = HTTPXRequest(
        http_version="2",
        read_timeout=60.0,
        write_timeout=60.0,
        connect_timeout=60.0,
        pool_timeout=60.0,
        media_write_timeout=900.0,  
    )
    application = ApplicationBuilder().token(BOT_TOKEN).request(request).build()
    
    start_handler = CommandHandler('start', start) 
    
    dl_handler = CommandHandler('dl',sendSong)

    migratePl_handler = CommandHandler('spotifytoyt',migratePlaylist)

    application.add_handler(start_handler)
    
    application.add_handler(dl_handler)
    
    application.add_handler(migratePl_handler)

    login_handler = ConversationHandler(
    entry_points=[CommandHandler('login', login_command)],
    states={
        WAITING_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_auth_code)],
    },
    fallbacks=[],
    )

    application.add_handler(login_handler)
    
    application.run_polling()