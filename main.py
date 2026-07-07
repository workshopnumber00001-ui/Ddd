import sys
import os

# सबसे जरूरी लाइन - यह Python को बताती है कि फाइलें कहाँ हैं
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pyromod.listen
from config import Config
from pyrogram import Client, idle
import asyncio
import threading
from flask import Flask
from logger import LOGGER
from modules.retasks import recover_incomplete_batches
from modules.scheduler import start_daily_schedulers

# Flask Web Server (Render की Health Check के लिए)
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running successfully!"

# Flask को अलग Thread में चलाना
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# Telegram Bot Main Function
async def main():
    bot = Client(
        "Bot",
        bot_token=Config.BOT_TOKEN,
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        sleep_threshold=30,
        plugins=dict(root="plugins"),
        workers=1000,
    )
    
    await bot.start()
    bot_info = await bot.get_me()
    LOGGER.info(f"<--- @{bot_info.username} Started --->")
    
    # Background Tasks
    asyncio.create_task(recover_incomplete_batches(bot))
    asyncio.create_task(start_daily_schedulers(bot))
    LOGGER.info("Daily update schedulers started")
    
    await idle()

if __name__ == "__main__":
    # Flask Web Server Thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Bot का Async Loop
    asyncio.get_event_loop().run_until_complete(main())
    LOGGER.info("<--- Bot Stopped --->")
