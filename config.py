import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)


BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID", "")
_creds_env = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
GOOGLE_CREDENTIALS_PATH: str = str(
    Path(_creds_env).resolve() if Path(_creds_env).is_absolute() else BASE_DIR / _creds_env
)
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
