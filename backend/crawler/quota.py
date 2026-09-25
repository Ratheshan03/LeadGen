"""
Monthly Google request counter with a hard cap (API_REQUEST_CAP in .env).

Every request is counted before the next one is allowed; when the cap is
reached, crawls stop cleanly and report partial results. The count resets
automatically at the start of each month (UTC).
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

from backend.config import settings


class QuotaManager:
    def __init__(self, path: Path | None = None, max_requests: int | None = None):
        self.path = Path(path or settings.QUOTA_FILE)
        self.max_requests = max_requests if max_requests is not None else settings.API_REQUEST_CAP
        self._lock = threading.Lock()
        self.usage = self._load()

    @staticmethod
    def current_month() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("count"), int):
                raise ValueError
        except (OSError, ValueError):
            data = {"month": self.current_month(), "count": 0}
        if data.get("month") != self.current_month():
            data = {"month": self.current_month(), "count": 0}
        return data

    def _save(self) -> None:
        # Atomic write: temp file in the same folder, then rename over the target.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".quota_", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.usage, f)
            os.replace(tmp, self.path)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def _roll_month(self) -> None:
        if self.usage.get("month") != self.current_month():
            self.usage = {"month": self.current_month(), "count": 0}

    def increment(self, n: int = 1) -> None:
        with self._lock:
            self._roll_month()
            self.usage["count"] += n
            self._save()

    @property
    def used(self) -> int:
        with self._lock:
            self._roll_month()
            return self.usage["count"]

    @property
    def remaining(self) -> int:
        return max(0, self.max_requests - self.used)

    def is_within_limit(self) -> bool:
        return self.used < self.max_requests

    def status(self) -> dict:
        return {"month": self.current_month(), "used": self.used, "cap": self.max_requests, "remaining": self.remaining}
