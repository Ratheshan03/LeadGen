import sys
import os
import json
from datetime import datetime
from shapely.geometry import shape

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers import generate_tiles_for_australia
from visualization import visualize_tiles_on_map, visualize_region_polygon


def get_polygon_from_geojson(region_name: str, geojson_type: str):
    """
    Loads and returns the polygon geometry of a given region from the specified GeoJSON.

    Args:
        region_name (str): Name of the region to look up.
        geojson_type (str): One of 'gccsa', 'regions', or 'lga'.

    Returns:
        Tuple[str, Polygon or MultiPolygon]: Matched region name and Shapely geometry object.
    """
    geojson_file_map = {
        "gccsa": "data/geojson/gccsa.geojson",
        "regions": "data/geojson/regions.geojson",
        "lga": "data/geojson/lga.geojson"
    }

    geojson_path = geojson_file_map.get(geojson_type.lower())
    if not geojson_path or not os.path.exists(geojson_path):
        print(f"❌ Invalid geojson type or path not found: {geojson_type}")
        return None, None

    with open(geojson_path, 'r', encoding='utf-8') as f:
        geo_data = json.load(f)

    for feature in geo_data["features"]:
        props = feature.get("properties")
        geom = feature.get("geometry")

        if geojson_type == "gccsa":
            name = props.get("GCC_NAME21", "").strip().lower()
        elif geojson_type == "regions":
            name = props.get("SA2_NAME21", "").strip().lower()
        elif geojson_type == "lga":
            name = props.get("LGA_NAME21", "").strip().lower()
        else:
            continue

        if name == region_name.strip().lower():
            return name, shape(geom)

    print(f"⚠️ Region '{region_name}' not found in {geojson_type}.geojson.")
    return None, None


if __name__ == "__main__":
    tile_km = 5
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    region_name = "north melbourne"  # Must match the 'name' in geojson (case-insensitive)
    geojson_type = "regions"  # options: 'gccsa', 'regions', 'lga'

    print(f"🌏 Generating tiles for '{region_name}' using {geojson_type}.geojson at {tile_km}km resolution.")

    all_tiles = generate_tiles_for_australia(
        tile_km=tile_km,
        geojson_source=geojson_type,
        target_region=region_name,
    )

    if not all_tiles:
        print("❌ No tiles generated. Please check the region name or geojson file.")
        sys.exit(1)

    region_safe = region_name.lower().replace(" ", "_")
    tile_map_path = f"output_maps/{region_safe}_tiles_{tile_km}km_{timestamp}.html"

    print(f"\n🗺️ Visualizing tiles for region: {region_name}...")
    # Visualize original polygon boundary
    matched_name, matched_geom = get_polygon_from_geojson(region_name, geojson_type)
    if matched_geom:
        polygon_map_path = f"output_maps/{region_safe}_polygon_{tile_km}km_{timestamp}.html"
        visualize_region_polygon(matched_name, matched_geom, save_path=polygon_map_path, color="green", zoom=12)

    # Visualize generated tiles
    visualize_tiles_on_map(all_tiles, save_path=tile_map_path, zoom=10, color="orange")

    print("\n🎯 Done! Open the HTML files in your browser to inspect tile coverage.")
