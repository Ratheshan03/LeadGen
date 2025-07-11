# import sys
# import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from helpers import generate_tiles_for_region_unified
# from visualization import visualize_tiles_on_map

# if __name__ == "__main__":
#     state = "Victoria"
#     region = "Melbourne"

#     print(f"🧭 Generating unified tiles for {region}, {state} ...")
#     tiles = generate_tiles_for_region_unified(state, region, tile_km=5)

#     print(f"✅ Total tiles generated: {len(tiles)}")
#     visualize_tiles_on_map(
#         tiles,
#         save_path=f"{region.lower()}_unified_tiles_map.html",
#         zoom=11,
#         color="orange"
#     )


import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers import generate_tiles_for_region_unified
from visualization import visualize_tiles_on_map
from config.constants import REGION_TILE_CONFIGS  # Make sure this is the final 64-region config

if __name__ == "__main__":
    all_tiles = []

    for region_name, config in REGION_TILE_CONFIGS.items():
        if region_name == "default":
            continue  # skip default fallback

        tile_km = config.get("tile_km", 5)
        print(f"🧭 Generating tiles for: {region_name} ...")
        try:
            tiles = generate_tiles_for_region_unified("AUTO", region_name, tile_km=tile_km)
            for tile in tiles:
                tile["tile_name"] = f"{region_name}"  # Optional: add region name as tile label
            all_tiles.extend(tiles)
            print(f"✅ {region_name}: {len(tiles)} tiles")
        except Exception as e:
            print(f"❌ Error generating tiles for {region_name}: {e}")

    print(f"🎯 Total tiles aggregated: {len(all_tiles)}")
    visualize_tiles_on_map(
        all_tiles,
        save_path="australia_all_regions_tiles_map.html",
        zoom=4,  # Low zoom to view entire AU
        color="purple"
    )
