import pytest

from backend.config.business_types import BusinessTypesError, get_business_types, normalise_type

ORIGINAL_TYPE_COUNT = 93  # the list LeadGen shipped with


def test_default_config_matches_original_list():
    bt = get_business_types()
    assert len(bt.all_types) == ORIGINAL_TYPE_COUNT
    assert bt.all_types == sorted(bt.all_types)
    assert {"restaurant", "plumber", "accounting", "airport"} <= set(bt.all_types)
    assert bt.type_to_category["accounting"] == "Finance"


def test_resolve_all_category_and_types():
    bt = get_business_types()
    assert bt.resolve("ALL") == bt.all_types
    assert bt.resolve("Food and Drink") == bt.categories["Food and Drink"]
    assert bt.resolve(["Car Repair", "plumber", "plumber"]) == ["car_repair", "plumber"]


def test_normalise_type():
    assert normalise_type("  Car-Repair ") == "car_repair"


def test_bad_file_gives_clear_error(tmp_path):
    bad = tmp_path / "business_types.yaml"
    bad.write_text("Food:\n  restaurant\n", encoding="utf-8")
    with pytest.raises(BusinessTypesError, match="must be a list"):
        get_business_types(bad)
    bad.write_text("Food: [unclosed", encoding="utf-8")
    with pytest.raises(BusinessTypesError, match="not valid YAML"):
        get_business_types(bad)
