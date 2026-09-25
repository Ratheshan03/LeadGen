"""
LeadGen backend.

Start it with   python -m backend      (or start_backend.bat on Windows)
API docs at     http://localhost:8000/docs
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import api
from backend.config import settings
from backend.crawler.quota import QuotaManager
from backend.jobs import JobManager
from backend.logging_setup import setup_logging
from backend.storage import get_store

log = logging.getLogger("leadgen")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    store = get_store()  # fail fast with a clear message if storage is misconfigured
    api.quota = QuotaManager()
    api.jobs = JobManager(api.quota)
    log.info("Storage: %s (%s leads)", store.describe(), f"{store.count():,}")
    log.info("Google API keys configured: %s | monthly cap: %s", len(settings.GOOGLE_API_KEYS), f"{settings.API_REQUEST_CAP:,}")
    if not settings.GOOGLE_API_KEYS:
        log.warning("No GOOGLE_API_KEYS in .env - crawls will fail until you add one.")
    yield


app = FastAPI(title="LeadGen API", version="2.0.0",
              description="Business lead crawler for Australia and New Zealand (Google Places).", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_methods=["GET", "POST"],
                   allow_headers=["*"])
app.include_router(api.router)
