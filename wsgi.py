"""WSGI entry point for PythonAnywhere deployment."""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

os.environ.setdefault("BOT_TOKEN", "")
os.environ.setdefault("SPREADSHEET_ID", "")
os.environ.setdefault("GOOGLE_CREDENTIALS_PATH", str(BASE_DIR / "credentials.json"))

from telegram import Update
from telegram.ext import Application, CommandHandler
from flask import Flask, request

from bot.handlers import handler as conversation_handler
from bot.handlers import history
from bot.sheets_client import SheetsClient
from config import BOT_TOKEN, GOOGLE_CREDENTIALS_JSON, GOOGLE_CREDENTIALS_PATH, SPREADSHEET_ID

# Build app
application = Application.builder().token(BOT_TOKEN).updater(None).build()

# Init Sheets
if SPREADSHEET_ID:
    try:
        creds = GOOGLE_CREDENTIALS_JSON or (
            open(GOOGLE_CREDENTIALS_PATH, encoding="utf-8").read()
            if GOOGLE_CREDENTIALS_PATH and os.path.isfile(GOOGLE_CREDENTIALS_PATH)
            else ""
        )
        if creds:
            application.bot_data["sheets_client"] = SheetsClient(creds, SPREADSHEET_ID)
    except Exception:
        pass

application.add_handler(conversation_handler)
application.add_handler(CommandHandler("history", history))
application.initialize()

# Flask app
flask_app = Flask(__name__)


@flask_app.route("/")
def index():
    return "Noest Cost Bot running ✅"


@flask_app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.process_update(update)
    return "OK", 200


@flask_app.route("/set_webhook")
def set_webhook():
    url = f"https://{request.host}/{BOT_TOKEN}"
    application.bot.set_webhook(url=url)
    return f"Webhook set ✅ → {url}", 200


app = flask_app
