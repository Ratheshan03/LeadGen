from fastapi import APIRouter, Query
import asyncio
from services.google_maps import GoogleMapsService
from services.business_manager import BusinessManager
from config.constants import REGION_COORDINATES
from typing import List
from collections import defaultdict
from db.mongo import leads_collection

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
    Crawl businesses in a given state/region for specific types using Places API (New).
    """
    if region not in REGION_COORDINATES:
        return {"error": f"Region '{region}' not found in config"}

    location = REGION_COORDINATES[region]
    total_saved = 0

    for business_type in types:
        try:
            response = google_maps.search_places_nearby(
                location=location,
                radius=5000,
                place_type=business_type
            )
            places = response.get("places", [])
            # print(f"Found {len(places)} places for type '{business_type}' in {region}")
            
            saved_count = await business_manager.filter_and_save_results(places, state, region)
            total_saved += saved_count

        except Exception as e:
            print(f"Error during crawling: {str(e)}")
            continue

    return {"message": "Crawling complete", "businesses_saved": total_saved}


@router.get("/leads")
async def get_leads(state: str = None, type: str = None):
    """
    Retrieve stored leads with optional filters (state, type).
    """
    query = {}
    if state:
        query["state"] = state
    if type:
        query["types"] = {"$in": [type]}
    leads_cursor = await leads_collection.find(query).to_list(length=1000)
    leads = []
    for lead in leads_cursor:
        lead["_id"] = str(lead["_id"])  # Convert ObjectId to string
        leads.append(lead)

    return leads

@router.get("/leads/summary")
async def leads_summary():
    pipeline = [
        {"$unwind": "$tags"},
        {
            "$group": {
                "_id": {"state": "$state", "type": "$tags"},
                "count": {"$sum": 1}
            }
        }
    ]
    summary_data = await leads_collection.aggregate(pipeline).to_list(length=1000)

    # Reformat to nested structure for frontend
    summary = defaultdict(dict)
    for item in summary_data:
        state = item["_id"].get("state")
        btype = item["_id"].get("type")
        count = item["count"]

        if not state or not btype:
            continue

        summary[state][btype] = count

    return summary
