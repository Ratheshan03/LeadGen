"""
Central configuration. Every setting comes from the project-root `.env` file
(see `.env.example`), with safe defaults. All paths are absolute, so the app
behaves the same no matter which folder it is started from.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip() or default)
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "").strip() or default)
    except ValueError:
        return default


# --- Folders -----------------------------------------------------------------
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = ROOT_DIR / "config"
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "").strip() or ROOT_DIR / "output")
STORAGE_DIR = ROOT_DIR / "storage"
LOG_DIR = ROOT_DIR / "logs"

# --- Google Places API -------------------------------------------------------
GOOGLE_API_KEYS = [k.strip() for k in os.getenv("GOOGLE_API_KEYS", "").split(",") if k.strip()]

# Hard monthly cap on Google requests. Crawls stop cleanly when it is reached.
API_REQUEST_CAP = _int("API_REQUEST_CAP", 10000)

# Used only for cost estimates. Text Search "Enterprise" SKU (the fields we
# request: phone, website, rating...) is USD 35 per 1,000 requests.
COST_PER_1000_REQUESTS_USD = _float("COST_PER_1000_REQUESTS_USD", 35.0)

# Seconds to wait before requesting the next results page (Google needs the
# page token to become valid).
PAGE_DELAY_SECONDS = _float("PAGE_DELAY_SECONDS", 2.0)
HTTP_TIMEOUT_SECONDS = _float("HTTP_TIMEOUT_SECONDS", 30.0)

# --- Storage -----------------------------------------------------------------
# "sqlite" (default, a local file - nothing to install) or "mongodb".
STORAGE = os.getenv("STORAGE", "sqlite").strip().lower() or "sqlite"
SQLITE_PATH = Path(os.getenv("SQLITE_PATH", "").strip() or STORAGE_DIR / "leadgen.db")
MONGO_DB_URI = os.getenv("MONGO_DB_URI", "").strip()
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "leadgen").strip() or "leadgen"

QUOTA_FILE = STORAGE_DIR / "api_quota_usage.json"

# --- Backend / clients -------------------------------------------------------
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1").strip() or "127.0.0.1"
BACKEND_PORT = _int("BACKEND_PORT", 8000)
BACKEND_API_URL = (os.getenv("BACKEND_API_URL", "").strip() or f"http://localhost:{BACKEND_PORT}").rstrip("/")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:8501").split(",") if o.strip()]

# --- Data build (New Zealand boundaries from Stats NZ) ------------------------
STATS_NZ_API_KEY = os.getenv("STATS_NZ_API_KEY", "").strip()

for _folder in (OUTPUT_DIR, STORAGE_DIR, LOG_DIR):
    _folder.mkdir(parents=True, exist_ok=True)
