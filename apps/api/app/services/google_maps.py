import os
import requests
from dotenv import load_dotenv

load_dotenv()
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

def search_places(query: str):
    url = "https://places.googleapis.com/v1/places:searchText"

    payload = {
        "textQuery": query
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": (
            "places.displayName,"
            "places.formattedAddress,"
            "places.internationalPhoneNumber,"
            "places.websiteUri,"
            "places.businessStatus,"
            "places.rating,"
            "places.userRatingCount,"
            "places.regularOpeningHours"
        )
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        return []

    data = response.json()

    results = []
    for place in data.get("places", []):
        results.append({
            "name": place.get("displayName", {}).get("text"),
            "address": place.get("formattedAddress"),
            "phone": place.get("internationalPhoneNumber"),
            "website": place.get("websiteUri"),
            "status": place.get("businessStatus"),
            "rating": place.get("rating"),
            "total_reviews": place.get("userRatingCount"),
            "opening_hours": place.get("regularOpeningHours", {}).get("weekdayDescriptions", [])
        })

    return results
