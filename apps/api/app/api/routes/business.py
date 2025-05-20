from fastapi import APIRouter, Query, HTTPException
from app.services.google_maps import search_places
from app.services.lead_service import insert_leads, get_all_leads
from bson import ObjectId
from app.models.lead import LeadDB

router = APIRouter()

@router.post("/search")
def search_and_store_leads(query: str = Query(..., min_length=3)):
    try:
        places = search_places(query)
        saved = insert_leads(places)
        return {
            "message": f"{len(saved)} new leads saved",
            "leads": saved
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/leads")
def get_leads():
    return {"leads": get_all_leads()}


@router.patch("/leads/{lead_id}")
async def update_lead_status(lead_id: str, update_data: dict):
    from app.db.mongo import collection  # Import here or globally

    if not ObjectId.is_valid(lead_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")

    result = await collection.update_one(
        {"_id": ObjectId(lead_id)},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found or no changes made")

    updated = await collection.find_one({"_id": ObjectId(lead_id)})
    return updated

