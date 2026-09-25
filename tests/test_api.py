"""API + background job tests (fake Google API, temporary storage)."""
import time

import pytest
from fastapi.testclient import TestClient

from backend import jobs as jobs_module
from backend.config import settings
from backend.crawler.places import PlacesClient
from backend.storage import reset_store
from backend.storage.sqlite_store import SQLiteLeadStore
from tests.fakes import FakeGoogle, make_place

WALKERVILLE_CAFE = make_place("w1", -34.8930, 138.6186, "Walkerville Cafe")


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(settings, "QUOTA_FILE", tmp_path / "quota.json")
    fake = FakeGoogle(places={"cafe": [WALKERVILLE_CAFE]},
                      nearby={"cafe": [make_place("n1", -34.9285, 138.6007, "Adelaide Cafe")]})
    monkeypatch.setattr(jobs_module, "PlacesClient",
                        lambda quota: PlacesClient(keys=["k"], quota=quota, session=fake, page_delay=0))
    store = SQLiteLeadStore(tmp_path / "leads.db")
    reset_store(store)
    from backend.main import app
    with TestClient(app) as client:
        yield client
    reset_store(None)


def wait(client, job_id, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        job = client.get(f"/api/crawl/jobs/{job_id}").json()
        if job["status"] not in ("queued", "running"):
            return job
        time.sleep(0.1)
    raise AssertionError("job did not finish")


def test_health_status_and_meta(api):
    assert api.get("/api/health").json() == {"status": "ok"}
    status = api.get("/api/status").json()
    assert status["storage"].startswith("SQLite") and status["quota"]["used"] == 0
    meta = api.get("/api/meta").json()
    au = next(c for c in meta["countries"] if c["code"] == "AU")
    assert au["has_data"] and au["state_label"] == "State"
    assert len(meta["business_types"]["all"]) == 93


def test_areas_endpoints(api):
    lookup = api.get("/api/areas/lookup", params={"country": "AU", "level": "lga"}).json()
    assert "Walkerville" in lookup["South Australia"]
    sa = api.get("/api/areas", params={"country": "Australia", "state": "South Australia"}).json()
    assert all(a["state"] == "South Australia" for a in sa) and len(sa) > 60
    found = api.get("/api/areas/search", params={"q": "walker"}).json()
    assert found[0]["name"] == "Walkerville"
    assert api.get("/api/areas", params={"country": "Mars"}).status_code == 400


def test_estimate(api):
    est = api.post("/api/crawl/estimate", json={"mode": "area", "country": "AU", "state": "South Australia",
                                                "area": "Walkerville", "business_types": "ALL"}).json()
    assert est["tiles"] == 1 and est["business_types"] == 93 and est["min_requests"] == 93
    assert est["min_cost_usd"] == round(93 / 1000 * settings.COST_PER_1000_REQUESTS_USD, 2)
    bad = api.post("/api/crawl/estimate", json={"mode": "area", "area": "Walkervile"})
    assert bad.status_code == 400 and "Did you mean" in bad.json()["detail"]


def test_area_job_end_to_end_then_leads_and_export(api):
    job = api.post("/api/crawl/jobs", json={"mode": "area", "state": "South Australia", "area": "Walkerville",
                                            "business_types": ["cafe"]}).json()
    job = wait(api, job["id"])
    assert job["status"] == "completed", job["logs"]
    assert job["summary"]["leads_found"] == 1 and job["summary"]["excel_files"]
    assert any("cafe" in line and "found" in line for line in job["logs"])

    page = api.get("/api/leads", params={"country": "AU", "council": "Walkerville"}).json()
    assert page["total"] == 1 and page["items"][0]["name"] == "Walkerville Cafe"
    assert api.get("/api/leads/summary", params={"country": "AU"}).json()["total"] == 1
    xlsx = api.get("/api/leads/export", params={"country": "AU"})
    assert xlsx.status_code == 200 and xlsx.content[:2] == b"PK"
    assert api.get("/api/crawl/history").json()[0]["area"] == "Walkerville"


def test_state_crawl_skips_completed_areas(api):
    body = {"mode": "state", "state": "South Australia", "areas": ["Walkerville", "Prospect"], "business_types": ["cafe"]}
    first = wait(api, api.post("/api/crawl/jobs", json=body).json()["id"])
    assert first["status"] == "completed" and first["summary"]["areas_done"] == 2
    est = api.post("/api/crawl/estimate", json=body).json()
    assert est["areas"] == 0 and len(est["skipped"]) == 2
    assert api.post("/api/crawl/jobs", json=body).status_code == 400          # nothing left to do
    again = api.post("/api/crawl/jobs", json={**body, "skip_completed": False})
    assert again.status_code == 200


def test_nearby_job(api):
    job = wait(api, api.post("/api/crawl/jobs", json={"mode": "nearby", "state": "South Australia",
                                                      "cities": ["Adelaide"], "business_types": ["cafe"]}).json()["id"])
    assert job["status"] == "completed" and job["summary"]["leads_found"] == 1
    assert "(Nearby)" in job["summary"]["excel_files"][0]


def test_cancel_queued_job(api):
    first = api.post("/api/crawl/jobs", json={"mode": "area", "area": "Walkerville", "business_types": "ALL"}).json()
    second = api.post("/api/crawl/jobs", json={"mode": "area", "area": "Prospect", "business_types": ["cafe"]}).json()
    cancelled = api.post(f"/api/crawl/jobs/{second['id']}/cancel").json()
    assert cancelled["status"] in ("cancelled", "queued")
    assert wait(api, second["id"])["status"] == "cancelled"
    wait(api, first["id"])
