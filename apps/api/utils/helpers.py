import os
import re
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


# Tile Generation for all regions using GeoJSON files
def generate_tiles_for_australia(
    tile_km: float = 10.0,
    geojson_source: str = "lga",
    target_region: str = None,
    state_name: str = None
):
    print(f"\n📂 Loading GeoJSON data: {geojson_source} ...")
    base_path = "data/geojson"
    geojson_filename_map = {
        "gccsa": "gccsa.geojson",
        "lga": "lga.geojson",
        "regions": "regions.geojson"
    }

    geojson_path = os.path.join(base_path, geojson_filename_map.get(geojson_source.lower(), "regions.geojson"))
    with open(geojson_path, 'r', encoding='utf-8') as f:
        region_data = json.load(f)

    region_geom_map, region_area_map, region_metadata_map = {}, {}, {}

    region_name_key = {
        "gccsa": "GCC_NAME21",
        "lga": "LGA_NAME24",
        "regions": "SA2_NAME21"
    }[geojson_source]

    region_area_key = {
        "gccsa": "AREASQKM21",
        "lga": "AREASQKM",
        "regions": "AREASQKM21"
    }[geojson_source]

    print("🔎 Building geometry maps...")
    for feature in region_data["features"]:
        name = feature["properties"].get(region_name_key, "").strip().lower()
        geom = feature.get("geometry")
        if not geom:
            continue

        shapely_geom = shape(geom)
        if not shapely_geom.is_valid:
            shapely_geom = shapely_geom.buffer(0)  # fix self-intersections if needed

        region_geom_map[name] = shapely_geom
        region_area_map[name] = feature["properties"].get(region_area_key, 0) or 0
        region_metadata_map[name] = feature["properties"]

    print("🌐 Setting up coordinate transformations...")
    project = pyproj.Transformer.from_crs("EPSG:7844", "EPSG:3857", always_xy=True).transform
    reverse_project = pyproj.Transformer.from_crs("EPSG:3857", "EPSG:7844", always_xy=True).transform

    all_tiles = []

    def determine_tile_size(region_name, metadata, geojson_source):
        name = region_name.lower()
        area_key = "AREASQKM21" if geojson_source != "lga" else "AREASQKM"
        area = metadata.get(area_key, 0) or 0
        gcc_name = (metadata.get("GCC_NAME21") or "").lower()
        sa4_name = (metadata.get("SA4_NAME21") or "").lower()

        # 1. Keyword-based overrides (low density)
        if any(keyword in name or keyword in sa4_name for keyword in LOW_DENSITY_REGION_KEYWORDS):
            return max(size for _, _, size in TILE_SIZE_OVERRIDES)

        # 2. Metro regions (use finer tiles)
        if gcc_name in [g.lower() for g in GCCSA_REGIONS]:
            if area and area < 5000:
                return 5
            return 10

        # 3. Area-based overrides
        for min_area, max_area, size in TILE_SIZE_OVERRIDES:
            if min_area <= area < max_area:
                return size

        # 4. Safe default
        return 25

    def generate_tiles_for_geom(region_name, geom, tile_km_local):
        region_tiles = []
        unique_tiles_set = set()

        tile_size_m = tile_km_local * 1000
        geom_m = transform(project, geom)
        min_x, min_y, max_x, max_y = geom_m.bounds

        # Compute area
        meta_area = region_area_map.get(region_name, 0) or 0
        geom_area = geom_m.area / 1e6  # in km² (since geom_m is in meters)
        area = meta_area if meta_area > 0 else geom_area

        print(f"   • {region_name.title()}: Area={area:.1f} km², Tile Size={tile_km_local}km")

        # ---------------- Case 1 + Case 2: Single tile coverage ----------------
        bbox_width_km = (max_x - min_x) / 1000
        bbox_height_km = (max_y - min_y) / 1000
        bbox_diag_km = max(bbox_width_km, bbox_height_km)

        if area <= (tile_km_local ** 2) * 1.5 or bbox_diag_km <= tile_km_local * 3:
            # force one tile (buffer slightly if small)
            buffer = tile_size_m * (0.1 if area < 200 else 0.02)
            min_x, min_y, max_x, max_y = (
                min_x - buffer, min_y - buffer, max_x + buffer, max_y + buffer
            )
            tile_box_wgs84 = transform(reverse_project, box(min_x, min_y, max_x, max_y))
            lon_min, lat_min, lon_max, lat_max = tile_box_wgs84.bounds

            region_tiles.append({
                "region": region_name,
                "state": state_name,
                "source": geojson_source,
                "tile_name": f"{region_name.replace(' ', '_')}_single",
                "low": {"latitude": round(lat_min, 6), "longitude": round(lon_min, 6)},
                "high": {"latitude": round(lat_max, 6), "longitude": round(lon_max, 6)}
            })
            print(f"✅ Single-tile coverage for '{region_name}' (bbox ~{bbox_diag_km:.1f} km)")
            return region_tiles

        # ---------------- Case 3: Grid tiling ----------------
        min_overlap = 0.2 if area < 500 else 0.3
        row, x = 0, min_x
        while x < max_x:
            col, y = 0, min_y
            while y < max_y:
                tile_box = box(x, y, x + tile_size_m, y + tile_size_m)
                intersection = geom_m.intersection(tile_box)
                overlap_ratio = intersection.area / tile_box.area if not intersection.is_empty else 0

                if overlap_ratio >= min_overlap:
                    tile_box_wgs84 = transform(reverse_project, tile_box)
                    lon_min, lat_min, lon_max, lat_max = tile_box_wgs84.bounds
                    tile_key = (round(lat_min, 6), round(lon_min, 6),
                                round(lat_max, 6), round(lon_max, 6))
                    if tile_key not in unique_tiles_set:
                        unique_tiles_set.add(tile_key)
                        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", region_name)
                        region_tiles.append({
                            "region": region_name,
                            "state": state_name,
                            "source": geojson_source,
                            "tile_name": f"{safe_name}_r{row}_c{col}",
                            "low": {"latitude": round(lat_min, 6), "longitude": round(lon_min, 6)},
                            "high": {"latitude": round(lat_max, 6), "longitude": round(lon_max, 6)}
                        })
                col += 1
                y += tile_size_m
            row += 1
            x += tile_size_m

        # ---------------- Case 4: Fallback for elongated regions ----------------
        if not region_tiles:
            tile_box_wgs84 = transform(reverse_project, box(min_x, min_y, max_x, max_y))
            lon_min, lat_min, lon_max, lat_max = tile_box_wgs84.bounds
            width, height = lon_max - lon_min, lat_max - lat_min

            splits = 2 if max(width, height) / min(width, height) > 3 else 1
            for i in range(splits):
                if height > width:
                    split_box = box(min_x, min_y + i * (max_y - min_y) / splits,
                                    max_x, min_y + (i + 1) * (max_y - min_y) / splits)
                else:
                    split_box = box(min_x + i * (max_x - min_x) / splits, min_y,
                                    min_x + (i + 1) * (max_x - min_x) / splits, max_y)

                split_wgs84 = transform(reverse_project, split_box)
                lon_min, lat_min, lon_max, lat_max = split_wgs84.bounds
                region_tiles.append({
                    "region": region_name,
                    "state": state_name,
                    "source": geojson_source,
                    "tile_name": f"{region_name.replace(' ', '_')}_fallback_{i}",
                    "low": {"latitude": round(lat_min, 6), "longitude": round(lon_min, 6)},
                    "high": {"latitude": round(lat_max, 6), "longitude": round(lon_max, 6)}
                })

            print(f"⚠️ Fallback: '{region_name}' covered by {splits} elongated tiles.")


        # Diagnostics (approximate)
        expected_tiles = int(area / (tile_km_local ** 2))
        actual_tiles = len(region_tiles)

        if expected_tiles > 0:
            deviation = abs(actual_tiles - expected_tiles) / expected_tiles * 100
            if deviation > 30:
                print(f"⚠️ Tile count for '{region_name}' deviates by {deviation:.1f}% "
                    f"(Expected: ~{expected_tiles}, Got: {actual_tiles})")
            else:
                print(f"✅ Tile count close to expected ({actual_tiles} vs {expected_tiles})")
        else:
            print(f"⚠️ Could not estimate expected tiles for '{region_name}', area={area:.2f} km²")

        return region_tiles
    

    # Targeted region mode
    if target_region:
        region_key = target_region.strip().lower()
        print(f"\n📍 Generating tiles for specified region: '{target_region}'")
        target_geom = region_geom_map.get(region_key)
        if not target_geom:
            print(f"❌ No geometry found for region: '{target_region}'")
            suggestions = difflib.get_close_matches(region_key, region_geom_map.keys(), n=5, cutoff=0.6)
            if suggestions:
                print("🔎 Did you mean one of the following?")
                for s in suggestions:
                    print(f"   • {s}")
            return []

        tile_km_override = determine_tile_size(region_key, region_metadata_map.get(region_key, {}), geojson_source)
        print(f"\n📏 Generating tiles for: {target_region} ({geojson_source.upper()}) with tile size {tile_km_override}km.")

        try:
            region_tiles = generate_tiles_for_geom(region_key, target_geom, tile_km_override)
            all_tiles.extend(region_tiles)
            print(f"✅ {target_region} -> {len(region_tiles)} tiles generated.")
        except Exception as e:
            print(f"❌ Error generating tiles for {target_region}: {e}")
        return all_tiles

    # All regions mode
    print(f"\n📍 No specific region provided. Generating tiles for all regions in: {geojson_source.upper()}")
    for region_name, region_geom in tqdm(region_geom_map.items(), desc="🧩 Generating tiles"):
        try:
            tile_km_override = determine_tile_size(region_name, region_metadata_map.get(region_name, {}), geojson_source)
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


