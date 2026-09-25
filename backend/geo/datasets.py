"""
Country / boundary-level registry and area loading.

Each country exposes a few boundary "levels" (e.g. Australian LGAs or NZ
Territorial Authorities). Boundaries come from the processed files built by
`scripts/build_*_data.py` and are loaded once, then cached in memory.
"""
from __future__ import annotations

import difflib
import gzip
import json
import threading
from dataclasses import dataclass, field
from pathlib import Path

import shapely
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

from backend.config.settings import DATA_DIR
from backend.geo.tile_rules import AU_TILE_RULES, NZ_TILE_RULES, TileRules


@dataclass(frozen=True)
class Level:
    key: str        # "lga"
    label: str      # "Local Government Area (LGA)"
    short: str      # "LGA"


@dataclass(frozen=True)
class Country:
    code: str                   # "AU"
    name: str                   # "Australia"
    folder: str                 # "australia" (under data/)
    crs: str                    # CRS of the boundary coordinates
    state_label: str            # "State" (AU) / "Region" (NZ)
    levels: dict[str, Level]
    default_level: str          # level used by custom / full crawls by default
    council_level: str          # level used to label every lead with its council
    dense_level: str            # neighbourhood-sized level used by dense-city mode
    tile_rules: TileRules

    @property
    def data_dir(self) -> Path:
        return DATA_DIR / self.folder

    def boundary_file(self, level: str) -> Path:
        return self.data_dir / "boundaries" / f"{level}.geojson.gz"

    def lookup_file(self, level: str) -> Path:
        return self.data_dir / "lookups" / f"state_to_{level}.json"

    @property
    def cities_file(self) -> Path:
        return self.data_dir / "cities.json"

    def level(self, key: str) -> Level:
        key = (key or "").strip().lower()
        if key not in self.levels:
            raise GeoError(f"Unknown level '{key}' for {self.name}. Choose one of: {', '.join(self.levels)}")
        return self.levels[key]

    def has_data(self, level: str | None = None) -> bool:
        return self.boundary_file(level or self.default_level).exists()


COUNTRIES: dict[str, Country] = {
    "AU": Country(
        code="AU", name="Australia", folder="australia", crs="EPSG:7844", state_label="State",
        levels={
            "lga": Level("lga", "Local Government Area (LGA)", "LGA"),
            "sa2": Level("sa2", "Statistical Area Level 2 (SA2 - suburb sized)", "SA2"),
            "gccsa": Level("gccsa", "Greater Capital City Area (GCCSA)", "GCCSA"),
        },
        default_level="lga", council_level="lga", dense_level="sa2", tile_rules=AU_TILE_RULES,
    ),
    "NZ": Country(
        code="NZ", name="New Zealand", folder="new_zealand", crs="EPSG:4326", state_label="Region",
        levels={
            "ta": Level("ta", "Territorial Authority (District / City council)", "TA"),
            "sa2": Level("sa2", "Statistical Area 2 (SA2 - suburb sized)", "SA2"),
            "region": Level("region", "Regional Council area", "Region"),
        },
        default_level="ta", council_level="ta", dense_level="sa2", tile_rules=NZ_TILE_RULES,
    ),
}


class GeoError(ValueError):
    """A user-facing problem with a country, level or area name."""


def get_country(value: str) -> Country:
    """Accepts 'AU', 'au', 'Australia', 'NZ', 'New Zealand', ..."""
    v = (value or "").strip().lower()
    for country in COUNTRIES.values():
        if v in (country.code.lower(), country.name.lower()):
            return country
    raise GeoError(f"Unknown country '{value}'. Choose one of: {', '.join(c.name for c in COUNTRIES.values())}")


@dataclass
class Area:
    name: str
    code: str
    state: str
    area_km2: float
    level: str
    country: str               # country code
    props: dict
    geometry: object = field(repr=False)

    @property
    def key(self) -> str:
        return self.name.strip().lower()

    def to_dict(self) -> dict:
        return {"name": self.name, "code": self.code, "state": self.state,
                "area_km2": round(self.area_km2, 2), "level": self.level, "country": self.country}


class AreaSet:
    """All areas of one country+level, with name lookup and point location."""

    def __init__(self, country: Country, level: str, areas: list[Area]):
        self.country = country
        self.level = level
        self.areas = areas
        self._by_key: dict[str, list[Area]] = {}
        self._by_code: dict[str, Area] = {}
        for a in areas:
            self._by_key.setdefault(a.key, []).append(a)
            self._by_code[a.code] = a
        self._tree = STRtree([a.geometry for a in areas])

    def __len__(self) -> int:
        return len(self.areas)

    def states(self) -> list[str]:
        return sorted({a.state for a in self.areas}, key=str.lower)

    def in_state(self, state: str | None) -> list[Area]:
        if not state:
            return sorted(self.areas, key=lambda a: (a.state.lower(), a.name.lower()))
        s = state.strip().lower()
        return sorted((a for a in self.areas if a.state.lower() == s), key=lambda a: a.name.lower())

    def find(self, name: str, state: str | None = None) -> Area:
        """Find an area by name (case-insensitive). `state` disambiguates duplicates."""
        matches = self._by_key.get((name or "").strip().lower(), [])
        if state and len(matches) > 1:
            matches = [a for a in matches if a.state.lower() == state.strip().lower()] or matches
        if len(matches) == 1:
            return matches[0]
        label = self.country.levels[self.level].short
        if len(matches) > 1:
            states = ", ".join(sorted(a.state for a in matches))
            raise GeoError(f"'{name}' exists in several {self.country.state_label.lower()}s ({states}); please choose one.")
        suggestions = difflib.get_close_matches((name or "").strip().lower(), list(self._by_key), n=5, cutoff=0.6)
        hint = ""
        if suggestions:
            hint = " Did you mean: " + ", ".join(self._by_key[s][0].name for s in suggestions) + "?"
        raise GeoError(f"No {label} called '{name}' in {self.country.name}.{hint}")

    def by_code(self, code: str) -> Area:
        try:
            return self._by_code[str(code)]
        except KeyError:
            raise GeoError(f"No area with code '{code}' in {self.country.name} ({self.level}).") from None

    def search(self, text: str, limit: int = 20) -> list[Area]:
        t = (text or "").strip().lower()
        if not t:
            return []
        starts = [a for a in self.areas if a.key.startswith(t)]
        contains = [a for a in self.areas if t in a.key and not a.key.startswith(t)]
        return (sorted(starts, key=lambda a: a.name) + sorted(contains, key=lambda a: a.name))[:limit]

    def locate(self, lon: float, lat: float, max_distance_deg: float = 0.005) -> Area | None:
        """Area containing the point; else the nearest one within ~500 m; else None."""
        pt = Point(lon, lat)
        hits = self._tree.query(pt, predicate="intersects")
        if len(hits):
            return self.areas[int(min(hits))]
        nearest = self._tree.query_nearest(pt, max_distance=max_distance_deg)
        return self.areas[int(nearest[0])] if len(nearest) else None

    def overlapping(self, geom, min_share: float) -> list[Area]:
        """Areas that have at least `min_share` of their own area inside `geom`."""
        out = []
        for i in self._tree.query(geom, predicate="intersects"):
            a = self.areas[int(i)]
            own = a.geometry.area
            if own > 0 and a.geometry.intersection(geom).area / own >= min_share:
                out.append(a)
        return sorted(out, key=lambda a: a.name.lower())


_cache: dict[tuple[str, str], AreaSet] = {}
_lock = threading.Lock()


def load_areas(country: Country | str, level: str | None = None) -> AreaSet:
    """Load (once) and return every area of a country at a boundary level."""
    if isinstance(country, str):
        country = get_country(country)
    level = country.level(level or country.default_level).key
    key = (country.code, level)
    with _lock:
        if key in _cache:
            return _cache[key]
        path = country.boundary_file(level)
        if not path.exists():
            raise GeoError(
                f"Boundary data for {country.name} ({level}) is missing: {path}. "
                f"Run scripts/build_{country.folder}_data.py (see data/README.md)."
            )
        with gzip.open(path, "rt", encoding="utf-8") as f:
            fc = json.load(f)
        areas = []
        for feat in fc["features"]:
            p = feat["properties"]
            geom = shape(feat["geometry"])
            if not geom.is_valid:
                geom = geom.buffer(0)  # repair self-intersections
            areas.append(Area(
                name=p["name"], code=str(p.get("code", "")), state=p.get("state", ""),
                area_km2=float(p.get("area_km2") or 0), level=level, country=country.code,
                props=p, geometry=geom,
            ))
        shapely.prepare([a.geometry for a in areas])
        area_set = AreaSet(country, level, areas)
        _cache[key] = area_set
        return area_set


def load_lookup(country: Country | str, level: str | None = None) -> dict[str, list[str]]:
    """{state: [area names]} for pickers; falls back to the boundary file."""
    if isinstance(country, str):
        country = get_country(country)
    level = country.level(level or country.default_level).key
    path = country.lookup_file(level)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    lookup: dict[str, list[str]] = {}
    for a in load_areas(country, level).areas:
        lookup.setdefault(a.state, []).append(a.name)
    return {s: sorted(v, key=str.lower) for s, v in sorted(lookup.items())}


def load_cities(country: Country | str) -> list[dict]:
    """Major cities (name, state, lat, lng) used by Nearby Search."""
    if isinstance(country, str):
        country = get_country(country)
    if not country.cities_file.exists():
        return []
    return json.loads(country.cities_file.read_text(encoding="utf-8"))
