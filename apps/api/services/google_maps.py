import requests
from utils.api_key_manager import APIKeyManager
from config.constants import GOOGLE_PLACES_NEARBY_URL, GOOGLE_PLACE_DETAILS_URL
from utils.quota_manager import QuotaManager

class GoogleMapsService:
    def __init__(self):
        self.key_manager = APIKeyManager()

    def search_places_nearby(self, location: str, radius: float = 5000.0, place_type: str = None):
        latitude, longitude = map(float, location.split(","))

        payload = {
            "includedTypes": [place_type] if place_type else [],
            "maxResultCount": 20,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": radius
                }
            }
        }

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.key_manager.get_key(),
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types,places.id"
        }

        response = requests.post(GOOGLE_PLACES_NEARBY_URL, json=payload, headers=headers)
        QuotaManager().increment()

        if response.status_code != 200:
            raise Exception(f"Google API Error: {response.text}")

        return response.json()

    def get_place_details(self, place_id: str):
        url = f"{GOOGLE_PLACE_DETAILS_URL}/{place_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.key_manager.get_key(),
            "X-Goog-FieldMask": "id,displayName,formattedAddress,website,formattedPhoneNumber"
        }

        response = requests.get(url, headers=headers)
        QuotaManager().increment()

        if response.status_code != 200:
            raise Exception(f"Google API Error: {response.text}")

        return response.json()
