from config.constants import REGION_COORDINATES, AU_REGIONS

def transform_place_result(result: dict) -> dict:
    # Handles both new and legacy Places API results
    place_id = result.get("place_id") or result.get("id")
    name = result.get("name") or result.get("displayName", {}).get("text")
    address = result.get("formatted_address") or result.get("formattedAddress") or result.get("vicinity")

    return {
        "place_id": place_id,
        "name": name,
        "address": address,
        "phone": result.get("formatted_phone_number") or result.get("internationalPhoneNumber"),
        "website": result.get("website") or result.get("websiteUri"),
        "location": result.get("geometry", {}).get("location") or result.get("location", {}),
        "types": result.get("types", []),
        "tags": result.get("types", []),  # Tagging same as types for now
        "rating": result.get("rating"),
        "total_reviews": result.get("user_ratings_total") or result.get("userRatingCount"),
        "opening_hours": result.get("opening_hours", {}).get("weekday_text", []) or result.get("regularOpeningHours", {}).get("weekdayDescriptions", []),
    }


def generate_text_search_tiles(tile_delta=0.2):
    """
    Dynamically generates locationBias rectangles for text search,
    using REGION_COORDINATES as tile centers and creating a 3x3 grid
    around each.

    Each tile includes state and region to support automated crawling.

    Returns:
        List[Dict]: Each dict contains region, state, and locationBias.
    """
    tiles = []

    # Build reverse map from region -> state for fast lookup
    region_to_state = {
        region: state
        for state, regions in AU_REGIONS.items()
        for region in regions
    }

    for region, coord_str in REGION_COORDINATES.items():
        state = region_to_state.get(region, "UNKNOWN")
        lat_c, lon_c = map(float, coord_str.split(","))
        
        for i in [-1, 0, 1]:
            for j in [-1, 0, 1]:
                lat_low = lat_c + i * tile_delta
                lon_low = lon_c + j * tile_delta
                lat_high = lat_low + tile_delta
                lon_high = lon_low + tile_delta

                tile = {
                    "region": region,
                    "state": state,
                    "tile_name": f"{region.replace(' ', '_')}_tile_{i+1}{j+1}",
                    "low": {
                        "latitude": round(lat_low, 6),
                        "longitude": round(lon_low, 6)
                    },
                    "high": {
                        "latitude": round(lat_high, 6),
                        "longitude": round(lon_high, 6)
                    }
                }
                tiles.append(tile)

    return tiles


def generate_tiles_for_region(state: str, region: str, tile_delta=0.2):
    """
    Generate 3x3 grid tiles only for the specified region.
    """
    tiles = []
    if region not in REGION_COORDINATES:
        return []

    lat_c, lon_c = map(float, REGION_COORDINATES[region].split(","))

    for i in [-1, 0, 1]:
        for j in [-1, 0, 1]:
            lat_low = lat_c + i * tile_delta
            lon_low = lon_c + j * tile_delta
            lat_high = lat_low + tile_delta
            lon_high = lon_low + tile_delta

            tile = {
                "region": region,
                "state": state,
                "tile_name": f"{region.replace(' ', '_')}_tile_{i+1}{j+1}",
                "low": {"latitude": round(lat_low, 6), "longitude": round(lon_low, 6)},
                "high": {"latitude": round(lat_high, 6), "longitude": round(lon_high, 6)},
            }
            tiles.append(tile)

    return tiles
