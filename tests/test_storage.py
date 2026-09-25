"""The same behaviour is required from the SQLite (default) and MongoDB stores."""
from backend.storage.base import INSERTED, UNCHANGED, UPDATED, LeadFilter
from tests.conftest import make_lead


def test_insert_then_add_type_then_unchanged(store):
    assert store.upsert_lead(make_lead(), "cafe") == INSERTED
    assert store.upsert_lead(make_lead(), "restaurant") == UPDATED
    assert store.upsert_lead(make_lead(), "cafe") == UNCHANGED
    total, leads = store.query_leads(LeadFilter())
    assert total == 1 and store.count() == 1
    lead = leads[0]
    assert sorted(lead["business_types"]) == ["cafe", "restaurant"]
    assert lead["types"] == ["cafe", "food"] and lead["opening_hours"] == ["Monday: 7:00 AM - 3:00 PM"]
    assert lead["latitude"] == -34.893 and lead["first_seen"] and lead["last_seen"]


def test_refresh_keeps_old_values_when_google_returns_nothing(store):
    store.upsert_lead(make_lead(), "cafe")
    store.upsert_lead(make_lead(phone=None, website=None, rating=4.8), "cafe")
    lead = store.query_leads(LeadFilter())[1][0]
    assert lead["phone"] == "+61 8 1234 5678"          # kept
    assert lead["website"] == "https://joes.example"   # kept
    assert lead["rating"] == 4.8                       # refreshed


def test_filters_and_pagination(store):
    store.upsert_lead(make_lead("a", name="Alpha Bakery"), "bakery")
    store.upsert_lead(make_lead("b", name="Beta Plumbing", phone=None, phone_local=None, council="Prospect"), "plumber")
    store.upsert_lead(make_lead("c", name="Gamma 100% Cafe", state="Victoria", council="Melbourne", website=None), "cafe")
    assert store.query_leads(LeadFilter(state="south australia"))[0] == 2
    assert store.query_leads(LeadFilter(council="Prospect"))[0] == 1
    assert store.query_leads(LeadFilter(business_type="cafe"))[0] == 1
    assert store.query_leads(LeadFilter(search="100%"))[0] == 1          # literal %, not a wildcard
    assert store.query_leads(LeadFilter(has_phone=True))[0] == 2
    assert store.query_leads(LeadFilter(has_website=False))[0] == 1
    assert store.query_leads(LeadFilter(place_ids=["a", "c"]))[0] == 2
    total, page = store.query_leads(LeadFilter(), offset=1, limit=1)
    assert total == 3 and [p["name"] for p in page] == ["Beta Plumbing"]


def test_summary(store):
    store.upsert_lead(make_lead("a"), "cafe")
    store.upsert_lead(make_lead("a"), "bakery")
    store.upsert_lead(make_lead("b", state="Victoria", website=None), "cafe")
    s = store.summary(LeadFilter())
    assert s["total"] == 2 and s["with_website"] == 1 and s["with_phone"] == 2
    assert s["by_state"] == {"South Australia": 1, "Victoria": 1}
    assert s["by_business_type"] == {"cafe": 2, "bakery": 1}


def test_crawl_runs_and_resume(store):
    rid = store.start_run({"mode": "area", "country": "AU", "level": "lga", "state": "South Australia",
                           "area": "Walkerville", "business_types": "ALL", "dense": False})
    assert store.completed_areas("AU", "lga", "ALL", False) == set()
    store.finish_run(rid, {"status": "completed", "requests": 12, "leads_found": 40})
    assert store.completed_areas("AU", "lga", "ALL", False) == {("South Australia", "Walkerville")}
    assert store.completed_areas("AU", "lga", "ALL", True) == set()   # dense crawl is a different job
    runs = store.list_runs(country="AU")
    assert runs[0]["status"] == "completed" and runs[0]["requests"] == 12


def test_mongo_reads_leads_from_the_old_app():
    import mongomock
    from backend.storage.mongo_store import MongoLeadStore
    client = mongomock.MongoClient()
    client["old"]["leads"].insert_one({
        "place_id": "legacy1", "name": "Old Lead", "location": {"latitude": -27.4, "longitude": 153.0},
        "state": "Queensland", "region": "brisbane", "business_type": "cafe", "total_reviews": 9,
    })
    store = MongoLeadStore("", "old", client=client)
    lead = store.query_leads(LeadFilter(council="Brisbane"))[1][0]
    assert lead["latitude"] == -27.4 and lead["council"] == "brisbane"
    assert lead["business_types"] == ["cafe"] and lead["review_count"] == 9
