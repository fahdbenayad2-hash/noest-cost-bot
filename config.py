import json
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)


BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID", "")

_creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
if _creds_path:
    p = Path(_creds_path)
    GOOGLE_CREDENTIALS_PATH: str = str(p.resolve() if p.is_absolute() else BASE_DIR / p)
else:
    GOOGLE_CREDENTIALS_PATH: str = ""

_creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
GOOGLE_CREDENTIALS_JSON: str = _creds_json

WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
