"""
Storage factory. SQLite (a local file) is the default; set STORAGE=mongodb in
.env to use a MongoDB server or Atlas cluster instead.
"""
from __future__ import annotations

import threading

from backend.config import settings
from backend.storage.base import INSERTED, UNCHANGED, UPDATED, LeadFilter, LeadStore

__all__ = ["get_store", "reset_store", "LeadStore", "LeadFilter", "INSERTED", "UPDATED", "UNCHANGED"]

_store: LeadStore | None = None
_lock = threading.Lock()


def get_store() -> LeadStore:
    global _store
    with _lock:
        if _store is None:
            if settings.STORAGE == "mongodb":
                from backend.storage.mongo_store import MongoLeadStore
                _store = MongoLeadStore(settings.MONGO_DB_URI, settings.MONGO_DB_NAME)
            elif settings.STORAGE == "sqlite":
                from backend.storage.sqlite_store import SQLiteLeadStore
                _store = SQLiteLeadStore(settings.SQLITE_PATH)
            else:
                raise RuntimeError(f"Unknown STORAGE '{settings.STORAGE}' in .env (use 'sqlite' or 'mongodb').")
        return _store


def reset_store(store: LeadStore | None = None) -> None:
    """Replace the active store (used by tests)."""
    global _store
    with _lock:
        _store = store
