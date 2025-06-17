import itertools
import os

class APIKeyManager:
    def __init__(self):
        # Load keys from environment or fallback config
        keys_env = os.getenv("GOOGLE_API_KEYS", "")
        self.api_keys = [key.strip() for key in keys_env.split(",") if key.strip()]
        if not self.api_keys:
            raise Exception("No API keys found in environment!")

        self.keys_cycle = itertools.cycle(self.api_keys)  # round robin

    def get_key(self) -> str:
        return next(self.keys_cycle)
