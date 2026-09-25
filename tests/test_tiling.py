"""
Tiling regression tests.

tests/fixtures/golden_tiles_au/*.json hold the exact tiles the ORIGINAL
LeadGen code produced for every Australian area (captured before the
refactor). The current tiler, run on the compact boundary files, must give the
same number of tiles per area with edges within a couple of metres.
"""
import json
import math
from pathlib import Path

import pytest

from backend.geo.datasets import GeoError, get_country, load_areas
from backend.geo.tiling import split_tile_longer_side, standard_tiles, tiles_for_area

GOLDEN = Path(__file__).parent / "fixtures" / "golden_tiles_au"
AU = get_country("AU")
MAX_DRIFT_M = 2.0


def _edges(tiles):
    return sorted((t["low"]["latitude"], t["low"]["longitude"], t["high"]["latitude"], t["high"]["longitude"])
                  for t in tiles)


def _drift_m(a, b):
    lat = math.radians(a[0])
    return max(abs(a[0] - b[0]) * 111_320, abs(a[1] - b[1]) * 111_320 * math.cos(lat),
               abs(a[2] - b[2]) * 111_320, abs(a[3] - b[3]) * 111_320 * math.cos(lat))


@pytest.mark.parametrize("level", ["lga", "sa2", "gccsa"])
def test_tiles_match_original_crawler(level):
    golden = json.loads((GOLDEN / f"{level}.json").read_text(encoding="utf-8"))
    areas = load_areas(AU, level)
    assert len(areas) == len(golden)
    for area in areas.areas:
        expected = sorted(tuple(t[:4]) for t in golden[area.key])
        got = _edges(standard_tiles(area, AU))
        assert len(got) == len(expected), f"{area.name}: tile count changed"
        worst = max(_drift_m(e, g) for e, g in zip(expected, got))
        assert worst <= MAX_DRIFT_M, f"{area.name}: tile edge moved {worst:.1f} m"


def test_non_geographic_placeholders_are_excluded():
    names = {a.key for a in load_areas(AU, "lga").areas}
    assert not any("no usual address" in n or "migratory" in n for n in names)
    assert len(names) == 547


def test_find_is_case_insensitive_and_suggests():
    lgas = load_areas(AU, "lga")
    assert lgas.find("walkerville").name == "Walkerville"
    with pytest.raises(GeoError, match="Did you mean"):
        lgas.find("Walkervile")


def test_locate_point_returns_containing_council():
    lgas = load_areas(AU, "lga")
    assert lgas.locate(151.2153, -33.8568).name == "Sydney"          # Opera House
    assert lgas.locate(138.6186, -34.8930).name == "Walkerville"     # Walkerville town
    assert lgas.locate(160.0, -30.0) is None                         # Tasman Sea


def test_states_come_from_boundary_data():
    lgas = load_areas(AU, "lga")
    assert "New South Wales" in lgas.states()
    assert all(a.state == "South Australia" for a in lgas.in_state("south australia"))


def test_dense_mode_splits_a_city_into_neighbourhood_tiles():
    brisbane = load_areas(AU, "lga").find("Brisbane")
    standard = tiles_for_area(brisbane, AU, dense=False)
    dense = tiles_for_area(brisbane, AU, dense=True)
    assert len(standard) == 1
    assert len(dense) > 50
    assert all(t["area"] == "Brisbane" and t.get("sub_area") for t in dense)


def test_split_tile_longer_side():
    tile = {"tile_name": "t", "area": "X",
            "low": {"latitude": -34.0, "longitude": 150.0}, "high": {"latitude": -33.0, "longitude": 150.5}}
    halves = split_tile_longer_side(tile)
    assert [h["tile_name"] for h in halves] == ["t_h0", "t_h1"]
    assert halves[0]["high"]["latitude"] == -33.5 and halves[1]["low"]["latitude"] == -33.5
    assert all(h["area"] == "X" for h in halves)
    degenerate = {"low": {"latitude": 1, "longitude": 1}, "high": {"latitude": 1, "longitude": 2}}
    assert split_tile_longer_side(degenerate) == []
