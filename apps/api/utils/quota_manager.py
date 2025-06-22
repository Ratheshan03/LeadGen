import os
import json
from datetime import datetime
import tempfile

QUOTA_FILE = "api_quota_usage.json"
MAX_MONTHLY_QUOTA = 900  # Cap below Google’s free tier

class QuotaManager:
    def __init__(self, max_requests=MAX_MONTHLY_QUOTA):
        self.max_requests = max_requests
        self.load_usage()

    def load_usage(self):
        if os.path.exists(QUOTA_FILE):
            with open(QUOTA_FILE, "r") as f:
                self.usage_data = json.load(f)
        else:
            self.usage_data = {"month": self.current_month(), "count": 0}
            self.save_usage()

        if self.usage_data["month"] != self.current_month():
            self.reset_usage()

    def current_month(self):
        return datetime.utcnow().strftime("%Y-%m")

    def increment(self):
        self.usage_data["count"] += 1
        self.save_usage()

    def save_usage(self):
        # Atomic write to avoid data loss
        with tempfile.NamedTemporaryFile("w", delete=False, dir=".") as tf:
            json.dump(self.usage_data, tf)
            tempname = tf.name
        os.replace(tempname, QUOTA_FILE)

    def get_usage(self):
        return self.usage_data["count"]

    def remaining(self):
        return self.max_requests - self.usage_data["count"]

    def is_within_limit(self):
        return self.get_usage() < self.max_requests

    def reset_usage(self):
        self.usage_data = {"month": self.current_month(), "count": 0}
        self.save_usage()
