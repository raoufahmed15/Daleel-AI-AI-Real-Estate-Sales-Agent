"""Runtime configuration. Defaults keep the application in an empty local sandbox."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
# Swap for e.g. postgresql+psycopg://user:pw@host/db later (install the driver then).
DATABASE_URL = os.getenv("DALEEL_DATABASE_URL", f"sqlite:///{BASE_DIR / 'daleel-local.db'}")
APP_MODE = os.getenv("DALEEL_APP_MODE", "sandbox")
AUTO_SEED = os.getenv("DALEEL_AUTO_SEED", "0") == "1"
APP_VERSION = "0.1.0"
DEMO_NOTICE = (
    "Daleel AI is a local sandbox. No real messages, calls, or production CRM/payment/contract actions are performed."
)
