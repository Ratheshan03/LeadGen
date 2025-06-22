from fastapi import APIRouter, Query
import asyncio
from services.google_maps import GoogleMapsService
from services.business_manager import BusinessManager
from config.constants import REGION_COORDINATES, AU_REGIONS, BUSINESS_CATEGORIES, ALL_BUSINESS_TYPES
from utils.helpers import generate_text_search_tiles
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
    query: str = Query(..., description="Free-text query (e.g., 'plumber', 'accountants')"),
    state: str = Query(..., description="Australian state"),
    region: str = Query(..., description="City or region within the state")
):
    """
    Custom text search for user-defined region + query.
    """
    return await business_manager.crawl_custom_text_search(query, state, region)



@router.get("/crawl/textsearch/full")
async def crawl_text_search_full_route(dry_run: bool = False, limit_tiles: int = 0):
    """
    Automatically crawl all business types across AU using Text Search API.
    Dynamically generates tiles per region.
    If dry_run=True, simulates crawl without API or DB requests.
    """
    all_types = ALL_BUSINESS_TYPES
    # print("Running automated text search for types:", all_types)
    all_tiles = generate_text_search_tiles()
    # print(f"Generated {len(all_tiles)} tiles.")

    if limit_tiles > 0:
        all_tiles = all_tiles[:limit_tiles]
        # print(f"Limiting to first {limit_tiles} tiles for this run.")

    if not all_tiles:
        return {"error": "No dynamic tiles could be generated."}

    total_saved = 0
    total_tiles = 0
    all_failures = []
    all_details = []

    if dry_run:
        simulated_calls = []
        for btype in all_types:
            result = await business_manager.crawl_using_text_search(btype, all_tiles, dry_run=True)
            simulated_calls.extend(result.get("details", []))

        return {
            "message": "✅ DRY RUN: Simulation completed",
            "total_business_types": len(all_types),
            "total_tiles": len(all_tiles),
            "total_simulated_requests": len(simulated_calls),
            "planned_requests": simulated_calls[:10],  # preview first 10
            "note": "No actual API or DB operations were performed."
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
        "message": "Full AU-wide text search crawl completed.",
        "total_saved": total_saved,
        "tiles_scanned": total_tiles,
        "failures": all_failures,
        "details": all_details
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
