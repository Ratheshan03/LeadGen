"""
Build LeadGen's New Zealand boundary data from the official Stats NZ files.

Source: Stats NZ Geographic Data Service, licensed CC BY 4.0
(https://datafinder.stats.govt.nz):
  Regional Council 2025 Clipped        layer 120945  -> level "region"
  Territorial Authority 2025 Clipped   layer 120962  -> level "ta"   (district / city councils)
  Statistical Area 2 2025 Clipped      layer 120969  -> level "sa2"  (suburb-sized areas)
"Clipped" versions follow the coastline (no sea), which is what a land crawl needs.

Get the data in ONE of two ways, then run the script from the project root:

  A) Automatic download
     Create a free account at https://datafinder.stats.govt.nz, then
     My account -> API keys -> create a key. Add it to .env:
         STATS_NZ_API_KEY=your-key
     and run:
         python scripts/build_new_zealand_data.py --download

  B) Manual download
     Open each layer page, click Download, choose "GeoPackage" (or "Shapefile"),
     any coordinate system. Unzip into:
         data/new_zealand/source/region/   (Regional Council)
         data/new_zealand/source/ta/       (Territorial Authority)
         data/new_zealand/source/sa2/      (Statistical Area 2)
     and run:
         python scripts/build_new_zealand_data.py

Output (committed to the repo, read by the backend):
  data/new_zealand/boundaries/{region,ta,sa2}.geojson.gz
  data/new_zealand/lookups/state_to_{region,ta,sa2}.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import geopandas as gpd
import requests
from shapely.strtree import STRtree

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geodata_common import DATA_DIR, clean_geometry, write_boundaries, write_lookup  # noqa: E402

COUNTRY_DIR = DATA_DIR / "new_zealand"
SOURCE_DIR = COUNTRY_DIR / "source"
CRS = "EPSG:4326"
LAYERS = {"region": 120945, "ta": 120962, "sa2": 120969}
PREFIX = {"region": "REGC", "ta": "TA", "sa2": "SA2"}
WFS = "https://datafinder.stats.govt.nz/services;key={key}/wfs"

# Not land areas you can crawl: offshore islands straddling the 180th meridian,
# ocean / inlet / inland-water statistical areas.
SKIP_TA_CODES = {"999"}
SKIP_SA2_PREFIXES = ("oceanic", "inlet", "inland water")
REGION_RENAMES = {"Area Outside Region": "Chatham Islands"}
# "Area Outside Region" mixes the Chatham Islands with remote islands on both
# sides of the 180th meridian; it is rebuilt from the Chatham Islands council.
OUTSIDE_REGION = "Area Outside Region"
CHATHAM_TA = "Chatham Islands Territory"


# ------------------------------------------------------------------ download --
def download(api_key: str) -> None:
    for level, layer in LAYERS.items():
        out = SOURCE_DIR / level / f"{level}.geojson"
        out.parent.mkdir(parents=True, exist_ok=True)
        features, start, page = [], 0, 1000
        print(f"Downloading {level} (layer {layer}) ...", flush=True)
        while True:
            params = {"service": "WFS", "version": "2.0.0", "request": "GetFeature",
                      "typeNames": f"layer-{layer}", "outputFormat": "json", "srsName": "EPSG:4326",
                      "count": page, "startIndex": start}
            for attempt in range(4):
                try:
                    r = requests.get(WFS.format(key=api_key), params=params, timeout=300)
                    break
                except requests.RequestException:
                    time.sleep(5 * (attempt + 1))
            else:
                raise SystemExit("Could not reach Stats NZ - check your internet connection and try again.")
            if r.status_code in (401, 403):
                raise SystemExit("Stats NZ rejected the API key. Check STATS_NZ_API_KEY in .env "
                                 "(the key needs access to layers / WFS).")
            r.raise_for_status()
            batch = r.json().get("features", [])
            features.extend(batch)
            print(f"  {len(features)} features", flush=True)
            if len(batch) < page:
                break
            start += page
        out.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")


# ---------------------------------------------------------------------- read --
def read_level(level: str) -> gpd.GeoDataFrame:
    folder = SOURCE_DIR / level
    files = sorted([p for ext in ("*.gpkg", "*.shp", "*.geojson", "*.json") for p in folder.rglob(ext)])
    if not files:
        raise SystemExit(f"No {level} data in {folder}. Download it first (see the top of this script).")
    gdf = gpd.read_file(files[0])
    if gdf.crs is None:
        gdf = gdf.set_crs(CRS)
    gdf = gdf.to_crs(CRS)
    minx, miny, maxx, maxy = gdf.total_bounds
    if -50 < minx < -30 and 160 < maxy < 180:  # latitude/longitude swapped by the source
        gdf["geometry"] = gdf.geometry.map(lambda g: g if g is None else _swap_xy(g))
    return gdf


def _swap_xy(geom):
    from shapely.ops import transform
    return transform(lambda x, y, z=None: (y, x), geom)


def fields(gdf: gpd.GeoDataFrame, level: str) -> tuple[str, str, str | None]:
    cols = {c.upper(): c for c in gdf.columns}
    code = next((cols[c] for c in cols if re.fullmatch(fr"{PREFIX[level]}\d{{4}}_V\d+_\d+", c)), None)
    if not code:
        raise SystemExit(f"Could not find the {PREFIX[level]} code column in the {level} file: {list(gdf.columns)}")
    name = cols.get(f"{code.upper()}_NAME")
    area = cols.get("LAND_AREA_SQ_KM") or cols.get("AREA_SQ_KM")
    return code, name, area


def clean_region_name(name: str) -> str:
    name = REGION_RENAMES.get(name, name)
    return re.sub(r"\s+Region$", "", name).strip()


def build_features(gdf, level) -> list[dict]:
    code_col, name_col, area_col = fields(gdf, level)
    out = []
    for _, row in gdf.iterrows():
        code, name = str(row[code_col]), str(row[name_col]).strip()
        if level == "ta" and code in SKIP_TA_CODES:
            continue
        if level == "sa2" and name.lower().startswith(SKIP_SA2_PREFIXES):
            continue
        geom = clean_geometry(row.geometry)
        if geom is None:
            continue
        minx, _, maxx, _ = geom.bounds
        if maxx - minx > 20:  # crosses the 180th meridian - not a crawlable land area as-is
            if level == "region" and name == OUTSIDE_REGION:
                geom = None  # replaced by the Chatham Islands council boundary in main()
            else:
                print(f"  skipping {name}: spans the 180th meridian")
                continue
        area = float(row[area_col]) if area_col and row[area_col] == row[area_col] else 0.0
        out.append({"name": clean_region_name(name) if level == "region" else name,
                    "code": code, "area_km2": area, "geometry": geom})
    return out


def assign_parent(children: list[dict], parents: list[dict], key: str, by_largest_overlap: bool) -> None:
    """Set child[key] to the name of the parent it lies in."""
    tree = STRtree([p["geometry"] for p in parents])
    for child in children:
        g = child["geometry"]
        if by_largest_overlap:
            best, best_area = None, 0.0
            for i in tree.query(g, predicate="intersects"):
                a = parents[int(i)]["geometry"].intersection(g).area
                if a > best_area:
                    best, best_area = parents[int(i)], a
        else:
            pt = g.representative_point()
            hits = tree.query(pt, predicate="intersects")
            best = parents[int(hits[0])] if len(hits) else None
        if best is None:
            best = parents[int(tree.query_nearest(g.representative_point())[0])]
        child[key] = best["name"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--download", action="store_true", help="download the layers using STATS_NZ_API_KEY")
    args = parser.parse_args()
    if args.download:
        from backend.config.settings import STATS_NZ_API_KEY
        if not STATS_NZ_API_KEY:
            raise SystemExit("Add STATS_NZ_API_KEY=your-key to .env first (see the top of this script).")
        download(STATS_NZ_API_KEY)

    regions = build_features(read_level("region"), "region")
    tas = build_features(read_level("ta"), "ta")
    sa2s = build_features(read_level("sa2"), "sa2")

    chatham = next((t for t in tas if t["name"] == CHATHAM_TA), None)
    for r in regions:
        if r["geometry"] is None and chatham:
            r["geometry"], r["area_km2"] = chatham["geometry"], chatham["area_km2"]
    regions = [r for r in regions if r["geometry"] is not None]
    print(f"regions: {len(regions)}, territorial authorities: {len(tas)}, SA2s: {len(sa2s)}")

    assign_parent(tas, regions, "state", by_largest_overlap=True)
    assign_parent(sa2s, tas, "ta", by_largest_overlap=False)
    assign_parent(sa2s, regions, "state", by_largest_overlap=False)
    for r in regions:
        r["state"] = r["name"]

    for level, items in (("region", regions), ("ta", tas), ("sa2", sa2s)):
        feats = []
        for it in sorted(items, key=lambda x: (x["state"], x["name"])):
            props = {"name": it["name"], "code": it["code"], "state": it["state"], "area_km2": round(it["area_km2"], 4)}
            if level == "sa2":
                props["ta"] = it["ta"]
            feats.append((props, it["geometry"]))
        write_boundaries(COUNTRY_DIR / "boundaries" / f"{level}.geojson.gz", feats, CRS)
        write_lookup(COUNTRY_DIR / "lookups" / f"state_to_{level}.json", feats)

    # The Nearby Search city list must use the same region names.
    cities_file = COUNTRY_DIR / "cities.json"
    if cities_file.exists():
        names = {r["name"] for r in regions}
        bad = sorted({c["state"] for c in json.loads(cities_file.read_text(encoding="utf-8"))} - names)
        if bad:
            print(f"  WARNING: cities.json uses region names not in the data: {bad}")


if __name__ == "__main__":
    main()
