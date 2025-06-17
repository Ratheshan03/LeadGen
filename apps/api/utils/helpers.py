def transform_place_result(result: dict) -> dict:
    # Support both v1 (new) and legacy API responses
    place_id = result.get("place_id") or result.get("id")
    name = result.get("name") or result.get("displayName", {}).get("text")
    address = result.get("formatted_address") or result.get("formattedAddress") or result.get("vicinity")

    return {
        "place_id": place_id,
        "name": name,
        "address": address,
        "phone": result.get("formatted_phone_number") or result.get("internationalPhoneNumber") or None,
        "website": result.get("website") or result.get("websiteUri") or None,
        "status": "active",
        "rating": result.get("rating"),
        "total_reviews": result.get("user_ratings_total") or result.get("userRatingCount"),
        "opening_hours": result.get("opening_hours", {}).get("weekday_text", []) or result.get("regularOpeningHours", {}).get("weekdayDescriptions", []),
        "tags": result.get("types", []),
    }
