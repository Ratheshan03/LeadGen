from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGO_DB_URI", "mongodb://localhost:27017")
MONGODB_NAME = os.getenv("MONGO_DB_NAME", "leads_db")

client = AsyncIOMotorClient(MONGODB_URI)
db = client[MONGODB_NAME]

# Leads collection
leads_collection = db["leads"]

# Ensure unique constraint on place_id (Google Places unique identifier)
async def init_db_indexes():
    await leads_collection.create_index(
        [("place_id", ASCENDING)],
        unique=True,
        name="unique_place_id_index"
    )
