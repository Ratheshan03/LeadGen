import requests
import time
from utils.api_key_manager import APIKeyManager
from config.constants import (
    GOOGLE_PLACES_NEARBY_URL,
    GOOGLE_PLACE_DETAILS_URL,
    GOOGLE_PLACES_TEXT_URL,
    AU_REGIONS,
    REGION_COORDINATES,
    BUSINESS_CATEGORIES
)
from utils.quota_manager import QuotaManager

class GoogleMapsService:
    def __init__(self):
        self.key_manager = APIKeyManager()
        self.quota = QuotaManager()

    def _get_headers(self):
        return {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.key_manager.get_key(),
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types,places.id"
        }

    def _get_payload(self, location, place_type, radius=5000.0, page_token=None):
        latitude, longitude = map(float, location.split(","))

        payload = {
            "includedTypes": [place_type],
            "maxResultCount": 20,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": radius
                }
            }
        }

        if page_token:
            payload["pageToken"] = page_token

        return payload

    def search_places_nearby(self, location: str, place_type: str, radius: float = 5000.0):
        all_results = []
        next_page_token = None

        for _ in range(10):  # Max 10 pages per type/location (tune as needed)
            payload = self._get_payload(location, place_type, radius, next_page_token)
            headers = self._get_headers()

            response = requests.post(GOOGLE_PLACES_NEARBY_URL, json=payload, headers=headers)
            self.quota.increment()

            if response.status_code == 429:
                print("Rate limit hit. Rotating API key...")
                self.key_manager.rotate_key()
                continue

            if response.status_code != 200:
                print(f"Google API Error: {response.text}")
                break

            data = response.json()
            places = data.get("places") or data.get("results") or []
            all_results.extend(places)

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

            time.sleep(2)  # Small wait as per Google API best practices

        return all_results

    def get_place_details(self, place_id: str):
        url = f"{GOOGLE_PLACE_DETAILS_URL}/{place_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.key_manager.get_key(),
            "X-Goog-FieldMask": "id,displayName,formattedAddress,website,formattedPhoneNumber"
        }

        response = requests.get(url, headers=headers)
        self.quota.increment()

        if response.status_code != 200:
            raise Exception(f"Google API Error: {response.text}")

        return response.json()

    # 🚀 Automated Crawl: Full Country Sweep
    def crawl_all_regions(self, dry_run: bool = False):
        results = []

        for state, cities in AU_REGIONS.items():
            for city in cities:
                print(f"\n🚩 Scanning {city}, {state}")
                location = REGION_COORDINATES.get(city)

                if not location:
                    print(f"No coordinates found for {city}, skipping...")
                    continue

                for category, place_types in BUSINESS_CATEGORIES.items():
                    for place_type in place_types:
                        print(f"🔍 Checking: {place_type} in {city}")

                        if dry_run:
                            # Skip actual search, just simulate entry
                            results.append({
                                "place": {
                                    "displayName": {"text": f"{place_type} example in {city}"},
                                    "formattedAddress": f"Example Address, {city}",
                                    "types": [place_type]
                                },
                                "state": state,
                                "region": city,
                                "category": category,
                                "business_type": place_type
                            })
                            continue

                        try:
                            places = self.search_places_nearby(location, place_type)
                            for place in places:
                                results.append({
                                    "place": place,
                                    "state": state,
                                    "region": city,
                                    "category": category,
                                    "business_type": place_type
                                })
                            print(f"Retrieved {len(places)} places.")
                        except Exception as e:
                            print(f"Error while fetching {place_type} in {city}: {str(e)}")

        return results


    def text_search_places(self, text_query: str, location_bias: dict = None, max_results: int = 20):
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.key_manager.get_key(),
            "X-Goog-FieldMask": (
                "places.displayName,places.formattedAddress,places.websiteUri,"
                "places.internationalPhoneNumber,places.types,places.rating,places.id"
            )
        }

        all_results = []
        page_token = None
        pages_fetched = 0

        for _ in range(10):  # Google only supports up to 10 pages
            if page_token:
                payload = {"pageToken": page_token}
            else:
                payload = {
                    "textQuery": text_query,
                    "maxResultCount": max_results
                }
                if location_bias:
                    payload["locationBias"] = location_bias

            response = requests.post(GOOGLE_PLACES_TEXT_URL, json=payload, headers=headers)
            self.quota.increment()

            if response.status_code == 429:
                print("Rate limit hit. Rotating API key...")
                self.key_manager.rotate_key()
                time.sleep(1)
                continue

            if response.status_code != 200:
                print(f"Google Text Search API Error: {response.status_code}, {response.text}")
                break

            data = response.json()
            results = data.get("places", [])
            all_results.extend(results)
            pages_fetched += 1

            page_token = data.get("nextPageToken")
            if not page_token:
                break

            time.sleep(1.5)  # Per Google API best practice

        return {
            "results": all_results,
            "pages_fetched": pages_fetched,
            "total_returned": len(all_results)
        }

