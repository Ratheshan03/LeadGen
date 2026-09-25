"""
Build LeadGen's Australian boundary data from the official ABS shapefiles.

Source: Australian Bureau of Statistics, ASGS Edition 3 digital boundary files
(GDA2020), licensed CC BY 4.0:
  https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files

Download these zips, and extract each into data/australia/source/<folder>/:
  LGA 2024   (Local Government Areas)            -> data/australia/source/lga/
  SA2 2021   (Statistical Areas Level 2)         -> data/australia/source/sa2/
  GCCSA 2021 (Greater Capital City Stat. Areas)  -> data/australia/source/gccsa/

Then run from the project root:
  python scripts/build_australia_data.py

Output (committed to the repo, read by the backend):
  data/australia/boundaries/{lga,sa2,gccsa}.geojson.gz
  data/australia/lookups/state_to_{lga,sa2,gccsa}.json
"""
from __future__ import annotations

import sys
from pathlib import Path

import pyogrio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geodata_common import DATA_DIR, clean_geometry, write_boundaries, write_lookup  # noqa: E402

COUNTRY_DIR = DATA_DIR / "australia"
CRS = "EPSG:7844"  # GDA2020 geographic, as published by the ABS

LEVELS = {
    "lga": {
        "shapefile": "lga/LGA_2024_AUST_GDA2020.shp",
        "props": lambda p: {
            "name": p["LGA_NAME24"], "code": p["LGA_CODE24"],
            "state": p["STE_NAME21"], "area_km2": p["AREASQKM"],
        },
    },
    "sa2": {
        "shapefile": "sa2/SA2_2021_AUST_GDA2020.shp",
        "props": lambda p: {
            "name": p["SA2_NAME21"], "code": p["SA2_CODE21"],
            "state": p["STE_NAME21"], "area_km2": p["AREASQKM21"],
            "sa3": p["SA3_NAME21"], "sa4": p["SA4_NAME21"], "gccsa": p["GCC_NAME21"],
        },
    },
    "gccsa": {
        "shapefile": "gccsa/GCCSA_2021_AUST_GDA2020.shp",
        "props": lambda p: {
            "name": p["GCC_NAME21"], "code": p["GCC_CODE21"],
            "state": p["STE_NAME21"], "area_km2": p["AREASQKM21"],
        },
    },
}


def build_level(level: str, spec: dict) -> None:
    path = COUNTRY_DIR / "source" / spec["shapefile"]
    if not path.exists():
        print(f"  !! missing {path} - download it first (see the top of this script)")
        return
    df = pyogrio.read_dataframe(path)
    features, skipped = [], 0
    for _, row in df.iterrows():
        geom = clean_geometry(row.geometry)
        if geom is None:  # "No usual address", "Migratory - Offshore - Shipping", ...
            skipped += 1
            continue
        props = spec["props"](row)
        props["area_km2"] = float(props["area_km2"] or 0)
        features.append((props, geom))
    print(f"{level}: {len(features)} areas ({skipped} non-geographic entries skipped)")
    write_boundaries(COUNTRY_DIR / "boundaries" / f"{level}.geojson.gz", features, CRS)
    write_lookup(COUNTRY_DIR / "lookups" / f"state_to_{level}.json", features)


def main() -> None:
    for level, spec in LEVELS.items():
        build_level(level, spec)


if __name__ == "__main__":
    main()
