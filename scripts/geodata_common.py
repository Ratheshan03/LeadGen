"""
Shared helpers for the boundary-data build scripts.

Every country's boundaries are converted into the same compact format so the
crawler can treat Australia and New Zealand identically:

    data/<country>/boundaries/<level>.geojson.gz
        FeatureCollection, one Feature per area, with normalised properties:
            name      area name, original spelling (e.g. "Walkerville")
            code      official statistical code
            state     parent state / region name
            area_km2  land area in km²
            ...       optional extra parents (e.g. sa4, gccsa for AU SA2s)
    data/<country>/lookups/state_to_<level>.json
        {"<state>": ["<area>", ...]}  sorted, used by the pickers

Geometry is simplified with a ~1 m tolerance and coordinates are rounded to
6 decimals (~0.1 m). That shrinks the files ~10x while keeping boundaries
accurate to about a metre.
"""
from __future__ import annotations

import gzip
import json
import os
from pathlib import Path

import shapely
from shapely import to_geojson

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"

SIMPLIFY_TOLERANCE_DEG = 0.00001  # ~1.1 m
COORD_PRECISION = 6               # ~0.1 m


def clean_geometry(geom):
    """Simplify, round and repair a geometry. Returns None for empty input."""
    if geom is None or geom.is_empty:
        return None
    geom = shapely.simplify(geom, SIMPLIFY_TOLERANCE_DEG, preserve_topology=True)
    geom = shapely.set_precision(geom, 10 ** -COORD_PRECISION)
    if not geom.is_valid:
        geom = geom.buffer(0)  # same repair the crawler has always applied
    return None if geom.is_empty else geom


def write_boundaries(path: Path, features: list[tuple[dict, object]], crs: str) -> None:
    """Write [(properties, geometry), ...] as a gzipped GeoJSON FeatureCollection."""
    path.parent.mkdir(parents=True, exist_ok=True)
    parts = []
    for props, geom in features:
        parts.append(
            '{"type":"Feature","properties":' + json.dumps(props, ensure_ascii=False)
            + ',"geometry":' + to_geojson(geom) + "}"
        )
    header = '{"type":"FeatureCollection","crs":{"type":"name","properties":{"name":"' + crs + '"}},"features":['
    payload = (header + ",".join(parts) + "]}").encode("utf-8")
    tmp = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(tmp, "wb", compresslevel=6) as f:
        f.write(payload)
    os.replace(tmp, path)
    print(f"  wrote {path.relative_to(ROOT_DIR)}  ({len(features)} areas, {path.stat().st_size / 1e6:.1f} MB)")


def write_lookup(path: Path, features: list[tuple[dict, object]]) -> None:
    """Write {"state": [sorted area names]} for the pickers."""
    lookup: dict[str, list[str]] = {}
    for props, _ in features:
        lookup.setdefault(props["state"], []).append(props["name"])
    lookup = {state: sorted(set(names), key=str.lower) for state, names in sorted(lookup.items())}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lookup, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT_DIR)}  ({len(lookup)} states/regions)")
