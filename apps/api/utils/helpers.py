import requests
import math
from config.constants import REGION_COORDINATES, REGION_TILE_CONFIGS, AU_REGIONS

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


def km_to_lat_lon_deltas(km: float):
    return km / 111, km / 111  # ~111 km per degree latitude/longitude


def generate_text_search_tiles_unified(tile_km=5):
    """
    Uses the unified REGION_TILE_CONFIGS to generate tile boundaries for all regions.
    Useful for text search with proper bounding boxes.

    Returns:
        List[Dict]: All region tiles (used for crawling).
    """
    tiles = []

    region_to_state = {
        region: state
        for state, regions in AU_REGIONS.items()
        for region in regions
    }

    for region, center_str in REGION_COORDINATES.items():
        state = region_to_state.get(region, "UNKNOWN")
        lat_center, lon_center = map(float, center_str.split(","))

        tile_config = REGION_TILE_CONFIGS.get(region, REGION_TILE_CONFIGS["default"])
        tile_km = tile_config["tile_km"]
        delta_lat, delta_lon = km_to_lat_lon_deltas(tile_km)

        if "bbox_override" in tile_config:
            lat_min = tile_config["bbox_override"]["lat_min"]
            lat_max = tile_config["bbox_override"]["lat_max"]
            lon_min = tile_config["bbox_override"]["lon_min"]
            lon_max = tile_config["bbox_override"]["lon_max"]
        else:
            width_km = tile_config["width_km"]
            height_km = tile_config["height_km"]
            lat_range = height_km / 2 / 111
            lon_range = width_km / 2 / 111
            lat_min = lat_center - lat_range
            lat_max = lat_center + lat_range
            lon_min = lon_center - lon_range
            lon_max = lon_center + lon_range

        rows = math.ceil((lat_max - lat_min) / delta_lat)
        cols = math.ceil((lon_max - lon_min) / delta_lon)

        for i in range(rows):
            for j in range(cols):
                lat_low = lat_min + i * delta_lat
                lat_high = lat_low + delta_lat
                lon_low = lon_min + j * delta_lon
                lon_high = lon_low + delta_lon

                tiles.append({
                    "region": region,
                    "state": state,
                    "tile_name": f"{region.replace(' ', '_')}_r{i+1}_c{j+1}",
                    "low": {"latitude": round(lat_low, 6), "longitude": round(lon_low, 6)},
                    "high": {"latitude": round(lat_high, 6), "longitude": round(lon_high, 6)},
                })

    print(f"✅ Total unified search tiles generated: {len(tiles)}")
    return tiles



def generate_tiles_for_region_unified(state: str, region: str, tile_km: float = None, buffer_factor: float = -0.05):
    """
    Combines bbox_override > Nominatim bbox > region fallback center to generate tiles.
    """
    center = REGION_COORDINATES.get(region)
    if not center:
        print(f"❌ No coordinates defined for region: {region}")
        return []

    lat_center, lon_center = map(float, center.split(","))
    region_tile_config = REGION_TILE_CONFIGS.get(region, REGION_TILE_CONFIGS["default"])
    tile_km = tile_km or region_tile_config["tile_km"]

    # ✅ Use bbox_override if available
    if "bbox_override" in region_tile_config:
        bbox = region_tile_config["bbox_override"]
        lat_min, lat_max = bbox["lat_min"], bbox["lat_max"]
        lon_min, lon_max = bbox["lon_min"], bbox["lon_max"]
        print(f"📦 Using bbox_override for {region}: ({lat_min}, {lon_min}) to ({lat_max}, {lon_max})")
    
    else:
        # 🌐 Try Nominatim bounding box
        query = f"{region}, {state}, Australia"
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={query}&polygon_geojson=1"
        headers = {"User-Agent": "leadgen-tile-crawler/1.0 (rathe.personal.project@example.com)"}

        print(f"🔍 Attempting to fetch bounding box from Nominatim for: {query}")
        try:
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            if data and "boundingbox" in data[0]:
                bbox = data[0]["boundingbox"]
                lat_min = float(bbox[0])
                lat_max = float(bbox[1])
                lon_min = float(bbox[2])
                lon_max = float(bbox[3])

                # 🧠 Apply buffer to trim or expand
                lat_range = lat_max - lat_min
                lon_range = lon_max - lon_min
                lat_min += lat_range * buffer_factor
                lat_max -= lat_range * buffer_factor
                lon_min += lon_range * buffer_factor
                lon_max -= lon_range * buffer_factor

                print(f"📦 Bounding box used from Nominatim: ({lat_min}, {lon_min}) to ({lat_max}, {lon_max})")
            else:
                raise ValueError("Nominatim returned no bbox.")
        except Exception as e:
            print(f"[⚠️ Fallback to center box] Nominatim failed: {e}")
            width_km = region_tile_config["width_km"]
            height_km = region_tile_config["height_km"]
            lat_range = height_km / 2 / 111
            lon_range = width_km / 2 / 111
            lat_min = lat_center - lat_range
            lat_max = lat_center + lat_range
            lon_min = lon_center - lon_range
            lon_max = lon_center + lon_range
            print(f"📦 Bounding box from center+config: ({lat_min}, {lon_min}) to ({lat_max}, {lon_max})")

    # 🔳 Tile calculation
    delta_lat, delta_lon = km_to_lat_lon_deltas(tile_km)
    rows = math.ceil((lat_max - lat_min) / delta_lat)
    cols = math.ceil((lon_max - lon_min) / delta_lon)

    tiles = []
    for i in range(rows):
        for j in range(cols):
            lat_low = lat_min + i * delta_lat
            lat_high = lat_low + delta_lat
            lon_low = lon_min + j * delta_lon
            lon_high = lon_low + delta_lon

            tiles.append({
                "region": region,
                "state": state,
                "tile_name": f"{region.replace(' ', '_')}_r{i+1}_c{j+1}",
                "low": {"latitude": round(lat_low, 6), "longitude": round(lon_low, 6)},
                "high": {"latitude": round(lat_high, 6), "longitude": round(lon_high, 6)},
            })

    print(f"✅ {region}, {state}: {len(tiles)} tiles generated (tile_km={tile_km})")
    return tiles

