import mongomock
import pytest

from backend.storage.mongo_store import MongoLeadStore
from backend.storage.sqlite_store import SQLiteLeadStore


def make_lead(place_id="p1", **overrides):
    lead = {
        "place_id": place_id, "name": "Joe's Cafe", "address": "1 Main St, Walkerville SA 5081",
        "phone": "+61 8 1234 5678", "phone_local": "(08) 1234 5678", "website": "https://joes.example",
        "google_maps_url": "https://maps.google.com/?cid=1", "rating": 4.5, "review_count": 120,
        "business_status": "OPERATIONAL", "primary_type": "cafe", "types": ["cafe", "food"],
        "opening_hours": ["Monday: 7:00 AM - 3:00 PM"], "latitude": -34.893, "longitude": 138.618,
        "country": "Australia", "state": "South Australia", "council": "Walkerville", "sa2": "Walkerville",
        "source": "text_search",
    }
    lead.update(overrides)
    return lead


@pytest.fixture(params=["sqlite", "mongodb"])
def store(request, tmp_path):
    if request.param == "sqlite":
        s = SQLiteLeadStore(tmp_path / "leads.db")
    else:
        s = MongoLeadStore("", "leadgen_test", client=mongomock.MongoClient())
    yield s
    s.close()
