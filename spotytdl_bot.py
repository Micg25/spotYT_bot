import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from telegram.request import HTTPXRequest
import spotytdl
import os
from telegram.error import TimedOut, TelegramError
import asyncio
import httpx
BOT_TOKEN="" #insert your BOT TOKEN
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="use the command <code>/dl {spotify/youtube link}</code>  to start downloading tracks and albums ",parse_mode="HTML")


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
                        break  # Errore irreversibile, esce
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
                    break  # Errore irreversibile, esce
                except Exception as e:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error while sending: '{titles}', {e}")
                    break
    except RuntimeError as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{str(e)}")
        return
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Done",parse_mode="HTML")
if __name__ == '__main__':
    
    request = HTTPXRequest(
        http_version="2",
        read_timeout=60.0,
        write_timeout=60.0,
        connect_timeout=60.0,
        pool_timeout=60.0,
        media_write_timeout=900.0,  # timeout specifico per l'invio di file
    )
    application = ApplicationBuilder().token(BOT_TOKEN).request(request).build()
    
    start_handler = CommandHandler('start', start) 
    
    dl_handler = CommandHandler('dl',sendSong)


    application.add_handler(start_handler)
    
    application.add_handler(dl_handler)
    
    application.run_polling()