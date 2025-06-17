import os
import sys
import asyncio
import requests

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from dotenv import load_dotenv
from db.mongo import db, leads_collection
from utils.api_key_manager import APIKeyManager

load_dotenv(dotenv_path='../.env')

# Test DB connection
async def test_db():
    print("Testing MongoDB connection...")
    test_doc = {"test": "connection"}
    result = await leads_collection.insert_one(test_doc)
    print("Inserted test doc with ID:", result.inserted_id)
    await leads_collection.delete_one({"_id": result.inserted_id})
    print("Test document removed successfully.")

# Test API key rotation
def test_api_key_rotation():
    print("Testing API Key rotation...")
    key_manager = APIKeyManager()
    for _ in range(3):
        print("Current key:", key_manager.get_key())

# Basic Google Places test
def test_google_places():
    print("Testing Google Places API...")
    key_manager = APIKeyManager()
    key = key_manager.get_key()

    params = {
        "key": key,
        "location": "-33.8688,151.2093",
        "radius": 500,
        "type": "restaurant"
    }

    response = requests.get("https://maps.googleapis.com/maps/api/place/nearbysearch/json", params=params)

    if response.status_code == 200:
        data = response.json()
        print("Success! Businesses returned:", len(data.get("results", [])))
        for biz in data.get("results", [])[:3]:
            print("-", biz.get("name"), "//", biz.get("place_id"))
    else:
        print("Failed. Status code:", response.status_code)
        print(response.text)

# Main runner
if __name__ == "__main__":
    print("Running backend integration tests...\n")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_db())

    print("\n---\n")
    test_api_key_rotation()
    print("\n---\n")
    test_google_places()

