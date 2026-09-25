"""
Tile generation: cover an area with rectangles ("tiles") for Google Text Search.

Standard mode reproduces LeadGen's original tiling exactly:
  * sparse giant  (huge + flagged remote)       -> one bounding-box tile
  * small / compact area                        -> one tile (bbox + small buffer)
  * otherwise                                   -> grid of tile_km squares
  * elongated area the grid missed              -> 1-2 fallback strips
Tile size comes from TileRules (area buckets + low-density keywords).

Dense-city mode (optional) crawls the area as its SA2 neighbourhoods instead,
so busy city centres get small tiles and are not cut off at Google's 60-result
limit, while rural parts keep large tiles.
"""
from __future__ import annotations

import re
from functools import lru_cache

import shapely
from pyproj import Transformer
from shapely.geometry import box
from shapely.ops import transform

from backend.geo.datasets import Area, Country, load_areas

# Share of an SA2 that must lie inside the target area for dense-city mode.
DENSE_MIN_SHARE = 0.2


@lru_cache(maxsize=None)
def _transformers(crs: str):
    fwd = Transformer.from_crs(crs, "EPSG:3857", always_xy=True).transform
    rev = Transformer.from_crs("EPSG:3857", crs, always_xy=True).transform
    return fwd, rev


def _slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") or "area"


def tile_size_km(area: Area, country: Country) -> float:
    """Pick the tile size (km) for an area. Original LeadGen rules."""
    rules = country.tile_rules
    name = area.key
    parent = (area.props.get("sa4") or "").lower()
    if any(k in name or k in parent for k in rules.low_density_keywords):
        return rules.max_tile_km
    capital_region = (area.props.get("gccsa") or (area.name if area.level == "gccsa" else "")).lower()
    if capital_region in rules.fine_tile_regions:
        return 5 if 0 < area.area_km2 < 5000 else 10
    for lo, hi, size in rules.size_buckets:
        if lo <= area.area_km2 < hi:
            return size
    return 25


def _tile(area: Area, name_suffix: str, bounds_wgs, **extra) -> dict:
    lon_min, lat_min, lon_max, lat_max = bounds_wgs
    return {
        "area": area.name, "state": area.state, "country": area.country, "level": area.level,
        "tile_name": f"{_slug(area.name)}_{name_suffix}",
        "low": {"latitude": round(lat_min, 6), "longitude": round(lon_min, 6)},
        "high": {"latitude": round(lat_max, 6), "longitude": round(lon_max, 6)},
        **extra,
    }


def standard_tiles(area: Area, country: Country, tile_km: float | None = None) -> list[dict]:
    """Original LeadGen tiling for one area."""
    rules = country.tile_rules
    tile_km = tile_km or tile_size_km(area, country)
    project, reverse = _transformers(country.crs)

    tile_size_m = tile_km * 1000
    geom_m = transform(project, area.geometry)
    min_x, min_y, max_x, max_y = geom_m.bounds
    area_km2 = area.area_km2 if area.area_km2 > 0 else geom_m.area / 1e6

    def wgs(bx):
        return transform(reverse, bx).bounds

    # Case 0: sparse giant -> one bounding-box tile
    if area_km2 >= rules.sparse_giant_area_km2 and area.key in rules.low_density_areas:
        return [_tile(area, "sparse_single", wgs(box(min_x, min_y, max_x, max_y)))]

    # Cases 1-2: small or compact -> one tile with a small buffer
    bbox_diag_km = max((max_x - min_x) / 1000, (max_y - min_y) / 1000)
    if area_km2 <= (tile_km ** 2) * 1.5 or bbox_diag_km <= tile_km * 3:
        buffer = tile_size_m * (0.1 if area_km2 < 200 else 0.02)
        return [_tile(area, "single", wgs(box(min_x - buffer, min_y - buffer, max_x + buffer, max_y + buffer)))]

    # Case 3: grid tiling, keeping tiles that overlap the area enough
    tiles, seen = [], set()
    min_overlap = 0.2 if area_km2 < 500 else 0.3
    shapely.prepare(geom_m)  # fast intersects/contains checks below
    row, x = 0, min_x
    while x < max_x:
        col, y = 0, min_y
        while y < max_y:
            tile_box = box(x, y, x + tile_size_m, y + tile_size_m)
            if not geom_m.intersects(tile_box):
                ratio = 0.0
            elif geom_m.contains(tile_box):
                ratio = 1.0
            else:  # edge tile: measure the overlap
                ratio = shapely.clip_by_rect(geom_m, x, y, x + tile_size_m, y + tile_size_m).area / tile_box.area
            if ratio >= min_overlap:
                t = _tile(area, f"r{row}_c{col}", wgs(tile_box))
                k = (t["low"]["latitude"], t["low"]["longitude"], t["high"]["latitude"], t["high"]["longitude"])
                if k not in seen:
                    seen.add(k)
                    tiles.append(t)
            col += 1
            y += tile_size_m
        row += 1
        x += tile_size_m

    # Case 4: elongated area the grid missed -> 1-2 strips
    if not tiles:
        lon_min, lat_min, lon_max, lat_max = wgs(box(min_x, min_y, max_x, max_y))
        width, height = lon_max - lon_min, lat_max - lat_min
        splits = 2 if max(width, height) / min(width, height) > 3 else 1
        for i in range(splits):
            if height > width:
                strip = box(min_x, min_y + i * (max_y - min_y) / splits, max_x, min_y + (i + 1) * (max_y - min_y) / splits)
            else:
                strip = box(min_x + i * (max_x - min_x) / splits, min_y, min_x + (i + 1) * (max_x - min_x) / splits, max_y)
            tiles.append(_tile(area, f"fallback_{i}", wgs(strip)))
    return tiles


def dense_tiles(area: Area, country: Country) -> list[dict]:
    """Dense-city mode: one tight tile per SA2 neighbourhood inside the area."""
    if area.level == country.dense_level:
        return standard_tiles(area, country)
    subs = load_areas(country, country.dense_level).overlapping(area.geometry, DENSE_MIN_SHARE)
    if not subs:
        return standard_tiles(area, country)

    rules = country.tile_rules
    project, reverse = _transformers(country.crs)
    tiles = []
    for sub in subs:
        if sub.area_km2 < rules.dense_small_area_km2:
            b = rules.dense_tile_buffer_m
            min_x, min_y, max_x, max_y = transform(project, sub.geometry).bounds
            bounds = transform(reverse, box(min_x - b, min_y - b, max_x + b, max_y + b)).bounds
            sub_tiles = [_tile(sub, "dense", bounds)]
        else:
            sub_tiles = standard_tiles(sub, country)
        for t in sub_tiles:
            t.update(area=area.name, state=area.state, level=area.level, sub_area=sub.name)
        tiles.extend(sub_tiles)
    return tiles


def tiles_for_area(area: Area, country: Country, dense: bool = False) -> list[dict]:
    return dense_tiles(area, country) if dense else standard_tiles(area, country)


def split_tile_longer_side(tile: dict) -> list[dict]:
    """
    Split a tile into two halves across its longer side (by degree span).
    Used when a tile hits Google's 60-result cap: the halves are re-crawled to
    recover the businesses Google cut off. Returns [] for a degenerate tile.
    """
    low, high = tile.get("low", {}), tile.get("high", {})
    lat_min, lat_max = low.get("latitude"), high.get("latitude")
    lon_min, lon_max = low.get("longitude"), high.get("longitude")
    if None in (lat_min, lat_max, lon_min, lon_max):
        return []
    lat_span, lon_span = lat_max - lat_min, lon_max - lon_min
    if lat_span <= 0 or lon_span <= 0:
        return []

    if lat_span >= lon_span:
        mid = (lat_min + lat_max) / 2
        halves = [(lat_min, mid, lon_min, lon_max), (mid, lat_max, lon_min, lon_max)]
    else:
        mid = (lon_min + lon_max) / 2
        halves = [(lat_min, lat_max, lon_min, mid), (lat_min, lat_max, mid, lon_max)]

    name = tile.get("tile_name", "tile")
    out = []
    for i, (a_lat, b_lat, a_lon, b_lon) in enumerate(halves):
        out.append({
            **{k: v for k, v in tile.items() if k not in ("low", "high", "tile_name")},
            "tile_name": f"{name}_h{i}",
            "low": {"latitude": round(a_lat, 6), "longitude": round(a_lon, 6)},
            "high": {"latitude": round(b_lat, 6), "longitude": round(b_lon, 6)},
        })
    return out
