"""
Google Places API (New) client: Text Search and Nearby Search.

Text Search behaviour is the same as LeadGen has always used:
  * up to 3 pages of 20 results (Google's maximum of 60 per query)
  * results are kept only if strictly inside the tile rectangle
  * paging stops on an empty page, on a page with nothing inside the tile,
    or when there is no next page
  * the monthly quota is checked before every request
"""
from __future__ import annotations

import itertools
import logging
import random
import threading
import time

import requests
from shapely.geometry import Point, box

from backend.config import settings
from backend.crawler.quota import QuotaManager

log = logging.getLogger("leadgen.places")

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
NEARBY_SEARCH_URL = "https://places.googleapis.com/v1/places:searchNearby"

# All of these are billed at the Text/Nearby Search "Enterprise" rate, which
# the crawler already paid for phone/website/rating - the rest cost nothing extra.
PLACE_FIELDS = (
    "id", "displayName", "formattedAddress", "websiteUri", "internationalPhoneNumber",
    "nationalPhoneNumber", "types", "primaryType", "rating", "userRatingCount",
    "regularOpeningHours", "businessStatus", "location", "googleMapsUri",
)
TEXT_FIELD_MASK = ",".join(f"places.{f}" for f in PLACE_FIELDS) + ",nextPageToken"
NEARBY_FIELD_MASK = ",".join(f"places.{f}" for f in PLACE_FIELDS)

MAX_PAGES = 3          # Google returns at most 60 results (3 x 20) per query
MAX_RETRIES = 3        # per request, for rate limits / server errors


class PlacesError(RuntimeError):
    """A problem that makes further requests pointless (bad key, billing off...)."""


class APIKeyManager:
    """Round-robin over GOOGLE_API_KEYS; rotates when a key is rate limited."""

    def __init__(self, keys: list[str] | None = None):
        self.keys = list(keys if keys is not None else settings.GOOGLE_API_KEYS)
        if not self.keys:
            raise PlacesError("No Google API key configured. Add GOOGLE_API_KEYS=your-key to the .env file.")
        random.shuffle(self.keys)
        self._cycle = itertools.cycle(self.keys)
        self._lock = threading.Lock()
        self.current = next(self._cycle)

    def get_key(self) -> str:
        return self.current

    def rotate_key(self) -> str:
        with self._lock:
            self.current = next(self._cycle)
            return self.current


def _error_message(response: requests.Response) -> str:
    try:
        err = response.json().get("error", {})
        return f"{err.get('status', response.status_code)}: {err.get('message', '')}".strip()
    except ValueError:
        return f"HTTP {response.status_code}"


class PlacesClient:
    def __init__(self, keys: list[str] | None = None, quota: QuotaManager | None = None,
                 session: requests.Session | None = None, page_delay: float | None = None):
        self.keys = APIKeyManager(keys)
        self.quota = quota or QuotaManager()
        self.session = session or requests.Session()
        self.page_delay = settings.PAGE_DELAY_SECONDS if page_delay is None else page_delay

    # ------------------------------------------------------------------ core
    def _post(self, url: str, payload: dict, field_mask: str) -> tuple[dict | None, int, bool]:
        """
        POST with quota guard, key rotation on 429 and retries on 5xx.
        Returns (json or None, requests_made, quota_exceeded).
        """
        made = 0
        for attempt in range(MAX_RETRIES + 1):
            if not self.quota.is_within_limit():
                log.warning("Monthly request cap reached (%s/%s) - stopping to protect your budget.",
                            self.quota.used, self.quota.max_requests)
                return None, made, True
            headers = {"Content-Type": "application/json", "X-Goog-Api-Key": self.keys.get_key(),
                       "X-Goog-FieldMask": field_mask}
            try:
                response = self.session.post(url, json=payload, headers=headers, timeout=settings.HTTP_TIMEOUT_SECONDS)
            except requests.RequestException as exc:
                made += 1
                self.quota.increment()
                log.warning("Network error talking to Google (%s); retrying.", exc.__class__.__name__)
                time.sleep(2 * (attempt + 1))
                continue
            made += 1
            self.quota.increment()

            if response.status_code == 200:
                return response.json(), made, False
            if response.status_code == 429:
                log.warning("Rate limited by Google - switching API key and retrying.")
                self.keys.rotate_key()
                time.sleep(1.5 * (attempt + 1))
                continue
            if response.status_code >= 500:
                log.warning("Google server error (%s); retrying.", response.status_code)
                time.sleep(2 * (attempt + 1))
                continue
            message = _error_message(response)
            if response.status_code in (401, 403):
                raise PlacesError(
                    f"Google rejected the API key ({message}). Check GOOGLE_API_KEYS in .env, that "
                    "'Places API (New)' is enabled and billing is active in Google Cloud."
                )
            log.error("Google API error %s", message)
            return None, made, False
        log.error("Giving up on this request after %s attempts.", MAX_RETRIES + 1)
        return None, made, False

    # ----------------------------------------------------------- text search
    def text_search(self, query: str, tile: dict, page_size: int = 20) -> dict:
        """
        Search one tile for one query. Returns
        {"results", "pages_fetched", "requests_made", "quota_exceeded"}.
        """
        low, high = tile["low"], tile["high"]
        base = {"textQuery": query, "pageSize": page_size,
                "locationRestriction": {"rectangle": {"low": low, "high": high}}}
        bounds = box(low["longitude"], low["latitude"], high["longitude"], high["latitude"])

        found: dict[str, dict] = {}
        pages_fetched = requests_made = 0
        quota_exceeded = False
        page_token = None
        for _ in range(MAX_PAGES):
            payload = {**base, "pageToken": page_token} if page_token else base
            data, made, quota_exceeded = self._post(TEXT_SEARCH_URL, payload, TEXT_FIELD_MASK)
            requests_made += made
            if data is None:
                break
            places = data.get("places", [])
            if not places:
                break
            inside = []
            for p in places:
                loc = p.get("location") or {}
                if "latitude" in loc and "longitude" in loc and bounds.contains(Point(loc["longitude"], loc["latitude"])):
                    inside.append(p)
            if not inside:
                break
            for p in inside:
                if "id" in p:
                    found[p["id"]] = p
            pages_fetched += 1
            page_token = data.get("nextPageToken")
            if not page_token:
                break
            time.sleep(self.page_delay)
        return {"results": list(found.values()), "pages_fetched": pages_fetched,
                "requests_made": requests_made, "quota_exceeded": quota_exceeded}

    # --------------------------------------------------------- nearby search
    def nearby_search(self, place_type: str, lat: float, lng: float, radius_m: float = 5000) -> dict:
        """Up to 20 places of one type within a circle (Google's Nearby Search limit)."""
        payload = {
            "includedTypes": [place_type], "maxResultCount": 20,
            "locationRestriction": {"circle": {"center": {"latitude": lat, "longitude": lng},
                                               "radius": float(min(max(radius_m, 1), 50000))}},
        }
        data, made, quota_exceeded = self._post(NEARBY_SEARCH_URL, payload, NEARBY_FIELD_MASK)
        places = (data or {}).get("places", [])
        return {"results": [p for p in places if "id" in p], "pages_fetched": 1 if places else 0,
                "requests_made": made, "quota_exceeded": quota_exceeded}


_STATUS_LABELS = {
    "OPERATIONAL": "Operational",
    "CLOSED_TEMPORARILY": "Temporarily closed",
    "CLOSED_PERMANENTLY": "Permanently closed",
}


def parse_place(place: dict) -> dict:
    """Google place JSON -> LeadGen lead fields (location labels added later)."""
    loc = place.get("location") or {}
    return {
        "place_id": place.get("id"),
        "name": (place.get("displayName") or {}).get("text"),
        "address": place.get("formattedAddress"),
        "phone": place.get("internationalPhoneNumber"),
        "phone_local": place.get("nationalPhoneNumber"),
        "website": place.get("websiteUri"),
        "google_maps_url": place.get("googleMapsUri"),
        "rating": place.get("rating"),
        "review_count": place.get("userRatingCount"),
        "business_status": _STATUS_LABELS.get(place.get("businessStatus"), place.get("businessStatus")),
        "primary_type": place.get("primaryType"),
        "types": list(place.get("types") or []),
        "opening_hours": list((place.get("regularOpeningHours") or {}).get("weekdayDescriptions") or []),
        "latitude": loc.get("latitude"),
        "longitude": loc.get("longitude"),
    }
