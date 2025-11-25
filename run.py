#!/usr/bin/env python3
import os
import sys

# Set environment variables BEFORE importing bot
os.environ['TELEGRAM_BOT_TOKEN'] = '8542557681:AAF42OpFf2nHY4Rl6l0jkjRUDI9wb-DAcus'
os.environ['ADMIN_USERNAME'] = 'AraboMardelli'
os.environ['ADMIN_PASSWORD'] = 'AraboKing336'

# Now import and run the bot
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scr'))
from telegram_bot import YoYoXcloudBot

if __name__ == "__main__":
    bot = YoYoXcloudBot()
    bot.run()
