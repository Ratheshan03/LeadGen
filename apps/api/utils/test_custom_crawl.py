import sys
import os
import json
import requests
from datetime import datetime
from shapely.geometry import shape

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visualization import visualize_tiles_on_map, visualize_region_polygon

BASE_URL = "http://localhost:8000" 

def crawl_custom_text_search(query: str, state: str, region: str, geojson_type: str, dry_run=True):
    """Call custom scoped text search API."""
    try:
        response = requests.get(
            f"{BASE_URL}/api/business/crawl/textsearch/custom",
            params={
                "query": query,
                "state": state,
                "region": region,
                "geojson_type": geojson_type,
                "dry_run": str(dry_run).lower()
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"Custom text search crawl failed: {str(e)}"}


def get_polygon_from_geojson(region_name: str, geojson_type: str):
    """Load the polygon geometry for a given region from a local GeoJSON file."""
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
            name = props.get("LGA_NAME24", "").strip().lower()
        else:
            continue

        if name == region_name.strip().lower():
            return name, shape(geom)

    print(f"⚠️ Region '{region_name}' not found in {geojson_type}.geojson.")
    return None, None


if __name__ == "__main__":
    tile_km = 10
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    # Test parameters
    region_name = "Walkerville"
    geojson_type = "lga"
    state_name = "South Australia"
    business_query = "All"  # Test single type first instead of ALL
    dry_run = False

    print(f"\n🔍 Starting CUSTOM CRAWL: Query='{business_query}', State='{state_name}', Region='{region_name}', Dry Run={dry_run}...")

    crawl_response = crawl_custom_text_search(
        query=business_query,
        state=state_name,
        region=region_name,
        geojson_type=geojson_type,
        dry_run=dry_run
    )

    if "error" in crawl_response:
        print(f"❌ Crawl failed: {crawl_response['error']}")
        sys.exit(1)

    tiles = crawl_response.get("tiles", [])
    if not tiles:
        print("⚠️ No tiles returned from API response.")
    else:
        region_safe = region_name.lower().replace(" ", "_")
        tile_map_path = f"output_maps/{region_safe}_tiles_{timestamp}.html"
        visualize_tiles_on_map(tiles, save_path=tile_map_path, zoom=10, color="orange")
        print(f"✅ Tile map saved: {tile_map_path}")

    # Visualize polygon 
    matched_name, matched_geom = get_polygon_from_geojson(region_name, geojson_type)
    if matched_geom:
        polygon_map_path = f"output_maps/{region_safe}_polygon_{timestamp}.html"
        visualize_region_polygon(matched_name, matched_geom, save_path=polygon_map_path, color="green", zoom=12)
        print(f"✅ Polygon map saved: {polygon_map_path}")

    # Display basic results
    print("\n" + "="*70)
    print("CRAWL RESULTS SUMMARY")
    print("="*70)
    print(f"✅ Total Saved: {crawl_response.get('total_saved', 0)} leads")
    print(f"📍 Tiles Generated: {crawl_response.get('tiles_generated', crawl_response.get('tiles_scanned', 0))}")
    print(f"🔁 Tile Crawls (tile×type): {crawl_response.get('tile_crawls', 'n/a')}")
    print(f"📊 API Requests: {crawl_response.get('api_requests_total', 0)}")
    print(f"💵 Estimated Cost: ${crawl_response.get('estimated_cost_usd', 0)} USD")
    print(f"❌ Failures: {crawl_response.get('failures', 0)}")
    if crawl_response.get("quota_exceeded"):
        print("🛑 QUOTA CAP REACHED — crawl stopped early. Results are PARTIAL.")
    print("="*70)
    print("\n🎯 Done! Open the HTML files in 'output_maps' to inspect tile coverage and polygon mapping.")

