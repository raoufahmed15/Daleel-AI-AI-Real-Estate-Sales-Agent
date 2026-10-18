"""Runtime configuration. Everything is optional; defaults give a local SQLite demo."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
# Swap for e.g. postgresql+psycopg://user:pw@host/db later (install the driver then).
DATABASE_URL = os.getenv("DALEEL_DATABASE_URL", f"sqlite:///{BASE_DIR / 'daleel.db'}")
APP_MODE = os.getenv("DALEEL_APP_MODE", "demo")
AUTO_SEED = os.getenv("DALEEL_AUTO_SEED", "1") == "1"
APP_VERSION = "0.1.0"
DEMO_NOTICE = (
    "Daleel AI is a DEMO AI sales assistant. All data is synthetic, bookings are simulated, "
    "and no real messages, calls, or CRM/payment/contract actions are performed."
)
