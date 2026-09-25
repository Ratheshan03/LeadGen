import os
import json
import tempfile
from datetime import datetime

# Pull the cap from settings (which loads .env via python-dotenv). Reading from
# settings instead of a bare os.getenv at import time avoids a load-order bug
# where this module could be imported before .env was loaded, falling back to a
# wrong default (that produced the "9500/1000" cap mismatch).
try:
    from config.settings import API_REQUEST_CAP as _SETTINGS_CAP
except Exception:  # pragma: no cover - settings import should normally succeed
    _SETTINGS_CAP = int(os.getenv("API_REQUEST_CAP", "10500"))

# Absolute path to the single canonical quota file, pinned to apps/api/ so it is
# always written/read from the same place no matter what the current working
# directory is. Previously this was a relative path ("api_quota_usage.json"),
# which (a) wrote to the wrong dir when scripts ran from elsewhere and (b) left
# orphaned tmp* files behind when os.replace crossed directories.
_API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
QUOTA_FILE = os.path.join(_API_DIR, "api_quota_usage.json")

# Monthly request cap (Google Places spend ceiling).
MAX_MONTHLY_QUOTA = _SETTINGS_CAP


class QuotaManager:
    def __init__(self, max_requests=None):
        self.max_requests = max_requests if max_requests is not None else MAX_MONTHLY_QUOTA
        self.load_usage()

    def load_usage(self):
        if os.path.exists(QUOTA_FILE):
            try:
                with open(QUOTA_FILE, "r", encoding="utf-8") as f:
                    self.usage_data = json.load(f)
                # Guard against a partially written / malformed file.
                if not isinstance(self.usage_data, dict) or "count" not in self.usage_data:
                    raise ValueError("malformed quota file")
            except (json.JSONDecodeError, ValueError, OSError):
                self.usage_data = {"month": self.current_month(), "count": 0}
                self.save_usage()
        else:
            self.usage_data = {"month": self.current_month(), "count": 0}
            self.save_usage()

        if self.usage_data.get("month") != self.current_month():
            self.reset_usage()

    def current_month(self):
        return datetime.utcnow().strftime("%Y-%m")

    def increment(self):
        self.usage_data["count"] += 1
        self.save_usage()

    def save_usage(self):
        # Atomic write: write to a temp file IN THE SAME DIRECTORY as the target
        # (so os.replace is an atomic rename on the same filesystem, not a
        # cross-directory move), then replace. Clean up the temp file on failure
        # so we never leave stray tmp* files in apps/api/.
        target_dir = os.path.dirname(QUOTA_FILE)
        tempname = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", delete=False, dir=target_dir, prefix=".quota_", suffix=".tmp", encoding="utf-8"
            ) as tf:
                json.dump(self.usage_data, tf)
                tempname = tf.name
            os.replace(tempname, QUOTA_FILE)
        except Exception:
            # Best-effort cleanup; re-raise so callers know the write failed.
            if tempname and os.path.exists(tempname):
                try:
                    os.remove(tempname)
                except OSError:
                    pass
            raise

    def get_usage(self):
        return self.usage_data["count"]

    def remaining(self):
        return self.max_requests - self.usage_data["count"]

    def is_within_limit(self):
        return self.get_usage() < self.max_requests

    def reset_usage(self):
        self.usage_data = {"month": self.current_month(), "count": 0}
        self.save_usage()
