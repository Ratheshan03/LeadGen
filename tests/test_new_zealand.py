"""New Zealand data and crawl tests (fake Google API)."""
import openpyxl
import pytest

from backend.config import settings
from backend.crawler.engine import Labeler, crawl_area
from backend.crawler.places import PlacesClient
from backend.crawler.quota import QuotaManager
from backend.geo.datasets import get_country, load_areas, load_cities, load_lookup
from backend.geo.tiling import tiles_for_area
from backend.storage.sqlite_store import SQLiteLeadStore
from tests.fakes import FakeGoogle, make_place

NZ = get_country("NZ")
pytestmark = pytest.mark.skipif(not NZ.has_data("ta"), reason="New Zealand boundary data not built yet")


def test_areas_load_with_regions():
    regions, tas, sa2s = load_areas(NZ, "region"), load_areas(NZ, "ta"), load_areas(NZ, "sa2")
    assert 16 <= len(regions) <= 17
    assert 60 <= len(tas) <= 70
    assert len(sa2s) > 1500
    region_names = {r.name for r in regions.areas}
    assert {"Auckland", "Canterbury", "Wellington", "Otago"} <= region_names
    assert all(t.state in region_names for t in tas.areas)
    assert all(s.state in region_names for s in sa2s.areas)
    assert not any("oceanic" in s.key or s.key.startswith("inlet") for s in sa2s.areas)
    lookup = load_lookup(NZ, "ta")
    assert "Christchurch City" in lookup["Canterbury"]


def test_names_match_with_or_without_macrons():
    tas = load_areas(NZ, "ta")
    whangarei = tas.find("whangarei district")
    assert whangarei.name.startswith("Whang") and whangarei.state == "Northland"
    assert tas.search("tauranga")[0].name == "Tauranga City"


def test_every_city_is_inside_its_region():
    regions = load_areas(NZ, "region")
    for city in load_cities(NZ):
        region = regions.locate(city["lng"], city["lat"], max_distance_deg=0.05)
        assert region is not None and region.name == city["state"], city


def test_every_council_tiles_cleanly():
    for ta in load_areas(NZ, "ta").areas:
        tiles = tiles_for_area(ta, NZ)
        assert tiles, ta.name
        for t in tiles:
            lat_lo, lat_hi = t["low"]["latitude"], t["high"]["latitude"]
            lon_lo, lon_hi = t["low"]["longitude"], t["high"]["longitude"]
            assert -53 < lat_lo < lat_hi < -28, ta.name
            assert lon_lo < lon_hi and lon_hi - lon_lo < 10, ta.name   # never wraps the 180th meridian


def test_labels_and_dense_mode():
    labeler = Labeler(NZ)
    lead = {"latitude": -43.5321, "longitude": 172.6362}   # Christchurch Cathedral Square
    labeler.label(lead, fallback_state="?")
    assert (lead["council"], lead["state"], lead["country"]) == ("Christchurch City", "Canterbury", "New Zealand")
    auckland = load_areas(NZ, "ta").find("Auckland")
    assert len(tiles_for_area(auckland, NZ, dense=True)) > 100


def test_crawl_christchurch(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "OUTPUT_DIR", tmp_path / "output")
    store = SQLiteLeadStore(tmp_path / "leads.db")
    area = load_areas(NZ, "ta").find("Christchurch City")
    fake = FakeGoogle(places={"cafe": [make_place("c1", -43.5321, 172.6362, "Cathedral Square Cafe")]})
    client = PlacesClient(keys=["k"], quota=QuotaManager(tmp_path / "q.json", 100), session=fake, page_delay=0)
    result = crawl_area(client=client, store=store, country=NZ, area=area, business_types=["cafe"], types_label="cafe")
    assert result.status == "completed" and result.leads_found == 1
    assert "New Zealand" in result.excel_file and "Canterbury" in result.excel_file
    rows = list(openpyxl.load_workbook(result.excel_file)["Leads"].iter_rows(values_only=True))
    header = rows[0]
    assert "Region" in header and rows[1][header.index("Region")] == "Canterbury"
