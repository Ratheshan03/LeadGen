import json
from fastapi import APIRouter, Query
from services.google_maps import GoogleMapsService
from services.business_manager import BusinessManager
from config.constants import REGION_COORDINATES, AU_REGIONS, BUSINESS_CATEGORIES, ALL_BUSINESS_TYPES, GCCSA_REGIONS, REGIONS_PATH, GEO_KEY_REGION_NAME, GCCSA_PATH, LGA_PATH
from utils.helpers import generate_tiles_for_australia
from db.queries import export_to_excel
from typing import List, Optional
from collections import defaultdict
from db.mongo import leads_collection, db
from itertools import chain
from db.queries import get_leads_by_filter

router = APIRouter()
google_maps = GoogleMapsService()
business_manager = BusinessManager()


@router.get("/crawl")
async def crawl_businesses(
    state: str = Query(..., description="State to crawl (e.g., NSW, VIC, etc.)"),
    region: str = Query(..., description="Specific region or city name"),
    types: List[str] = Query(..., description="List of business types to crawl")
):
    """
    Crawl businesses in a given state/region for specific types using Places API (Manual Mode).
    """
    if region not in REGION_COORDINATES:
        return {"error": f"Region '{region}' not found in config"}

    location = REGION_COORDINATES[region]
    total_saved = 0

    for business_type in types:
        try:
            places = google_maps.search_places_nearby(
                location=location,
                radius=5000,
                place_type=business_type
            )

            saved_count = await business_manager.filter_and_save_results(places, state, region)
            total_saved += saved_count

        except Exception as e:
            print(f"Error during crawling: {str(e)}")
            continue

    return {"message": "Manual crawling complete", "businesses_saved": total_saved}


@router.get("/crawl/all")
async def crawl_all_regions_route(
    dry_run: bool = False
):
    """
    Automatically crawl all configured states/regions/types.
    Use dry_run=True to simulate the crawl without DB writes.
    """
    total_saved = 0
    errors = []
    regions_processed = defaultdict(dict)
    dry_run_plan = []

    all_results = google_maps.crawl_all_regions(dry_run=dry_run)

    if dry_run:
        for item in all_results:
            place = item["place"]
            dry_run_plan.append({
                "name": place.get("displayName", {}).get("text"),
                "location": place.get("formattedAddress"),
                "types": place.get("types", []),
                "state": item["state"],
                "region": item["region"],
                "category": item["category"],
                "type": item["business_type"]
            })

        return {
            "message": "✅ Dry run complete",
            "planned_tasks": dry_run_plan,
            "total_found": len(dry_run_plan)
        }

    # Actual insert
    for item in all_results:
        try:
            saved = await business_manager.save_crawled_batch(
                places=[item["place"]],
                state=item["state"],
                region=item["region"],
                category=item["category"],
                business_type=item["business_type"]
            )
            total_saved += saved
            regions_processed[item["region"]][item["business_type"]] = saved

        except Exception as e:
            errors.append({
                "place_id": item["place"].get("place_id") or item["place"].get("id"),
                "error": str(e)
            })

    return {
        "message": "✅ Full crawl completed",
        "total_saved": total_saved,
        "regions_processed": regions_processed,
        "errors": errors
    }



@router.get("/leads")
async def get_leads_route(
    state: Optional[str] = None,
    type: Optional[str] = None,
    category: Optional[str] = None,
    business_type: Optional[str] = None
):
    """
    Retrieve stored leads with advanced filters (state, category, type, business_type).
    """
    leads = await get_leads_by_filter(
        db=db,  # ✅ Correct full DB object
        state=state,
        type_=type,
        category=category,
        business_type=business_type
    )

    # Convert ObjectIds to string
    for lead in leads:
        lead["_id"] = str(lead["_id"])

    return leads


@router.get("/leads/summary")
async def leads_summary(
    state: Optional[str] = Query(None),
    business_type: Optional[str] = Query(None)
):
    VALID_BUSINESS_TYPES = set(chain.from_iterable(BUSINESS_CATEGORIES.values()))

    # === Main Summary Aggregation from `types` array ===
    pipeline = [
        {"$unwind": "$types"},
        {"$match": {
            "types": {"$in": list(VALID_BUSINESS_TYPES)},
            **({"state": state} if state else {}),
            **({"types": business_type} if business_type else {})
        }},
        {
            "$group": {
                "_id": {"state": "$state", "type": "$types"},
                "count": {"$sum": 1}
            }
        }
    ]
    summary_data = await db.leads.aggregate(pipeline).to_list(length=5000)

    summary = defaultdict(lambda: defaultdict(int))
    for item in summary_data:
        state_ = item["_id"].get("state")
        type_ = item["_id"].get("type")
        count = item["count"]
        if state_ and type_:
            summary[state_][type_] += count

    # === Extra Tags Summary (All types including non-main) ===
    extra_tags_pipeline = [
        {"$unwind": "$types"},
        {"$group": {"_id": "$types", "count": {"$sum": 1}}}
    ]
    tag_data = await db.leads.aggregate(extra_tags_pipeline).to_list(length=5000)
    extra_types = {item["_id"]: item["count"] for item in tag_data if item["_id"]}

    total_businesses = await db.leads.count_documents({})

    return {
        "summary": summary,
        "extra_types": extra_types,
        "total_businesses": total_businesses
    }


@router.get("/crawl/textsearch/custom")
async def crawl_text_search_custom_route(
    query: str = Query(..., description="Business type or 'ALL'"),
    state: str = Query(..., description="Australian state"),
    region: str = Query(..., description="City or region within the state"),
    geojson_type: str = Query("regions", description="GeoJSON source type: 'regions', 'gccsa', or 'lga'"),
    dry_run: bool = False
):
    # Generate tiles
    tiles = generate_tiles_for_australia(
        tile_km=10,
        geojson_source=geojson_type,
        target_region=region,
        state_name=state
    )

    if not tiles:
        return {
            "error": f"No tiles generated for region '{region}' using geojson '{geojson_type}'."
        }

    if dry_run:
        return {
            "message": f"🟢 Dry run: Tiles generated for region '{region}', state '{state}'",
            "tiles_generated": len(tiles),
            "tiles": tiles,
            "dry_run": True,
            "api_requests_total": 0
        }

    # Handle ALL business types
    if query.upper() == "ALL":
        results = []
        failures = []
        details = []
        combined_saved_data = []
        api_requests_grand_total = 0

        for btype in ALL_BUSINESS_TYPES:
            try:
                print(f"🚀 Crawling for business type: {btype}")
                result = await business_manager.crawl_custom_text_search(
                    btype, state, region, tiles, dry_run
                )
                results.append(result)
                failures.extend(result.get("failures", []))
                details.extend(result.get("details", []))
                combined_saved_data.extend(result.get("saved_data", []))
                api_requests_grand_total += result.get("api_requests_total", 0)
            except Exception as e:
                print(f"❌ Error while crawling '{btype}': {str(e)}")
                failures.append({"business_type": btype, "error": str(e)})

        excel_path = export_to_excel(
            data=combined_saved_data,
            region=region,
            state=state,
            business_type="ALL"
        )

        return {
            "message": f"✅ Crawled all business types in region: {region}, state: {state}",
            "business_types": len(ALL_BUSINESS_TYPES),
            "dry_run": dry_run,
            "failures": len(failures),
            "details": len(details),
            "total_saved": len(combined_saved_data),
            "tiles_generated": len(tiles),
            "tiles": tiles,
            "excel_file": excel_path,
            "api_requests_total": api_requests_grand_total  # ✅ surfaced
        }

    # Single business type
    result = await business_manager.crawl_custom_text_search(query, state, region, tiles, dry_run)

    excel_path = export_to_excel(
        data=result.get("saved_data", []),
        region=region,
        state=state,
        business_type=query
    )

    return {
        "message": result.get("message"),
        "dry_run": dry_run,
        "failures": result.get("failures", []),
        "details": result.get("details", []),
        "total_saved": result.get("total_saved", 0),
        "tiles_scanned": result.get("tiles_scanned", 0),
        "tiles_generated": len(tiles),
        "tiles": tiles,
        "excel_file": excel_path,
        "api_requests_total": result.get("api_requests_total", 0)
    }




@router.get("/crawl/textsearch/full")
async def crawl_text_search_full_route(
    dry_run: bool = False,
    limit_tiles: int = 0,
    geojson_type: str = Query("gccsa", description="GeoJSON source: 'gccsa', 'regions', or 'lga'")
):
    """
    Crawl all business types across AU using text search.
    Supports tile generation from gccsa, regions, or lga GeoJSON files.
    """

    geojson_type = geojson_type.lower()
    if geojson_type not in {"gccsa", "regions", "lga"}:
        return {"error": "Invalid geojson_type. Must be one of 'gccsa', 'regions', or 'lga'."}

    all_types = ALL_BUSINESS_TYPES
    all_tiles = []

    # Map geojson type to path
    geojson_path_map = {
        "gccsa": GCCSA_PATH,
        "regions": REGIONS_PATH,
        "lga": LGA_PATH
    }
    geojson_path = geojson_path_map[geojson_type]

    # Load geojson file
    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)
    except Exception as e:
        return {"error": f"Failed to load GeoJSON file: {str(e)}"}

    # State names list for filtering in all geojsons (keys of GCCSA_REGIONS)
    states_list = list(GCCSA_REGIONS.keys())

    # Generate tiles based on geojson type
    for state_name in states_list:
        # Filter features by state (key varies per geojson)
        if geojson_type == "gccsa":
            # gccsa geojson: filter by state and gccsa region
            gccsa_regions = GCCSA_REGIONS.get(state_name, [])
            for gccsa_region in gccsa_regions:
                features = [
                    feat for feat in geojson_data["features"]
                    if feat["properties"].get("STE_NAME21") == state_name and
                       feat["properties"].get("GCC_NAME21") == gccsa_region
                ]
                for feature in features:
                    region_name = feature["properties"].get("GCC_NAME21")
                    if region_name:
                        try:
                            tiles = generate_tiles_for_australia(
                                tile_km=10,
                                geojson_source=geojson_type,
                                target_region=region_name,
                                state_name=state_name
                            )
                            all_tiles.extend(tiles)
                        except Exception as e:
                            print(f"[TileGen ERROR] {region_name}: {e}")

        elif geojson_type == "regions":
            # regions geojson: filter by state only, generate tiles per SA2_NAME21 region
            features = [
                feat for feat in geojson_data["features"]
                if feat["properties"].get("STE_NAME21") == state_name
            ]
            for feature in features:
                region_name = feature["properties"].get("SA2_NAME21")
                if region_name:
                    try:
                        tiles = generate_tiles_for_australia(
                            tile_km=10,
                            geojson_source=geojson_type,
                            target_region=region_name,
                            state_name=state_name
                        )
                        all_tiles.extend(tiles)
                    except Exception as e:
                        print(f"[TileGen ERROR] {region_name}: {e}")

        elif geojson_type == "lga":
            # lga geojson: filter by state, generate tiles per LGA_NAME24
            features = [
                feat for feat in geojson_data["features"]
                if feat["properties"].get("STE_NAME21") == state_name
            ]
            for feature in features:
                region_name = feature["properties"].get("LGA_NAME24")
                if region_name:
                    try:
                        tiles = generate_tiles_for_australia(
                            tile_km=10,
                            geojson_source=geojson_type,
                            target_region=region_name,
                            state_name=state_name
                        )
                        all_tiles.extend(tiles)
                    except Exception as e:
                        print(f"[TileGen ERROR] {region_name}: {e}")

    # Apply limit if requested
    if limit_tiles > 0:
        all_tiles = all_tiles[:limit_tiles]

    if not all_tiles:
        return {"error": "No tiles generated."}

    total_saved = 0
    total_tiles = 0
    all_failures = []
    all_details = []

    if dry_run:
        simulated_calls = []
        for btype in all_types:
            result = await business_manager.crawl_using_text_search(btype, all_tiles, dry_run=True)
            simulated_calls.extend(result.get("details", []))
            all_failures.extend(result.get("failures", []))
            all_details.extend(result.get("details", []))

        return {
            "message": f"✅ DRY RUN: Simulation complete using {geojson_type}",
            "total_business_types": len(all_types),
            "total_tiles": len(all_tiles),
            "total_simulated_requests": len(simulated_calls),
            "planned_requests_sample": simulated_calls[:10],
            "failures": all_failures,
            "details": all_details,
            "note": "No actual API or DB requests were made."
        }

    # Real crawl
    for btype in all_types:
        print(f"Real crawl: {btype}")
        result = await business_manager.crawl_using_text_search(btype, all_tiles, dry_run=False)
        total_saved += result.get("total_saved", 0)
        total_tiles += result.get("tiles_scanned", 0)
        all_failures.extend(result.get("failures", []))
        all_details.extend(result.get("details", []))

    return {
        "message": f"✅ Full AU-wide text search crawl completed using {geojson_type}.",
        "total_saved": total_saved,
        "tiles_scanned": total_tiles,
        "failures": all_failures,
        "details": all_details,
        "total_business_types": len(all_types)
    }




@router.get("/leads/crawl/textsearch/coverage")
async def check_coverage(state: Optional[str] = None, region: Optional[str] = None):
    query = {}
    if state:
        query["state"] = state
    if region:
        query["region"] = region

    count = await db.leads.count_documents(query)

    return {
        "region": region or "All Regions",
        "state": state or "All States",
        "total_leads": count
    }
