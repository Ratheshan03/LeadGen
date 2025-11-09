import requests
import time
import json
from shapely.geometry import box, Point 
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

    # Places Nearby Search API
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
    

    # Places Details API 
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


    # Text Search API
    def text_search_places(self, text_query: str, location_bias: dict = None, max_results: int = 20):
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.key_manager.get_key(),
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,places.websiteUri,"
                "places.internationalPhoneNumber,places.types,places.rating,"
                "places.location,places.googleMapsUri,nextPageToken"
            )
        }

        all_results = []
        page_token = None
        pages_fetched = 0
        requests_made = 0

        # prepare base payload ONCE
        base_payload = {
            "textQuery": text_query,
            "pageSize": max_results
        }
        if location_bias and "rectangle" in location_bias:
            base_payload["locationRestriction"] = location_bias
        else:
            print("⚠️ No location restriction provided. Skipping geo-filtering.")

        # Multiple pages handling - capped at 20 (unchanged)
        for _ in range(20):
            if page_token:
                payload = {**base_payload, "pageToken": page_token}
                print(f"\n🔄 Fetching NEXT page {pages_fetched + 1} for '{text_query}'")
            else:
                payload = base_payload.copy()
                if "locationRestriction" in payload:  # ✅ correct key
                    print(f"\n📍 First page search for '{text_query}' with location restriction")
                else:
                    print(f"\n📍 First page search for '{text_query}' WITHOUT location restriction")

            # ---- Perform request (with quota + retry handling) ----
            response = requests.post(GOOGLE_PLACES_TEXT_URL, json=payload, headers=headers)
            requests_made += 1
            self.quota.increment()

            if response.status_code == 429:
                print("🚫 Rate limit hit. Rotating API key...")
                self.key_manager.rotate_key()
                time.sleep(1.5)
                # retry next loop iteration using the new key
                continue

            if response.status_code != 200:
                print(f"❌ Google API Error: {response.status_code} | {response.text}")
                break

            data = response.json()
            results = data.get("places", [])
            print(f"📊 Page {pages_fetched + 1} results: {len(results)} places found")

            if not results:
                print("⛔ Empty page returned. Stopping further requests to save quota.")
                break

            # Geo-filter strictly inside the tile rectangle
            if location_bias and "rectangle" in location_bias:
                low = location_bias["rectangle"]["low"]
                high = location_bias["rectangle"]["high"]
                bounds_polygon = box(low["longitude"], low["latitude"], high["longitude"], high["latitude"])

                filtered_results = []
                for place in results:
                    loc = place.get("location", {})
                    if not loc or "longitude" not in loc or "latitude" not in loc:
                        print("⚠️ Skipping place: Missing or malformed location")
                        continue
                    point = Point(loc["longitude"], loc["latitude"])
                    if bounds_polygon.contains(point):
                        filtered_results.append(place)

                print(f"🌐 Geo-filtered: {len(filtered_results)} / {len(results)} retained inside bounds")
                results = filtered_results
            else:
                print("⚠️ No location restriction provided. Skipping geo-filtering.")

            
            # After geo-filtering
            print(f"✅ Page {pages_fetched + 1} fetched: {len(results)} filtered results")

            if not results:
                print("⛔ No results after geo-filtering. Stopping further requests.")
                break

            token = data.get("nextPageToken")

            print(f"✅ Page {pages_fetched + 1} fetched: {len(results)} filtered results")

            all_results.extend(results)
            pages_fetched += 1

            if not token:
                print("⛔ No further pages.")
                break

            page_token = token
            time.sleep(2.0)

        # De-dup by 'id' (as requested in field mask)
        unique_results = {place["id"]: place for place in all_results if "id" in place}

        print(f"\n🎯 Done: {len(unique_results)} total unique places across {pages_fetched} pages "
              f"({requests_made} HTTP requests).")

        return {
            "results": list(unique_results.values()),
            "pages_fetched": pages_fetched,
            "total_returned": len(unique_results),
            "requests_made": requests_made
        }
    