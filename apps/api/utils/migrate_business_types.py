"""
Database Migration Script: Convert business_type to business_types array

This script migrates existing leads from the old schema (single business_type)
to the new schema (business_types array).

Usage:
    python utils/migrate_business_types.py
"""

import sys
import os
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGO_DB_URI", "mongodb://localhost:27017")
MONGODB_NAME = os.getenv("MONGO_DB_NAME", "leads_db")


async def migrate_business_types():
    """
    Migrate all existing leads to use business_types array instead of business_type string.

    Steps:
    1. Find all documents with business_type field (old schema)
    2. Convert business_type to business_types array [business_type]
    3. Remove old business_type field
    4. Report statistics
    """

    print("\n" + "="*70)
    print("DATABASE MIGRATION: business_type → business_types")
    print("="*70)

    # Connect to database
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_NAME]
    leads_collection = db["leads"]

    # Step 1: Count documents needing migration
    old_schema_count = await leads_collection.count_documents({"business_type": {"$exists": True}})
    new_schema_count = await leads_collection.count_documents({"business_types": {"$exists": True}})
    total_count = await leads_collection.count_documents({})

    print(f"\n📊 Current Database State:")
    print(f"   Total leads: {total_count}")
    print(f"   Using old schema (business_type): {old_schema_count}")
    print(f"   Using new schema (business_types): {new_schema_count}")

    if old_schema_count == 0:
        print("\n✅ No migration needed. All documents already use business_types array.")
        client.close()
        return

    # Ask for confirmation
    print(f"\n⚠️  This will migrate {old_schema_count} documents.")
    response = input("Continue? (yes/no): ")

    if response.lower() not in ['yes', 'y']:
        print("Migration cancelled.")
        client.close()
        return

    # Step 2: Perform migration
    print(f"\n🔄 Starting migration...")
    start_time = datetime.now()

    migrated = 0
    failed = 0

    # Find all documents with old schema
    cursor = leads_collection.find({"business_type": {"$exists": True}})

    async for doc in cursor:
        try:
            business_type = doc.get("business_type")
            existing_types = doc.get("business_types", [])

            # Combine old business_type with existing business_types (if any)
            if business_type and business_type not in existing_types:
                existing_types.append(business_type)

            # Update document
            await leads_collection.update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {"business_types": existing_types},
                    "$unset": {"business_type": ""}  # Remove old field
                }
            )

            migrated += 1

            if migrated % 100 == 0:
                print(f"   Migrated {migrated}/{old_schema_count} documents...")

        except Exception as e:
            failed += 1
            print(f"   ❌ Failed to migrate document {doc.get('_id')}: {str(e)}")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Step 3: Verify migration
    remaining_old = await leads_collection.count_documents({"business_type": {"$exists": True}})
    new_count = await leads_collection.count_documents({"business_types": {"$exists": True}})

    # Step 4: Report results
    print("\n" + "="*70)
    print("MIGRATION COMPLETE")
    print("="*70)
    print(f"✅ Successfully migrated: {migrated} documents")
    print(f"❌ Failed: {failed} documents")
    print(f"⏱️  Duration: {duration:.2f} seconds")
    print(f"\n📊 Final Database State:")
    print(f"   Total leads: {await leads_collection.count_documents({})}")
    print(f"   Using old schema (business_type): {remaining_old}")
    print(f"   Using new schema (business_types): {new_count}")

    if remaining_old > 0:
        print(f"\n⚠️  Warning: {remaining_old} documents still using old schema")
    else:
        print("\n✅ All documents successfully migrated to new schema!")

    print("="*70 + "\n")

    client.close()


if __name__ == "__main__":
    asyncio.run(migrate_business_types())
