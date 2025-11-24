#!/usr/bin/env python3
"""
YoYoXcloud Premium Inboxer Bot - Main Entry Point
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add scr to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scr'))

from telegram_bot import YoYoXcloudBot

if __name__ == "__main__":
    bot = YoYoXcloudBot()
    bot.run()
