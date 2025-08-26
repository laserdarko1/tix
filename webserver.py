# webserver.py
from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "Discord Ticket Bot is running!"

@app.route("/health")
def health():
    return {"status": "healthy", "service": "discord-ticket-bot"}

def start_webserver():
    def run():
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port, debug=False)
    
    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()
