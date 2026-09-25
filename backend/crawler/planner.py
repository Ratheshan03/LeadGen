"""
Turns a crawl request into a concrete plan: which areas (or cities) and which
business types. Shared by the cost estimate and the job runner so both always
agree.

Request fields (all optional except where noted):
    mode            "area" | "state" | "full" | "nearby"     (required)
    country         "AU" / "Australia" / "NZ" / "New Zealand" (default AU)
    level           boundary level, e.g. "lga", "sa2", "ta"   (default: country default)
    state           state / region name                       (area, state, nearby)
    area            area name                                 (mode=area)
    areas           list of area names within `state`         (mode=state, optional subset)
    states          list of states                            (mode=full, optional subset)
    business_types  "ALL", a category, a type, or a list      (default ALL)
    dense           dense-city mode                           (default False)
    skip_completed  skip areas already crawled with the same settings (state/full, default True)
    cities          list of city names                        (mode=nearby, default all in state/country)
    radius_m        Nearby Search radius in metres            (default 5000)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from backend.config.business_types import get_business_types
from backend.crawler.engine import types_key
from backend.geo.datasets import Area, Country, GeoError, get_country, load_areas, load_cities
from backend.storage import LeadStore

MODES = ("area", "state", "full", "nearby")


@dataclass
class CrawlPlan:
    mode: str
    country: Country
    level: str
    business_types: list[str]
    types_label: str
    types_key: str
    dense: bool = False
    areas: list[Area] = field(default_factory=list)
    cities: list[dict] = field(default_factory=list)
    radius_m: int = 5000
    skipped: list[str] = field(default_factory=list)

    @property
    def title(self) -> str:
        if self.mode == "nearby":
            where = self.cities[0]["name"] if len(self.cities) == 1 else f"{len(self.cities)} cities"
            return f"Nearby Search - {where} ({self.types_label})"
        if self.mode == "area" and self.areas:
            return f"{self.areas[0].name}, {self.areas[0].state} ({self.types_label})"
        states = sorted({a.state for a in self.areas})
        where = states[0] if len(states) == 1 else f"{self.country.name}"
        return f"{where} - {len(self.areas)} areas ({self.types_label})"


def _types_label(requested, resolved: list[str], all_types: list[str]) -> str:
    if sorted(resolved) == sorted(all_types):
        return "ALL"
    if isinstance(requested, str):
        return requested.strip()
    if isinstance(requested, (list, tuple)) and len(requested) == 1:
        return str(requested[0]).strip()
    return f"{len(resolved)}-types"


def build_plan(req: dict, store: LeadStore | None = None) -> CrawlPlan:
    mode = (req.get("mode") or "").strip().lower()
    if mode not in MODES:
        raise GeoError(f"Unknown crawl mode '{mode}'. Use one of: {', '.join(MODES)}")
    country = get_country(req.get("country") or "AU")
    bt = get_business_types()
    requested = req.get("business_types") or "ALL"
    types = bt.resolve(requested)  # any Google place type is accepted, not just the configured ones
    if not types:
        raise GeoError("No business types selected.")
    label = _types_label(requested, types, bt.all_types)
    plan = CrawlPlan(mode=mode, country=country, level=country.level(req.get("level") or country.default_level).key,
                     business_types=types, types_label=label, types_key=types_key(types, bt.all_types),
                     dense=bool(req.get("dense")), radius_m=int(req.get("radius_m") or 5000))

    if mode == "nearby":
        cities = load_cities(country)
        if req.get("state"):
            cities = [c for c in cities if c["state"].lower() == req["state"].strip().lower()]
        wanted = [c.strip().lower() for c in (req.get("cities") or []) if c and c.strip()]
        if wanted:
            cities = [c for c in cities if c["name"].lower() in wanted]
        if not cities:
            raise GeoError("No matching cities for Nearby Search.")
        plan.cities = cities
        return plan

    areas_set = load_areas(country, plan.level)
    if mode == "area":
        if not req.get("area"):
            raise GeoError("Please choose an area.")
        plan.areas = [areas_set.find(req["area"], req.get("state"))]
        return plan

    if mode == "state":
        if not req.get("state"):
            raise GeoError(f"Please choose a {country.state_label.lower()}.")
        candidates = areas_set.in_state(req["state"])
        if not candidates:
            raise GeoError(f"No areas found in '{req['state']}' for {country.name}. "
                           f"Valid {country.state_label.lower()}s: {', '.join(areas_set.states())}")
        if req.get("areas"):
            wanted = {a.strip().lower() for a in req["areas"]}
            candidates = [a for a in candidates if a.key in wanted]
    else:  # full
        states = {s.strip().lower() for s in (req.get("states") or []) if s and s.strip()}
        candidates = [a for a in areas_set.in_state(None) if not states or a.state.lower() in states]

    if req.get("skip_completed", True) and store is not None:
        done = store.completed_areas(country.code, plan.level, plan.types_key, plan.dense)
        plan.skipped = [f"{a.name}, {a.state}" for a in candidates if (a.state, a.name) in done]
        candidates = [a for a in candidates if (a.state, a.name) not in done]
    plan.areas = candidates
    return plan
