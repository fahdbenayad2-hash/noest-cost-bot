from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler

from bot.handlers import handler as conversation_handler
from bot.handlers import history
from bot.sheets_client import SheetsClient
from config import BOT_TOKEN, GOOGLE_CREDENTIALS_PATH, SPREADSHEET_ID, WEBHOOK_URL

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Bootstrap and run the bot."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Check your .env file.")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    sheets_client = None
    if SPREADSHEET_ID and os.path.isfile(GOOGLE_CREDENTIALS_PATH):
        try:
            sheets_client = SheetsClient(GOOGLE_CREDENTIALS_PATH, SPREADSHEET_ID)
            logger.info("Google Sheets client initialised.")
        except Exception as exc:
            logger.warning("Failed to initialise Sheets client: %s", exc)
    else:
        logger.warning(
            "SPREADSHEET_ID or credentials file missing — Sheets disabled."
        )

    app.bot_data["sheets_client"] = sheets_client

    app.add_handler(conversation_handler)
    app.add_handler(CommandHandler("history", history))

    if WEBHOOK_URL:
        port = int(os.getenv("PORT", "8443"))
        logger.info("Starting webhook on port %d ...", port)
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
        )
    else:
        logger.info("Starting polling ...")
        app.run_polling()


if __name__ == "__main__":
    load_dotenv()
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    main()
