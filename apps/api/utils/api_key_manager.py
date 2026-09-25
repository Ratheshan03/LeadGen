import itertools
import os
import random

class APIKeyManager:
    def __init__(self):
        # Load keys from environment or fallback config
        keys_env = os.getenv("GOOGLE_API_KEYS", "")
        self.api_keys = [key.strip() for key in keys_env.split(",") if key.strip()]
        
        if not self.api_keys:
            raise Exception("No API keys found in environment variable: GOOGLE_API_KEYS")

        # Shuffle keys to randomize initial key access for better distribution
        random.shuffle(self.api_keys)

        self.keys_cycle = itertools.cycle(self.api_keys)  # round robin
        self.current_key = next(self.keys_cycle)

    def get_key(self) -> str:
        return self.current_key

    def rotate_key(self) -> str:
        """
        Advance to the next API key in the round-robin cycle.

        Called when the current key hits a rate limit (HTTP 429) so the next
        request uses a different key. With a single key this is a no-op (the
        same key is returned), which is correct — there is nothing to rotate to.
        """
        self.current_key = next(self.keys_cycle)
        return self.current_key
