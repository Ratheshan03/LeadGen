from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, Dict, Any, List
from bson.objectid import ObjectId

# Check if a business already exists using place_id
async def is_duplicate(db: AsyncIOMotorDatabase, place_id: str) -> bool:
    existing = await db.leads.find_one({"place_id": place_id})
    return existing is not None

# Insert a new business lead
async def insert_lead(db: AsyncIOMotorDatabase, lead_data: Dict[str, Any]) -> str:
    result = await db.leads.insert_one(lead_data)
    return str(result.inserted_id)

# Batch insert with deduplication
async def insert_leads_batch(db: AsyncIOMotorDatabase, leads: List[Dict[str, Any]]) -> int:
    if not leads:
        return 0

    # Deduplicate by checking existing place_ids
    place_ids = [lead["place_id"] for lead in leads]
    existing = await db.leads.find({"place_id": {"$in": place_ids}}).to_list(length=len(place_ids))
    existing_ids = {doc["place_id"] for doc in existing}

    # Filter new ones
    new_leads = [lead for lead in leads if lead["place_id"] not in existing_ids]

    if not new_leads:
        return 0

    result = await db.leads.insert_many(new_leads)
    return len(result.inserted_ids)

# Get leads filtered by state, type, category, or business_type
async def get_leads_by_filter(
    db: AsyncIOMotorDatabase,
    state: Optional[str] = None,
    type_: Optional[str] = None,
    category: Optional[str] = None,
    business_type: Optional[str] = None
):
    query = {}

    if state:
        query["state"] = state

    if type_:
        # Ensure we only match this exact type inside the "types" array
        query["types"] = {"$elemMatch": {"$regex": f"^{type_}$", "$options": "i"}}

    if category:
        query["category"] = {"$regex": f"^{category}$", "$options": "i"}

    if business_type:
        query["business_type"] = {"$regex": f"^{business_type}$", "$options": "i"}

    leads = await db.leads.find(query).to_list(length=1000)
    return leads


# Get a single lead by place_id
async def get_lead_by_place_id(db: AsyncIOMotorDatabase, place_id: str):
    return await db.leads.find_one({"place_id": place_id})

# Delete a lead by ObjectId (if needed for dashboard cleanup)
async def delete_lead_by_id(db: AsyncIOMotorDatabase, lead_id: str):
    return await db.leads.delete_one({"_id": ObjectId(lead_id)})
