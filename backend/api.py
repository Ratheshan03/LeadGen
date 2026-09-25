"""HTTP API used by custom_crawl.py, full_crawl.py and the dashboard."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.config import settings
from backend.config.business_types import BusinessTypesError, get_business_types
from backend.crawler import export
from backend.crawler.engine import estimate
from backend.crawler.planner import build_plan
from backend.geo.datasets import COUNTRIES, GeoError, get_country, load_areas, load_cities, load_lookup
from backend.storage import LeadFilter, get_store

router = APIRouter(prefix="/api")

# Set by backend.main at startup.
jobs = None
quota = None


class CrawlRequest(BaseModel):
    mode: Literal["area", "state", "full", "nearby"]
    country: str = "AU"
    level: str | None = None
    state: str | None = None
    area: str | None = None
    areas: list[str] | None = None
    states: list[str] | None = None
    business_types: str | list[str] = "ALL"
    dense: bool = False
    skip_completed: bool = True
    cities: list[str] | None = None
    radius_m: int = Field(5000, ge=100, le=50000)


def _plan(req: CrawlRequest):
    try:
        return build_plan(req.model_dump(), get_store())
    except (GeoError, BusinessTypesError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


def _country(value: str):
    try:
        return get_country(value)
    except GeoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


# ------------------------------------------------------------------ status --
@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/status")
def status():
    store = get_store()
    active = jobs.active() if jobs else None
    return {
        "storage": store.describe(),
        "total_leads": store.count(),
        "quota": quota.status(),
        "google_keys_configured": len(settings.GOOGLE_API_KEYS),
        "cost_per_1000_requests_usd": settings.COST_PER_1000_REQUESTS_USD,
        "output_folder": str(settings.OUTPUT_DIR),
        "countries": [{"code": c.code, "name": c.name, "has_data": c.has_data()} for c in COUNTRIES.values()],
        "active_job": active.to_dict(since=10**9) if active else None,
    }


@router.get("/meta")
def meta():
    try:
        bt = get_business_types()
    except BusinessTypesError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from None
    return {
        "countries": [{
            "code": c.code, "name": c.name, "state_label": c.state_label, "default_level": c.default_level,
            "has_data": c.has_data(),
            "levels": [{"key": lv.key, "label": lv.label, "short": lv.short, "has_data": c.has_data(lv.key)}
                       for lv in c.levels.values()],
        } for c in COUNTRIES.values()],
        "business_types": {"categories": bt.categories, "all": bt.all_types},
    }


# ------------------------------------------------------------------- areas --
@router.get("/areas")
def areas(country: str = "AU", level: str | None = None, state: str | None = None):
    c = _country(country)
    try:
        area_set = load_areas(c, level)
    except GeoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return [a.to_dict() for a in area_set.in_state(state)]


@router.get("/areas/lookup")
def areas_lookup(country: str = "AU", level: str | None = None):
    """{state: [area names]} for pickers."""
    c = _country(country)
    try:
        return load_lookup(c, level)
    except GeoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.get("/areas/search")
def areas_search(q: str, country: str = "AU", level: str | None = None, limit: int = Query(20, le=100)):
    c = _country(country)
    try:
        return [a.to_dict() for a in load_areas(c, level).search(q, limit)]
    except GeoError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.get("/cities")
def cities(country: str = "AU", state: str | None = None):
    items = load_cities(_country(country))
    if state:
        items = [c for c in items if c["state"].lower() == state.strip().lower()]
    return items


# ------------------------------------------------------------------- crawl --
@router.post("/crawl/estimate")
def crawl_estimate(req: CrawlRequest):
    plan = _plan(req)
    if plan.mode == "nearby":
        n = len(plan.cities) * len(plan.business_types)
        est = {"areas": len(plan.cities), "tiles": len(plan.cities), "business_types": len(plan.business_types),
               "min_requests": n, "min_cost_usd": round(n / 1000 * settings.COST_PER_1000_REQUESTS_USD, 2),
               "likely_max_requests": n, "likely_max_cost_usd": round(n / 1000 * settings.COST_PER_1000_REQUESTS_USD, 2),
               "note": "Nearby Search uses 1 request per business type per city (up to 20 results each)."}
    else:
        est = estimate(plan.country, plan.areas, plan.business_types, plan.dense)
    return {**est, "title": plan.title, "types_label": plan.types_label, "skipped": plan.skipped,
            "areas_list": [f"{a.name}, {a.state}" for a in plan.areas][:2000],
            "quota": quota.status()}


@router.post("/crawl/jobs")
def crawl_start(req: CrawlRequest):
    plan = _plan(req)
    if not plan.areas and not plan.cities:
        raise HTTPException(status_code=400, detail="Nothing to crawl - every area in this selection is already done "
                                                    "(set skip_completed to false to crawl again).")
    return jobs.submit(req.model_dump(), plan).to_dict()


@router.get("/crawl/jobs")
def crawl_jobs():
    return [j.to_dict(since=10**9) for j in jobs.list()]


@router.get("/crawl/jobs/{job_id}")
def crawl_job(job_id: str, since: int = 0):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found (the backend may have been restarted).")
    return job.to_dict(since=since)


@router.post("/crawl/jobs/{job_id}/cancel")
def crawl_cancel(job_id: str):
    job = jobs.cancel(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job.to_dict(since=10**9)


@router.get("/crawl/history")
def crawl_history(country: str | None = None, state: str | None = None, limit: int = Query(200, le=5000)):
    code = _country(country).code if country else None
    return get_store().list_runs(code, state, limit)


# ------------------------------------------------------------------- leads --
def _filter(country, state, council, business_type, q, has_phone, has_website) -> LeadFilter:
    name = _country(country).name if country else None
    return LeadFilter(country=name, state=state or None, council=council or None, business_type=business_type or None,
                      search=q or None, has_phone=has_phone, has_website=has_website)


@router.get("/leads")
def leads(country: str | None = None, state: str | None = None, council: str | None = None,
          business_type: str | None = None, q: str | None = None, has_phone: bool | None = None,
          has_website: bool | None = None, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
    total, items = get_store().query_leads(_filter(country, state, council, business_type, q, has_phone, has_website),
                                           offset, limit)
    return {"total": total, "offset": offset, "limit": limit, "items": items}


@router.get("/leads/summary")
def leads_summary(country: str | None = None, state: str | None = None, council: str | None = None,
                  business_type: str | None = None):
    return get_store().summary(_filter(country, state, council, business_type, None, None, None))


@router.get("/leads/export")
def leads_export(country: str | None = None, state: str | None = None, council: str | None = None,
                 business_type: str | None = None, q: str | None = None, has_phone: bool | None = None,
                 has_website: bool | None = None):
    flt = _filter(country, state, council, business_type, q, has_phone, has_website)
    _, items = get_store().query_leads(flt, 0, None)
    if not items:
        raise HTTPException(status_code=404, detail="No leads match these filters.")
    filters = {"country": flt.country, "state": state, "council": council, "business_type": business_type,
               "name_contains": q, "has_phone": has_phone, "has_website": has_website}
    label = "_".join(str(v) for v in (flt.country, state, council, business_type) if v) or "all"
    path = export.write_export_excel(export.export_path(label), items, filters)
    return FileResponse(path, filename=path.name,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
