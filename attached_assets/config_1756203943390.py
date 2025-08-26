# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN not found!")

PREFIX = "!"
DB_PATH = os.getenv("DB_PATH", "ticket_bot.db")
