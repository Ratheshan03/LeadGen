import os
import requests
import math
import json
import difflib
from shapely.geometry import shape, box, Polygon
from shapely.ops import transform
import pyproj
from tqdm import tqdm
from config.constants import REGION_COORDINATES, AU_REGIONS
from config.constants import GCCSA_REGIONS, TILE_SIZE_OVERRIDES, LOW_DENSITY_REGION_KEYWORDS


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
        "tags": result.get("types", []),
        "rating": result.get("rating"),
        "total_reviews": result.get("user_ratings_total") or result.get("userRatingCount"),
        "opening_hours": result.get("opening_hours", {}).get("weekday_text", []) or result.get("regularOpeningHours", {}).get("weekdayDescriptions", []),
    }


def km_to_lat_lon_deltas(km: float):
    return km / 111, km / 111  # ~111 km per degree latitude/longitude


# def generate_text_search_tiles_unified(tile_km=5):
#     """
#     Uses the unified REGION_TILE_CONFIGS to generate tile boundaries for all regions.
#     Useful for text search with proper bounding boxes.

#     Returns:
#         List[Dict]: All region tiles (used for crawling).
#     """
#     tiles = []

#     region_to_state = {
#         region: state
#         for state, regions in AU_REGIONS.items()
#         for region in regions
#     }

#     for region, center_str in REGION_COORDINATES.items():
#         state = region_to_state.get(region, "UNKNOWN")
#         lat_center, lon_center = map(float, center_str.split(","))

#         tile_config = REGION_TILE_CONFIGS.get(region, REGION_TILE_CONFIGS["default"])
#         tile_km = tile_config["tile_km"]
#         delta_lat, delta_lon = km_to_lat_lon_deltas(tile_km)

#         if "bbox_override" in tile_config:
#             lat_min = tile_config["bbox_override"]["lat_min"]
#             lat_max = tile_config["bbox_override"]["lat_max"]
#             lon_min = tile_config["bbox_override"]["lon_min"]
#             lon_max = tile_config["bbox_override"]["lon_max"]
#         else:
#             width_km = tile_config["width_km"]
#             height_km = tile_config["height_km"]
#             lat_range = height_km / 2 / 111
#             lon_range = width_km / 2 / 111
#             lat_min = lat_center - lat_range
#             lat_max = lat_center + lat_range
#             lon_min = lon_center - lon_range
#             lon_max = lon_center + lon_range

#         rows = math.ceil((lat_max - lat_min) / delta_lat)
#         cols = math.ceil((lon_max - lon_min) / delta_lon)

#         for i in range(rows):
#             for j in range(cols):
#                 lat_low = lat_min + i * delta_lat
#                 lat_high = lat_low + delta_lat
#                 lon_low = lon_min + j * delta_lon
#                 lon_high = lon_low + delta_lon

#                 tiles.append({
#                     "region": region,
#                     "state": state,
#                     "tile_name": f"{region.replace(' ', '_')}_r{i+1}_c{j+1}",
#                     "low": {"latitude": round(lat_low, 6), "longitude": round(lon_low, 6)},
#                     "high": {"latitude": round(lat_high, 6), "longitude": round(lon_high, 6)},
#                 })

#     print(f"✅ Total unified search tiles generated: {len(tiles)}")
#     return tiles




# Tile Generation for all regions using GeoJSON files

def generate_tiles_for_australia(
    tile_km: float = 10.0,
    geojson_source: str = "regions",
    target_region: str = None
):

    print(f"\n\U0001F4C2 Loading GeoJSON data: {geojson_source} ...")
    base_path = "data/geojson"
    geojson_filename_map = {
        "gccsa": "gccsa.geojson",
        "lga": "lga.geojson",
        "regions": "regions.geojson"
    }

    geojson_path = os.path.join(base_path, geojson_filename_map.get(geojson_source.lower(), "regions.geojson"))
    with open(geojson_path, 'r', encoding='utf-8') as f:
        region_data = json.load(f)

    region_geom_map = {}
    region_area_map = {}
    region_metadata_map = {}

    region_name_key = {
        "gccsa": "GCC_NAME21",
        "lga": "LGA_NAME24",
        "regions": "SA2_NAME21"
    }[geojson_source]

    region_area_key = "AREASQKM21"

    print("\U0001F50D Building geometry maps...")
    for feature in region_data["features"]:
        name = feature["properties"].get(region_name_key, "").strip().lower()
        if feature.get("geometry"):
            geom = shape(feature["geometry"])
            region_geom_map[name] = geom
            region_area_map[name] = feature["properties"].get(region_area_key, 0)
            region_metadata_map[name] = feature["properties"]

    print("\U0001F310Setting up coordinate transformations...")
    project = pyproj.Transformer.from_crs("EPSG:7844", "EPSG:3857", always_xy=True).transform
    reverse_project = pyproj.Transformer.from_crs("EPSG:3857", "EPSG:7844", always_xy=True).transform

    all_tiles = []

    def determine_tile_size(region_name, metadata):
        name = region_name.lower()
        area = metadata.get("AREASQKM21", 0)
        gcc_name = metadata.get("GCC_NAME21", "").lower()
        sa4_name = metadata.get("SA4_NAME21", "").lower()

        if gcc_name in [g.lower() for g in GCCSA_REGIONS]:
            return 10

        if any(keyword in name or keyword in sa4_name for keyword in LOW_DENSITY_REGION_KEYWORDS):
            return max(size for _, _, size in TILE_SIZE_OVERRIDES)

        for min_area, max_area, size in TILE_SIZE_OVERRIDES:
            if min_area <= area < max_area:
                return size

        return 10

    def generate_tiles_for_geom(region_name, geom, tile_km_local):
        region_tiles = []
        unique_tiles_set = set()

        tile_size_m = tile_km_local * 1000
        geom_m = transform(project, geom)
        min_x, min_y, max_x, max_y = geom_m.bounds

        dynamic_buffer = 200 if region_area_map.get(region_name, 100) < 5 else 0
        min_x -= dynamic_buffer
        min_y -= dynamic_buffer
        max_x += dynamic_buffer
        max_y += dynamic_buffer

        row = 0
        x = min_x
        while x < max_x:
            col = 0
            y = min_y
            while y < max_y:
                tile_box = box(x, y, x + tile_size_m, y + tile_size_m)
                intersection = geom_m.intersection(tile_box)
                overlap_ratio = intersection.area / tile_box.area if not intersection.is_empty else 0

                min_overlap = 0.01 if region_area_map.get(region_name, 100) < 5 else 0.35

                if overlap_ratio >= min_overlap:
                    tile_box_wgs84 = transform(reverse_project, tile_box)
                    lon_min, lat_min, lon_max, lat_max = tile_box_wgs84.bounds
                    tile_key = (round(lat_min, 6), round(lon_min, 6), round(lat_max, 6), round(lon_max, 6))

                    if tile_key not in unique_tiles_set:
                        unique_tiles_set.add(tile_key)
                        region_tiles.append({
                            "region": region_name,
                            "source": geojson_source,
                            "tile_name": f"{region_name.replace(' ', '_')}_r{row}_c{col}",
                            "low": {"latitude": round(lat_min, 6), "longitude": round(lon_min, 6)},
                            "high": {"latitude": round(lat_max, 6), "longitude": round(lon_max, 6)}
                        })
                col += 1
                y += tile_size_m
            row += 1
            x += tile_size_m

        expected_tiles = int(region_area_map.get(region_name.strip().lower(), 0) / (tile_km_local ** 2))
        actual_tiles = len(region_tiles)
        if expected_tiles:
            deviation = abs(actual_tiles - expected_tiles) / expected_tiles * 100
            if deviation > 30:
                print(f"⚠️ Tile count for '{region_name}' deviates by {deviation:.1f}% from expected "
                      f"(Expected: ~{expected_tiles}, Got: {actual_tiles})")
            else:
                print(f"✅ Tile count close to expected ({actual_tiles} vs {expected_tiles})")
        else:
            print(f"ℹ️ No area data found for '{region_name}', skipping diagnostics.")

        return region_tiles

    if target_region:
        region_key = target_region.strip().lower()
        target_geom = region_geom_map.get(region_key)
        if not target_geom:
            print(f"❌ No geometry found for region: '{target_region}'")
            suggestions = difflib.get_close_matches(region_key, region_geom_map.keys(), n=5, cutoff=0.6)
            if suggestions:
                print("🔎 Did you mean one of the following?")
                for s in suggestions:
                    print(f"   • {s}")
            else:
                print("📜 Available region names:")
                for name in sorted(region_geom_map.keys()):
                    print(f"   • {name}")
            return []

        tile_km_override = determine_tile_size(region_key, region_metadata_map.get(region_key, {}))
        print(f"\n📏 Generating tiles for: {target_region} ({geojson_source.upper()}) with tile size {tile_km_override}km...")
        try:
            region_tiles = generate_tiles_for_geom(region_key, target_geom, tile_km_override)
            all_tiles.extend(region_tiles)
            print(f"✅ {target_region} -> {len(region_tiles)} tiles generated.")
        except Exception as e:
            print(f"❌ Error generating tiles for {target_region}: {e}")
        return all_tiles

    print(f"\n📍 No specific region provided. Generating tiles for all regions in: {geojson_source.upper()}")
    for region_name, region_geom in tqdm(region_geom_map.items(), desc="\U0001F9F1 Generating tiles"):
        print(f"\n🔎 Processing: {region_name} ...")
        try:
            tile_km_override = determine_tile_size(region_name, region_metadata_map.get(region_name, {}))
            region_tiles = generate_tiles_for_geom(region_name, region_geom, tile_km_override)
            all_tiles.extend(region_tiles)
            print(f"✅ {region_name} -> {len(region_tiles)} tiles added.")
        except Exception as e:
            print(f"❌ Error processing {region_name}: {e}")

    print(f"\n✅ Total tiles generated: {len(all_tiles)}")
    return all_tiles



# Get polygon geometry for a specific GCCSA region by name
def get_gccsa_polygon(region_name: str):
    """
    Loads and returns the polygon geometry of a given GCCSA region by name.

    Args:
        region_name (str): Name of the GCCSA region (e.g., "Greater Sydney").

    Returns:
        Tuple[str, Polygon or MultiPolygon]: The region name and Shapely geometry object.
    """
    gccsa_geojson_path = "data/geojson/gccsa.geojson"
    with open(gccsa_geojson_path, 'r', encoding='utf-8') as f:
        gccsa_data = json.load(f)

    for feature in gccsa_data["features"]:
        props = feature.get("properties")
        geom = feature.get("geometry")
        name = props.get("GCC_NAME21", "").strip().lower()

        if name == region_name.strip().lower():
            return name, shape(geom)

    print(f"⚠️ GCCSA region '{region_name}' not found in GeoJSON.")
    return None, None


