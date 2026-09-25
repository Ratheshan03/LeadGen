import sys
import os
import json
import requests
from datetime import datetime
from shapely.geometry import shape

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visualization import visualize_multiple_polygons, visualize_multiple_tiles

BASE_URL = "http://localhost:8000"

GEOJSON_FILES = {
    "gccsa": "data/geojson/gccsa.geojson",
    "regions": "data/geojson/regions.geojson",
    "lga": "data/geojson/lga.geojson"
}

def load_regions_from_geojson(geojson_type):
    """Load region names and geometries from given geojson type."""
    path = GEOJSON_FILES.get(geojson_type)
    if not path or not os.path.exists(path):
        print(f"❌ GeoJSON file not found for type: {geojson_type}")
        return []

    with open(path, 'r', encoding='utf-8') as f:
        geo_data = json.load(f)

    regions = []
    for feature in geo_data["features"]:
        props = feature.get("properties")
        geom = feature.get("geometry")

        if not geom:
            print(f"⚠️ Skipping feature with no geometry: {props}")
            continue

        if geojson_type == "gccsa":
            name = props.get("GCC_NAME21", "").strip()
        elif geojson_type == "regions":
            name = props.get("SA2_NAME21", "").strip()
        elif geojson_type == "lga":
            name = props.get("LGA_NAME24", "").strip()
        else:
            continue

        if not name:
            print(f"⚠️ Skipping feature with missing name: {props}")
            continue

        regions.append((name, shape(geom)))

    return regions


def full_crawl_dry_run(geojson_type):
    """Call the full crawler endpoint in dry run mode."""
    try:
        response = requests.get(
            f"{BASE_URL}/api/business/crawl/textsearch/full",
            params={
                "dry_run": "true",
                "geojson_type": geojson_type
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Full crawl dry run failed for '{geojson_type}': {str(e)}"}


if __name__ == "__main__":
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    geojson_type = "lga"  # Options: "gccsa", "regions", "lga"

    print(f"\n🔎 Processing GeoJSON type: {geojson_type}")

    # Step 1: Call API to get dry run results (API handles tile generation)
    dry_run_result = full_crawl_dry_run(geojson_type)
    if "error" in dry_run_result:
        print(f"❌ Error: {dry_run_result['error']}")
        sys.exit(1)

    if "details" not in dry_run_result or "total_tiles" not in dry_run_result:
        print(f"❌ Invalid API response format: {dry_run_result}")
        sys.exit(1)

    total_tiles_count = dry_run_result.get("total_tiles", 0)
    simulated_requests = total_tiles_count
    details = dry_run_result.get("details", [])

    # Step 2: Load polygons for visualization (from local geojson)
    regions = load_regions_from_geojson(geojson_type)
    region_map = {name: geom for name, geom in regions}

    all_polygons = []
    all_tiles = []

    for item in details:
        region_name = item.get("region_name")
        tiles = item.get("tiles", [])

        if region_name in region_map:
            all_polygons.append((region_name, region_map[region_name]))
        all_tiles.extend(tiles)

    # Step 3: Save combined maps
    combined_polygon_map_path = f"output_maps/combined_polygons_{geojson_type}_10km_{timestamp}.html"
    combined_tiles_map_path = f"output_maps/combined_tiles_{geojson_type}_10km_{timestamp}.html"

    visualize_multiple_polygons(all_polygons, save_path=combined_polygon_map_path, color="blue", zoom=5)
    visualize_multiple_tiles(all_tiles, save_path=combined_tiles_map_path, zoom=5, color="orange")

    # Step 4: Save summary
    summary_report = {
        geojson_type: {
            "total_regions": len(all_polygons),
            "total_tiles": total_tiles_count,
            "simulated_requests": simulated_requests
        }
    }

    print(f"\n📊 Summary for {geojson_type}:")
    print(f"  - Total regions: {len(all_polygons)}")
    print(f"  - Total tiles: {total_tiles_count}")
    print(f"  - Estimated simulated requests: {simulated_requests}")

    summary_file = f"full_crawl_dry_run_summary_{geojson_type}_{timestamp}.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)

    print(f"\n✅ Summary report saved to: {summary_file}")
    print(f"✅ Combined polygon map saved to: {combined_polygon_map_path}")
    print(f"✅ Combined tiles map saved to: {combined_tiles_map_path}")
    print("🎯 Done! Open the HTML files in 'output_maps' to inspect total coverage.")
