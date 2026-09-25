"""
Crawl orchestration.

crawl_area()    one area (council / SA2 / capital region), one or ALL types
crawl_nearby()  Nearby Search around city centres
estimate()      tiles / requests / cost for a planned crawl, without calling Google

Every lead found is labelled with the council and SA2 it is actually located
in (from its coordinates) and saved to storage. The Excel file for an area
lists only the businesses inside that area; businesses found just across the
border are still saved under their own council.
"""
from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from functools import lru_cache

from backend.config import settings
from backend.crawler import export
from backend.crawler.places import PlacesClient, PlacesError, parse_place
from backend.geo.datasets import Area, Country, get_country, load_areas
from backend.geo.tiling import split_tile_longer_side, tiles_for_area
from backend.storage import INSERTED, LeadFilter, LeadStore

log = logging.getLogger("leadgen.crawler")

# A tile returning Google's full 60 in-bounds results (3 pages) is probably
# hiding more businesses, so it is split in half and each half re-crawled.
# Depth 2 = at most two rounds of splitting (quarters).
MAX_SATURATION_DEPTH = 2
SATURATION_MIN_RESULTS = 60

COMPLETED, QUOTA_REACHED, CANCELLED, FAILED = "completed", "quota_reached", "cancelled", "failed"


class Reporter:
    """Receives progress from a crawl. The job runner overrides these."""

    def log(self, message: str, level: int = logging.INFO) -> None:
        log.log(level, message)

    def progress(self, done: int, total: int, current: str = "") -> None:
        pass

    def cancelled(self) -> bool:
        return False


@dataclass
class AreaResult:
    country: str
    level: str
    state: str
    area: str
    status: str = COMPLETED
    tiles: int = 0
    business_types: int = 0
    requests: int = 0
    leads_found: int = 0          # inside the area
    leads_new: int = 0            # first time ever seen (inside the area)
    leads_outside: int = 0        # found in neighbouring areas (saved, not in this Excel)
    failures: list = field(default_factory=list)
    by_type: dict = field(default_factory=dict)
    excel_file: str | None = None
    map_file: str | None = None
    duration_s: float = 0.0
    error: str | None = None

    @property
    def cost_usd(self) -> float:
        return round(self.requests / 1000 * settings.COST_PER_1000_REQUESTS_USD, 2)

    def to_dict(self) -> dict:
        return {**asdict(self), "cost_usd": self.cost_usd}


# ---------------------------------------------------------------- tiles ----
@lru_cache(maxsize=4096)
def _cached_tiles(country_code: str, level: str, area_code: str, dense: bool) -> tuple:
    country = get_country(country_code)
    area = load_areas(country, level).by_code(area_code)
    return tuple(tiles_for_area(area, country, dense))


def area_tiles(country: Country, area: Area, dense: bool = False) -> list[dict]:
    """Tiles for an area (cached - tiling a big area can take a few seconds)."""
    return list(_cached_tiles(country.code, area.level, area.code, bool(dense)))


# ------------------------------------------------------------- labelling ---
class Labeler:
    """Finds the council / SA2 / state each lead is really in."""

    def __init__(self, country: Country):
        self.country = country
        self.councils = load_areas(country, country.council_level)
        self.sa2s = load_areas(country, country.dense_level)
        self._other: dict[str, object] = {}

    def label(self, lead: dict, fallback_state: str) -> None:
        lat, lon = lead.get("latitude"), lead.get("longitude")
        council = sa2 = None
        if lat is not None and lon is not None:
            council = self.councils.locate(lon, lat)
            sa2 = self.sa2s.locate(lon, lat)
        lead["country"] = self.country.name
        lead["council"] = council.name if council else None
        lead["sa2"] = sa2.name if sa2 else None
        lead["state"] = council.state if council else (sa2.state if sa2 else fallback_state)

    def in_area(self, lead: dict, area: Area) -> bool:
        """True if the lead lies in `area` (or in no known area at all)."""
        if area.level == self.country.council_level:
            located = lead.get("council")
        elif area.level == self.country.dense_level:
            located = lead.get("sa2")
        else:
            areas = self._other.get(area.level) or load_areas(self.country, area.level)
            self._other[area.level] = areas
            hit = None
            if lead.get("latitude") is not None:
                hit = areas.locate(lead["longitude"], lead["latitude"])
            located = hit.name if hit else None
        return located is None or located == area.name


# -------------------------------------------------------------- crawling ---
def crawl_tile(client: PlacesClient, query: str, tile: dict, reporter: Reporter, depth: int = 0):
    """Crawl one tile, splitting it (up to MAX_SATURATION_DEPTH) while Google's 60-result cap is hit."""
    data = client.text_search(query, tile)
    results = list(data["results"])
    requests_made, quota_hit, pages = data["requests_made"], data["quota_exceeded"], data["pages_fetched"]
    saturated = pages >= 3 and len(results) >= SATURATION_MIN_RESULTS
    if saturated and not quota_hit and depth < MAX_SATURATION_DEPTH:
        halves = split_tile_longer_side(tile)
        if halves:
            reporter.log(f"      '{query}': tile {tile.get('tile_name')} hit Google's 60-result limit - splitting it in two")
            for half in halves:
                sub_results, sub_requests, sub_quota, _ = crawl_tile(client, query, half, reporter, depth + 1)
                requests_made += sub_requests
                results.extend(sub_results)
                if sub_quota:
                    quota_hit = True
                    break
    if depth == 0:
        unique = {}
        for r in results:
            unique.setdefault(r.get("id"), r)
        results = [r for k, r in unique.items() if k]
    return results, requests_made, quota_hit, pages


def types_key(business_types: list[str], all_types: list[str]) -> str:
    return "ALL" if sorted(business_types) == sorted(all_types) else ",".join(sorted(business_types))


def crawl_area(*, client: PlacesClient, store: LeadStore, country: Country, area: Area, business_types: list[str],
               types_label: str, dense: bool = False, reporter: Reporter | None = None, job_id: str | None = None,
               mode: str = "area") -> AreaResult:
    reporter = reporter or Reporter()
    started = time.time()
    tiles = area_tiles(country, area, dense)
    result = AreaResult(country=country.name, level=area.level, state=area.state, area=area.name,
                        tiles=len(tiles), business_types=len(business_types))
    run_id = store.start_run({"job_id": job_id, "mode": mode, "country": country.code, "level": area.level,
                              "state": area.state, "area": area.name, "business_types": types_label,
                              "dense": dense, "tiles": len(tiles)})
    labeler = Labeler(country)
    found: dict[str, dict] = {}
    new_ids: set[str] = set()

    mode_note = " (dense-city mode)" if dense else ""
    reporter.log(f"Crawling {area.name}, {area.state} - {len(tiles)} tile(s){mode_note}, {len(business_types)} business type(s)")
    try:
        for index, btype in enumerate(business_types, 1):
            if reporter.cancelled():
                result.status = CANCELLED
                break
            reporter.progress(index - 1, len(business_types), btype)
            t_found, t_new, t_requests = set(), 0, 0
            for tile in tiles:
                try:
                    places, requests_made, quota_hit, _ = crawl_tile(client, btype, tile, reporter)
                except PlacesError:
                    raise
                except Exception as exc:  # one bad tile must not stop the crawl
                    result.failures.append({"business_type": btype, "tile": tile.get("tile_name"), "error": str(exc)})
                    reporter.log(f"    error in tile {tile.get('tile_name')} for '{btype}': {exc}", logging.WARNING)
                    continue
                t_requests += requests_made
                for place in places:
                    lead = parse_place(place)
                    if not lead["place_id"]:
                        continue
                    labeler.label(lead, fallback_state=area.state)
                    lead["source"] = "text_search"
                    if store.upsert_lead(lead, btype) == INSERTED:
                        new_ids.add(lead["place_id"])
                        t_new += 1
                    found[lead["place_id"]] = lead
                    t_found.add(lead["place_id"])
                if quota_hit:
                    result.status = QUOTA_REACHED
                    break
            result.requests += t_requests
            result.by_type[btype] = len(t_found)
            reporter.log(f"  [{index}/{len(business_types)}] {btype:<34} {len(t_found):>5} found  {t_new:>5} new  "
                         f"{t_requests:>4} requests")
            if result.status == QUOTA_REACHED:
                reporter.log("Monthly request cap reached - stopping. Results so far are saved.", logging.WARNING)
                break
        else:
            reporter.progress(len(business_types), len(business_types), "")
    except PlacesError as exc:
        result.status, result.error = FAILED, str(exc)
        reporter.log(str(exc), logging.ERROR)

    inside = [pid for pid, lead in found.items() if labeler.in_area(lead, area)]
    result.leads_found = len(inside)
    result.leads_new = len(new_ids.intersection(inside))
    result.leads_outside = len(found) - len(inside)
    result.duration_s = round(time.time() - started, 1)

    if inside:
        leads = fetch_leads(store, inside)
        paths = export.area_output_paths(country, area, types_label, dense)
        export.write_area_excel(paths["excel"], leads, area, country, result, types_label, dense)
        export.write_area_map(paths["map"], area, tiles, leads)
        result.excel_file, result.map_file = str(paths["excel"]), str(paths["map"])

    store.finish_run(run_id, {"status": result.status, "requests": result.requests, "leads_found": result.leads_found,
                              "leads_new": result.leads_new, "excel_file": result.excel_file, "error": result.error})
    reporter.log(
        f"Done: {result.leads_found} businesses in {area.name} ({result.leads_new} new), "
        f"{result.leads_outside} in neighbouring areas, {result.requests} requests (~${result.cost_usd}), "
        f"{result.duration_s:.0f}s"
    )
    return result


def fetch_leads(store: LeadStore, place_ids: list[str]) -> list[dict]:
    leads = []
    for i in range(0, len(place_ids), 900):
        leads.extend(store.query_leads(LeadFilter(place_ids=place_ids[i:i + 900]), limit=None)[1])
    return sorted(leads, key=lambda l: ((l.get("name") or "").lower(), l["place_id"]))


def crawl_nearby(*, client: PlacesClient, store: LeadStore, country: Country, city: dict, business_types: list[str],
                 types_label: str, radius_m: int = 5000, reporter: Reporter | None = None,
                 job_id: str | None = None) -> AreaResult:
    """Nearby Search: up to 20 places per business type within radius_m of a city centre."""
    reporter = reporter or Reporter()
    started = time.time()
    result = AreaResult(country=country.name, level="city", state=city["state"], area=city["name"],
                        tiles=1, business_types=len(business_types))
    run_id = store.start_run({"job_id": job_id, "mode": "nearby", "country": country.code, "level": "city",
                              "state": city["state"], "area": city["name"], "business_types": types_label, "tiles": 1})
    labeler = Labeler(country)
    found: dict[str, dict] = {}
    new_ids: set[str] = set()
    reporter.log(f"Nearby Search around {city['name']}, {city['state']} (radius {radius_m / 1000:g} km), "
                 f"{len(business_types)} business type(s)")
    try:
        for index, btype in enumerate(business_types, 1):
            if reporter.cancelled():
                result.status = CANCELLED
                break
            reporter.progress(index - 1, len(business_types), btype)
            data = client.nearby_search(btype, city["lat"], city["lng"], radius_m)
            result.requests += data["requests_made"]
            t_new = 0
            for place in data["results"]:
                lead = parse_place(place)
                labeler.label(lead, fallback_state=city["state"])
                lead["source"] = "nearby_search"
                if store.upsert_lead(lead, btype) == INSERTED:
                    new_ids.add(lead["place_id"])
                    t_new += 1
                found[lead["place_id"]] = lead
            result.by_type[btype] = len(data["results"])
            reporter.log(f"  [{index}/{len(business_types)}] {btype:<34} {len(data['results']):>5} found  {t_new:>5} new")
            if data["quota_exceeded"]:
                result.status = QUOTA_REACHED
                reporter.log("Monthly request cap reached - stopping. Results so far are saved.", logging.WARNING)
                break
        else:
            reporter.progress(len(business_types), len(business_types), "")
    except PlacesError as exc:
        result.status, result.error = FAILED, str(exc)
        reporter.log(str(exc), logging.ERROR)

    result.leads_found, result.leads_new = len(found), len(new_ids)
    result.duration_s = round(time.time() - started, 1)
    if found:
        leads = fetch_leads(store, list(found))
        paths = export.city_output_paths(country, city, types_label)
        export.write_area_excel(paths["excel"], leads, None, country, result, types_label, False, city=city,
                                radius_m=radius_m)
        export.write_city_map(paths["map"], city, radius_m, leads)
        result.excel_file, result.map_file = str(paths["excel"]), str(paths["map"])
    store.finish_run(run_id, {"status": result.status, "requests": result.requests, "leads_found": result.leads_found,
                              "leads_new": result.leads_new, "excel_file": result.excel_file, "error": result.error})
    reporter.log(f"Done: {result.leads_found} businesses near {city['name']} ({result.leads_new} new), "
                 f"{result.requests} requests (~${result.cost_usd})")
    return result


# -------------------------------------------------------------- estimate ---
def estimate(country: Country, areas: list[Area], business_types: list[str], dense: bool = False) -> dict:
    tiles = sum(len(area_tiles(country, a, dense)) for a in areas)
    minimum = tiles * len(business_types)
    price = settings.COST_PER_1000_REQUESTS_USD
    return {
        "areas": len(areas), "tiles": tiles, "business_types": len(business_types),
        "min_requests": minimum, "min_cost_usd": round(minimum / 1000 * price, 2),
        "likely_max_requests": minimum * 4, "likely_max_cost_usd": round(minimum * 4 / 1000 * price, 2),
        "note": ("Each tile needs at least 1 request per business type. Busy areas need extra pages and "
                 "saturation splits, typically up to ~4x the minimum."),
    }
