from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, Dict, Any
from bson.objectid import ObjectId

# Check if a business already exists using place_id
async def is_duplicate(db: AsyncIOMotorDatabase, place_id: str) -> bool:
    existing = await db.leads.find_one({"place_id": place_id})
    return existing is not None

# Insert a new business lead
async def insert_lead(db: AsyncIOMotorDatabase, lead_data: Dict[str, Any]) -> str:
    result = await db.leads.insert_one(lead_data)
    return str(result.inserted_id)

# Get leads filtered by state and/or type
async def get_leads_by_filter(db: AsyncIOMotorDatabase, state: Optional[str] = None, type_: Optional[str] = None):
    query = {}
    if state:
        query["state"] = state
    if type_:
        query["types"] = {"$in": [type_]}
    leads = await db.leads.find(query).to_list(length=1000)
    return leads

# Get a single lead by place_id
async def get_lead_by_place_id(db: AsyncIOMotorDatabase, place_id: str):
    return await db.leads.find_one({"place_id": place_id})

# Delete a lead by ObjectId (if needed for dashboard cleanup)
async def delete_lead_by_id(db: AsyncIOMotorDatabase, lead_id: str):
    return await db.leads.delete_one({"_id": ObjectId(lead_id)})
