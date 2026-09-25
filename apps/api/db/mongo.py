from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
import os
import ssl
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGO_DB_URI", "mongodb://localhost:27017")
MONGODB_NAME = os.getenv("MONGO_DB_NAME", "leads_db")

# tlsCAFile=certifi is the standard fix for WinError 10054 SSL resets on Windows
import certifi
client = AsyncIOMotorClient(
    MONGODB_URI,
    tls=True,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=30000,
)
db = client[MONGODB_NAME]

leads_collection = db["leads"]

async def init_db_indexes():
    try:
        await leads_collection.create_index(
            [("place_id", ASCENDING)],
            unique=True,
            name="unique_place_id_index"
        )
        print("MongoDB Index ensured.")
    except Exception as e:
        print("Failed to create MongoDB index:", str(e))
