#!/usr/bin/env python3
"""
YoYoXcloud Premium Inboxer Bot - Main Entry Point
"""
import sys
import os

# SET ENV VARS FIRST - BEFORE ANYTHING ELSE!
os.environ['TELEGRAM_BOT_TOKEN'] = '8542557681:AAF42OpFf2nHY4Rl6l0jkjRUDI9wb-DAcus'
os.environ['ADMIN_USERNAME'] = 'AraboMardelli'
os.environ['ADMIN_PASSWORD'] = 'AraboKing336'

# NOW load dotenv
from dotenv import load_dotenv
load_dotenv()

# Add scr to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scr'))

from telegram_bot import YoYoXcloudBot

if __name__ == "__main__":
    bot = YoYoXcloudBot()
    bot.run()
