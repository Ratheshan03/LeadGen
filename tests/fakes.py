"""A fake Google Places API for tests - no network, no cost."""
from __future__ import annotations

import itertools


def make_place(pid: str, lat: float, lng: float, name: str | None = None, types=("cafe",), **extra) -> dict:
    return {
        "id": pid, "displayName": {"text": name or f"Business {pid}"},
        "formattedAddress": f"{pid} Test St", "location": {"latitude": lat, "longitude": lng},
        "types": list(types), "primaryType": types[0], "internationalPhoneNumber": "+61 8 0000 0000",
        "nationalPhoneNumber": "(08) 0000 0000", "websiteUri": f"https://{pid}.example", "rating": 4.2,
        "userRatingCount": 10, "businessStatus": "OPERATIONAL", "googleMapsUri": f"https://maps.google.com/?cid={pid}",
        "regularOpeningHours": {"weekdayDescriptions": ["Monday: 9:00 AM - 5:00 PM"]}, **extra,
    }


class FakeResponse:
    def __init__(self, status: int, payload: dict | None = None):
        self.status_code = status
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeGoogle:
    """
    Stands in for requests.Session.

    places:    {query: [place, ...]} returned (20 per page) for Text Search, regardless of tile;
               the crawler's own geo-filter must drop the ones outside the tile.
    saturate:  every Text Search returns 3 full pages of in-tile results (Google's 60 cap).
    statuses:  HTTP status codes to return first (e.g. [429] or [403]).
    """

    def __init__(self, places: dict | None = None, saturate: bool = False, statuses=None, nearby: dict | None = None):
        self.places = places or {}
        self.nearby = nearby or {}
        self.saturate = saturate
        self.statuses = list(statuses or [])
        self.calls: list[dict] = []
        self._ids = itertools.count(1)

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json, "key": headers.get("X-Goog-Api-Key")})
        if self.statuses:
            status = self.statuses.pop(0)
            return FakeResponse(status, {"error": {"status": "TEST", "message": f"status {status}"}})
        if url.endswith(":searchNearby"):
            return FakeResponse(200, {"places": self.nearby.get(json["includedTypes"][0], [])})
        page = int((json.get("pageToken") or "p0")[1:])
        if self.saturate:
            rect = json["locationRestriction"]["rectangle"]
            lat_lo, lat_hi = rect["low"]["latitude"], rect["high"]["latitude"]
            lon_lo, lon_hi = rect["low"]["longitude"], rect["high"]["longitude"]
            items = []
            for i in range(20):
                f = (i + 1) / 22
                n = next(self._ids)
                items.append(make_place(f"s{n}", lat_lo + (lat_hi - lat_lo) * f, lon_lo + (lon_hi - lon_lo) * f))
            payload = {"places": items}
            if page < 2:
                payload["nextPageToken"] = f"p{page + 1}"
            return FakeResponse(200, payload)
        items = self.places.get(json["textQuery"], [])
        chunk = items[page * 20:(page + 1) * 20]
        payload = {"places": chunk}
        if (page + 1) * 20 < len(items):
            payload["nextPageToken"] = f"p{page + 1}"
        return FakeResponse(200, payload)
